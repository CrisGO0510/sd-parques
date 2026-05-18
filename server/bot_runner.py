"""BotRunner: schedules bot actions using threading.Timer with epoch-based
race protection against session resets."""
from __future__ import annotations

import logging
import random
import threading
from typing import TYPE_CHECKING, Callable, Optional

from core import engine  # noqa: F401  (kept for parity; engine accessed via session)
from core.entities import GamePhase
from server.recommender import most_advanced_piece_index, recommend
from server.session import GameSession

if TYPE_CHECKING:
    from server.server import Server

logger = logging.getLogger(__name__)

# Type alias for the delay primitive. Real implementation uses threading.Timer.
# Tests inject an inline variant that fires the callback synchronously.
DelayFn = Callable[[float, Callable[[], None]], object]


def _default_delay_fn(delay_seconds: float, cb: Callable[[], None]) -> threading.Timer:
    timer = threading.Timer(delay_seconds, cb)
    timer.daemon = True
    timer.start()
    return timer


class BotRunner:
    """Schedules one bot action per turn under the server's global lock.

    Each scheduled timer captures the current bound epoch in its closure.
    When the timer fires, the tick validates:
      1. closure epoch == self._epoch (no new bind_session happened)
      2. server.session is not None
      3. it is this bot's turn (or, in SETUP, this bot still owes a roll)

    If any check fails, the tick is silently discarded.
    """

    def __init__(
        self,
        server: "Server",
        rng: random.Random,
        delay_fn: Optional[DelayFn] = None,
        min_ms: int = 500,
        max_ms: int = 1500,
    ) -> None:
        self._server = server
        self._rng = rng
        self._delay_fn = delay_fn or _default_delay_fn
        self._min_ms = min_ms
        self._max_ms = max_ms
        self._timers: dict[str, object] = {}
        self._session: GameSession | None = None
        self._epoch: int = 0

    def bind_session(self, session: GameSession, epoch: int) -> None:
        self._session = session
        self._epoch = epoch

    def schedule(self, conn_id: str) -> None:
        """Cancel any previous timer for this conn_id and schedule a new tick."""
        self._cancel_one(conn_id)
        epoch = self._epoch
        delay_ms = self._rng.randint(self._min_ms, self._max_ms)
        delay_s = delay_ms / 1000.0
        timer = self._delay_fn(delay_s, lambda: self._tick(conn_id, epoch))
        self._timers[conn_id] = timer

    def cancel_all(self) -> None:
        for cid in list(self._timers.keys()):
            self._cancel_one(cid)

    def _cancel_one(self, conn_id: str) -> None:
        timer = self._timers.pop(conn_id, None)
        if timer is None:
            return
        cancel = getattr(timer, "cancel", None)
        if callable(cancel):
            cancel()

    def _tick(self, conn_id: str, epoch: int) -> None:
        with self._server.lock:
            # Guard 1: epoch must match the runner's bound epoch.
            if epoch != self._epoch:
                logger.debug("bot tick epoch mismatch: %d != %d, discarding",
                             epoch, self._epoch)
                return
            session = self._server.session
            if session is None:
                return
            game = session.game
            player_idx = session.player_index_for_conn(conn_id)
            if player_idx is None:
                return

            phase = game.phase
            if phase is GamePhase.SETUP:
                if player_idx in game.initial_rolls:
                    return
                self._do_roll_initial(session, conn_id, player_idx)
            elif phase is GamePhase.ROLLING:
                if session.current_turn_conn_id() != conn_id:
                    return
                self._do_roll_dice(session)
            elif phase is GamePhase.MOVING:
                if session.current_turn_conn_id() != conn_id:
                    return
                self._do_move(session, conn_id)
            elif phase is GamePhase.CROWNING:
                if session.current_turn_conn_id() != conn_id:
                    return
                self._do_crown(session, player_idx)
            elif phase is GamePhase.FINISHED:
                return

            # Reschedule whoever owes the next bot action (if any).
            self._server._maybe_schedule_bots()

    # --- per-phase actions ---

    def _do_roll_initial(self, session: GameSession, conn_id: str, player_idx: int) -> None:
        d1, d2 = session.roll_initial(player_idx)
        player = session.game.players[player_idx]
        self._server._broadcast_session({
            "type":         "initial_roll",
            "player_index": player_idx,
            "username":     player.name,
            "d1": d1, "d2": d2,
            "total":        d1 + d2,
        })
        self._server._broadcast_session({
            "type":  "state_update",
            "state": session.state_dict(),
        })

    def _do_roll_dice(self, session: GameSession) -> None:
        d1, d2 = session.roll_dice()
        player_idx = session.game.turn_order[session.game.current_turn_index]
        self._server._broadcast_session({
            "type":         "dice_result",
            "player_index": player_idx,
            "d1": d1, "d2": d2,
            "is_pair":      d1 == d2,
        })
        self._server._broadcast_session({
            "type":  "state_update",
            "state": session.state_dict(),
        })

    def _do_move(self, session: GameSession, conn_id: str) -> None:
        moves = session.available_moves()
        if not moves:
            session.skip_turn()
            self._server._broadcast_session({
                "type":  "state_update",
                "state": session.state_dict(),
            })
            return
        move = recommend(session.game, moves)
        if move is None:
            session.skip_turn()
            self._server._broadcast_session({
                "type":  "state_update",
                "state": session.state_dict(),
            })
            return
        result = session.apply_move(move)
        self._server._broadcast_session({
            "type": "move_applied",
            "move": {
                "piece_index": move.piece_index,
                "dice_value":  move.dice_value,
                "action":      move.action.value,
            },
            "result": {
                "action":       result.action.value,
                "reached_goal": result.reached_goal,
                "captured": [
                    {"index": c.index,
                     "circuit_position": c.circuit_position,
                     "state": c.state.value}
                    for c in result.captured
                ],
            },
        })
        self._server._broadcast_session({
            "type":  "state_update",
            "state": session.state_dict(),
        })
        if session.game.winner is not None:
            self._server._broadcast_session({
                "type":            "game_over",
                "winner_index":    session.game.winner,
                "winner_username": session.game.players[session.game.winner].name,
            })
            self._server._reset_to_lobby()

    def _do_crown(self, session: GameSession, player_idx: int) -> None:
        piece_idx = most_advanced_piece_index(session.game, player_idx)
        session.crown_piece(piece_idx)
        self._server._broadcast_session({
            "type":  "state_update",
            "state": session.state_dict(),
        })
        if session.game.winner is not None:
            self._server._broadcast_session({
                "type":            "game_over",
                "winner_index":    session.game.winner,
                "winner_username": session.game.players[session.game.winner].name,
            })
            self._server._reset_to_lobby()
