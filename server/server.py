"""Server: orchestrates accept loop, lobby, session, and message dispatch."""
from __future__ import annotations

import enum
import logging
import random
import socket
import threading
from typing import Any

from core.entities import Color
from core.exceptions import DomainError, DuplicatePlayer, InvalidMove, WrongPhase
from server.connection import ClientConnection
from server.lobby import Lobby
from server.protocol import ProtocolError, decode, encode, validate_command
from server.session import GameSession
from server.recommender import recommend

logger = logging.getLogger(__name__)


class ServerPhase(str, enum.Enum):
    LOBBY = "lobby"
    IN_GAME = "in_game"
    CLOSED = "closed"


DOMAIN_ERROR_CODES = {
    DuplicatePlayer: "DUPLICATE_PLAYER",
    WrongPhase:      "WRONG_PHASE",
    InvalidMove:     "INVALID_MOVE",
}


class Server:
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 5000,
        rng: random.Random | None = None,
    ):
        self.host = host
        self.port = port
        self._rng = rng
        self.lock = threading.Lock()
        self.phase: ServerPhase = ServerPhase.LOBBY
        self.lobby: Lobby = Lobby()
        self.session: GameSession | None = None
        self._connections: dict[str, Any] = {}
        self._listen_sock: socket.socket | None = None
        self._shutdown = False
        self._ready = threading.Event()
        self._next_conn_id = 0
        self._client_threads: list[threading.Thread] = []

    def serve_forever(self) -> None:
        self._listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listen_sock.bind((self.host, self.port))
        self.port = self._listen_sock.getsockname()[1]
        self._listen_sock.listen(8)
        self._listen_sock.settimeout(0.5)
        self._ready.set()
        logger.info("listening on %s:%d", self.host, self.port)
        try:
            while not self._shutdown:
                try:
                    sock, addr = self._listen_sock.accept()
                except socket.timeout:
                    continue
                except OSError:
                    if self._shutdown:
                        return
                    raise
                conn_id = self._mint_conn_id()
                conn = ClientConnection(sock, conn_id=conn_id)
                self.register_connection(conn)
                t = threading.Thread(
                    target=self._run_client_loop,
                    args=(conn,),
                    daemon=True,
                    name=f"client-{addr[1]}",
                )
                t.start()
                self._client_threads.append(t)
        finally:
            if self._listen_sock is not None:
                self._listen_sock.close()

    def wait_ready(self, timeout: float) -> None:
        if not self._ready.wait(timeout):
            raise TimeoutError("server did not bind in time")

    def shutdown(self) -> None:
        self._shutdown = True
        if self._listen_sock is not None:
            try:
                self._listen_sock.close()
            except OSError:
                pass

    def _mint_conn_id(self) -> str:
        with self.lock:
            self._next_conn_id += 1
            return f"c{self._next_conn_id}"

    def _run_client_loop(self, conn: ClientConnection) -> None:
        logger.info("%s connected", conn.conn_id)
        try:
            while True:
                line = conn.readline()
                if not line:
                    break
                try:
                    msg = decode(line)
                except ProtocolError as e:
                    self._send_error(conn, "BAD_MESSAGE", str(e))
                    continue
                self.handle_message(conn, msg)
        except (ConnectionResetError, OSError) as e:
            logger.warning("%s connection error: %s", conn.conn_id, e)
        finally:
            logger.info("%s disconnected", conn.conn_id)
            self._on_disconnect(conn)

    def _on_disconnect(self, conn: ClientConnection) -> None:
        with self.lock:
            if self.phase is ServerPhase.LOBBY:
                self.lobby.leave(conn.conn_id)
                self.unregister_connection(conn.conn_id)
                self._broadcast_lobby(self._lobby_update())
            elif self.phase is ServerPhase.IN_GAME:
                self._handle_ingame_leave(conn)
            else:
                self.unregister_connection(conn.conn_id)
            # Once every client from the previous round is gone, drop
            # back to LOBBY so new connections can start a fresh game
            # without restarting the server.
            if not self._connections and self.phase is not ServerPhase.LOBBY:
                self._reset_to_lobby()
        conn.close()

    def _auto_roll_initial_for_disconnected(self, conn_id: str) -> None:
        """If the game is still in SETUP and the just-disconnected
        player hasn't rolled their initial die yet, roll for them so
        turn_order can resolve and the other players stop waiting."""
        assert self.session is not None
        if self.session.game.phase.value != "setup":
            return
        player_idx = self.session.player_index_for_conn(conn_id)
        if player_idx is None:
            return
        if player_idx in self.session.game.initial_rolls:
            return
        try:
            d1, d2 = self.session.roll_initial(player_idx)
        except (DomainError, ValueError) as e:
            logger.warning("auto roll_initial failed for %s: %s", conn_id, e)
            return
        player = self.session.game.players[player_idx]
        logger.info(
            "auto-rolled initial for disconnected %s (%s): %d + %d = %d",
            conn_id, player.name, d1, d2, d1 + d2,
        )
        self._broadcast_session({
            "type": "initial_roll",
            "player_index": player_idx,
            "username": player.name,
            "d1": d1, "d2": d2,
            "total": d1 + d2,
        })

    def _maybe_skip_disconnected_turn(self) -> None:
        """If the turn cursor sits on a disconnected color, advance past
        it and rebroadcast state. Without this, the game freezes whenever
        play rotates onto a player who left earlier (since they will never
        send a command). Caller must hold `self.lock`."""
        if self.phase is not ServerPhase.IN_GAME or self.session is None:
            return
        if not self.session.disconnected_colors:
            return
        before_idx = self.session.game.current_turn_index
        self.session.advance_past_disconnected()
        if self.session.game.current_turn_index != before_idx:
            logger.info(
                "auto-skipped disconnected turn; current is now %s",
                self.session.current_turn_conn_id(),
            )
            self._broadcast_session({
                "type": "state_update",
                "state": self.session.state_dict(),
            })

    def _reset_to_lobby(self) -> None:
        """Clear any in-progress or finished game and return to LOBBY.
        Caller must hold `self.lock`."""
        logger.info(
            "no active connections left, resetting %s → LOBBY",
            self.phase.value,
        )
        self.phase = ServerPhase.LOBBY
        self.lobby = Lobby()
        self.session = None

    def register_connection(self, conn) -> None:
        """Make the server aware of a new connection (before any message arrives)."""
        self._connections[conn.conn_id] = conn

    def unregister_connection(self, conn_id: str) -> None:
        self._connections.pop(conn_id, None)

    # --- error helpers ---

    def _send_error(self, conn, code: str, message: str) -> None:
        conn.send(encode({"type": "error", "code": code, "message": message}))

    def _domain_error_code(self, e: DomainError) -> str:
        for cls, code in DOMAIN_ERROR_CODES.items():
            if isinstance(e, cls):
                return code
        return "DOMAIN_ERROR"

    # --- broadcast ---

    def _broadcast_lobby(self, event: dict) -> None:
        data = encode(event)
        for player in self.lobby.players():
            conn = self._connections.get(player.conn_id)
            if conn:
                conn.send(data)

    def _lobby_update(self) -> dict:
        return {
            "type": "lobby_update",
            "players": [
                {"username": p.username, "color": (p.color.value if p.color else None)}
                for p in self.lobby.players()
            ],
            "available_colors": [c.value for c in self.lobby.available_colors()],
        }

    def _broadcast_session(self, event: dict) -> None:
        if self.session is None:
            return
        data = encode(event)
        for conn_id in self.session.all_conn_ids():
            conn = self._connections.get(conn_id)
            if conn:
                try:
                    conn.send(data)
                except OSError:
                    pass

    # --- entry point ---

    def handle_message(self, conn, msg: dict) -> None:
        """Validate shape then dispatch within the lock."""
        try:
            validate_command(msg)
        except ProtocolError as e:
            self._send_error(conn, "BAD_MESSAGE", str(e))
            return

        with self.lock:
            try:
                self._dispatch(conn, msg)
            except DomainError as e:
                self._send_error(conn, self._domain_error_code(e), str(e))
            # If the turn just advanced onto someone who already left,
            # skip past them — otherwise the survivors stare at "Esperando…"
            # forever waiting for a command from a client that's gone.
            self._maybe_skip_disconnected_turn()

    # --- dispatch ---

    def _dispatch(self, conn, msg: dict) -> None:
        if self.phase is ServerPhase.LOBBY:
            self._dispatch_lobby(conn, msg)
        elif self.phase is ServerPhase.IN_GAME:
            self._dispatch_game(conn, msg)
        else:  # CLOSED
            self._send_error(conn, "GAME_ENDED", "the server is not accepting commands")

    def _dispatch_lobby(self, conn, msg: dict) -> None:
        t = msg["type"]
        if t == "join":
            player = self.lobby.join(conn.conn_id, msg["username"])
            conn.send(encode({
                "type": "welcome",
                "username": player.username,
                "is_host": player.is_host,
            }))
            self._broadcast_lobby(self._lobby_update())
        elif t == "select_color":
            try:
                color = Color(msg["color"])
            except ValueError:
                self._send_error(conn, "BAD_MESSAGE", f"invalid color: {msg['color']}")
                return
            self.lobby.select_color(conn.conn_id, color)
            self._broadcast_lobby(self._lobby_update())
        elif t == "start_game":
            host_conn_id = self.lobby.host_conn_id()
            if host_conn_id != conn.conn_id:
                self._send_error(conn, "FORBIDDEN", "only the host can start the game")
                return
            if not self.lobby.can_start():
                self._send_error(conn, "FORBIDDEN", "need 2-4 players with color assigned")
                return
            self._start_game()
        elif t == "leave":
            self.lobby.leave(conn.conn_id)
            self.unregister_connection(conn.conn_id)
            self._broadcast_lobby(self._lobby_update())
        else:
            self._send_error(conn, "WRONG_PHASE", f"{t} not allowed in LOBBY")

    def _start_game(self) -> None:
        entries = [
            (p.conn_id, p.username, p.color)
            for p in self.lobby.players()
        ]
        self.session = GameSession(entries=entries, rng=self._rng)
        self.phase = ServerPhase.IN_GAME
        self._broadcast_session({"type": "game_started"})
        self._broadcast_session({"type": "state_update", "state": self.session.state_dict()})

    def _dispatch_game(self, conn, msg: dict) -> None:
        assert self.session is not None
        t = msg["type"]

        # Identity check: conn must belong to the current game.
        player_idx = self.session.player_index_for_conn(conn.conn_id)
        if player_idx is None and t != "leave":
            self._send_error(conn, "FORBIDDEN", "you are not in this game")
            return

        if t == "leave":
            self._handle_ingame_leave(conn)
            return

        # Turn-scoped commands require being the current player.
        turn_required = {"roll_initial", "roll_dice", "move_piece",
                         "skip_turn", "crown_piece"}
        if t in turn_required:
            # roll_initial is allowed for any player who hasn't rolled yet.
            if t != "roll_initial":
                current_conn = self.session.current_turn_conn_id()
                if current_conn != conn.conn_id:
                    self._send_error(conn, "WRONG_PHASE", "not your turn")
                    return

        if t == "roll_initial":
            d1, d2 = self.session.roll_initial(player_idx)
            player = self.session.game.players[player_idx]
            self._broadcast_session({
                "type": "initial_roll",
                "player_index": player_idx,
                "username": player.name,
                "d1": d1, "d2": d2,
                "total": d1 + d2,
            })
            self._broadcast_session({
                "type": "state_update",
                "state": self.session.state_dict(),
            })
        elif t == "roll_dice":
            d1, d2 = self.session.roll_dice()
            self._broadcast_session({
                "type": "dice_result",
                "player_index": player_idx,
                "d1": d1, "d2": d2, "is_pair": d1 == d2,
            })
            self._broadcast_session({
                "type": "state_update",
                "state": self.session.state_dict(),
            })
            # If we're in MOVING phase, send available_moves to current player only.
            if self.session.game.phase.value == "moving":
                moves = [
                    {"piece_index": m.piece_index,
                     "dice_value":  m.dice_value,
                     "action":      m.action.value}
                    for m in self.session.available_moves()
                ]
                conn.send(encode({"type": "available_moves", "moves": moves}))
                rec = recommend(self.session.game, self.session.available_moves())
                if rec is not None:
                    conn.send(encode({
                        "type": "recommendation",
                        "piece_index": rec.piece_index,
                        "action": rec.action.value,
                        "dice_value": rec.dice_value,
                    }))
        elif t == "move_piece":
            from core.entities import Move, MoveAction
            try:
                move = Move(
                    piece_index=msg["piece_index"],
                    dice_value=msg["dice_value"],
                    action=MoveAction(msg["action"]),
                )
            except ValueError as e:
                self._send_error(conn, "BAD_MESSAGE", str(e))
                return
            result = self.session.apply_move(move)
            self._broadcast_session({
                "type": "move_applied",
                "move": {
                    "piece_index": move.piece_index,
                    "dice_value":  move.dice_value,
                    "action":      move.action.value,
                },
                "result": {
                    "action":         result.action.value,
                    "reached_goal":   result.reached_goal,
                    "captured":       [
                        {
                            "index":            c.index,
                            "circuit_position": c.circuit_position,
                            "state":            c.state.value,
                        }
                        for c in result.captured
                    ],
                },
            })
            self._broadcast_session({
                "type": "state_update",
                "state": self.session.state_dict(),
            })
            # If the game is over, drop straight back to LOBBY so a new
            # round can start even while losers are still parked on EndPage.
            if self.session.game.winner is not None:
                self._broadcast_session({
                    "type": "game_over",
                    "winner_index":    self.session.game.winner,
                    "winner_username": self.session.game.players[self.session.game.winner].name,
                })
                self._reset_to_lobby()
            elif self.session.game.pending_dice and self.session.game.phase.value == "moving":
                # Still moves pending; tell current player their options.
                current_conn_id = self.session.current_turn_conn_id()
                cur = self._connections.get(current_conn_id)
                if cur is not None:
                    moves = [
                        {"piece_index": m.piece_index,
                         "dice_value":  m.dice_value,
                         "action":      m.action.value}
                        for m in self.session.available_moves()
                    ]
                    cur.send(encode({"type": "available_moves", "moves": moves}))
                    rec = recommend(self.session.game, self.session.available_moves())
                    if rec is not None:
                        cur.send(encode({
                            "type": "recommendation",
                            "piece_index": rec.piece_index,
                            "action": rec.action.value,
                        }))
        elif t == "skip_turn":
            self.session.skip_turn()
            self._broadcast_session({
                "type": "state_update",
                "state": self.session.state_dict(),
            })
        elif t == "crown_piece":
            self.session.crown_piece(msg["piece_index"])
            self._broadcast_session({
                "type": "state_update",
                "state": self.session.state_dict(),
            })
            if self.session.game.winner is not None:
                self._broadcast_session({
                    "type": "game_over",
                    "winner_index":    self.session.game.winner,
                    "winner_username": self.session.game.players[self.session.game.winner].name,
                })
                self._reset_to_lobby()
        elif t == "join":
            self._send_error(conn, "FORBIDDEN", "a game is in progress")
        else:
            self._send_error(conn, "WRONG_PHASE", f"{t} not allowed in IN_GAME")

    def _handle_ingame_leave(self, conn) -> None:
        assert self.session is not None
        color = self.session.color_for_conn(conn.conn_id)
        if color is not None:
            logger.info(
                "in-game leave: conn=%s color=%s phase=%s",
                conn.conn_id, color.value, self.session.game.phase.value,
            )
            self.session.mark_disconnected(conn.conn_id)
            self.unregister_connection(conn.conn_id)
            # SETUP hangs if someone leaves without rolling their initial
            # die — roll on their behalf so turn_order can resolve.
            self._auto_roll_initial_for_disconnected(conn.conn_id)
            # If the disconnect leaves enough players to keep playing,
            # skip past any disconnected colors holding the turn so the
            # game doesn't hang waiting for them to roll.
            if self.session.connected_count() >= 2:
                if self.session.advance_past_disconnected():
                    logger.info(
                        "advanced past disconnected: current turn now on %s",
                        self.session.current_turn_conn_id(),
                    )
            self._broadcast_session({
                "type": "state_update",
                "state": self.session.state_dict(),
            })
            # If the new current player is in MOVING (rare — happens
            # only if the turn didn't actually advance), rebroadcast
            # available moves so they render. In the typical case
            # advance_past_disconnected resets phase to ROLLING.
            if self.session.game.phase.value == "moving":
                moves = self.session.available_moves()
                self._broadcast_session({
                    "type": "available_moves",
                    "moves": [
                        {"piece_index": m.piece_index,
                         "dice_value":  m.dice_value,
                         "action":      m.action.value}
                        for m in moves
                    ],
                })
            if self.session.connected_count() < 2:
                # End the game.
                last = self.session.game.winner  # may already be set
                if last is None:
                    # Try to declare the last connected player winner.
                    for idx, player in enumerate(self.session.game.players):
                        if player.color not in self.session.disconnected_colors:
                            last = idx
                            break
                self.session.game.winner = last
                self._broadcast_session({
                    "type": "game_over",
                    "winner_index":    last,
                    "winner_username": (
                        self.session.game.players[last].name if last is not None else None
                    ),
                })
                self._reset_to_lobby()
