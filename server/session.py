"""GameSession: wraps core.Game with conn↔color mapping."""
from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field

from core import engine
from core.entities import Color, Game, GamePhase


@dataclass
class SessionEntry:
    conn_id: str
    username: str
    color: Color
    is_bot: bool = False


@dataclass
class GameSession:
    entries: list[SessionEntry]
    rng: random.Random | None = None
    game: Game = field(init=False)
    _conn_by_color: dict[Color, str] = field(init=False)
    _color_by_conn: dict[str, Color] = field(init=False)
    _is_bot_by_conn: dict[str, bool] = field(init=False)
    disconnected_colors: set[Color] = field(default_factory=set, init=False)

    def __post_init__(self) -> None:
        self.game = engine.new_game(
            [(e.username, e.color) for e in self.entries],
            rng=self.rng,
        )
        self._conn_by_color = {e.color: e.conn_id for e in self.entries}
        self._color_by_conn = {e.conn_id: e.color for e in self.entries}
        self._is_bot_by_conn = {e.conn_id: e.is_bot for e in self.entries}

    # ---- mappings ----

    def color_for_conn(self, conn_id: str) -> Color | None:
        return self._color_by_conn.get(conn_id)

    def conn_for_color(self, color: Color) -> str | None:
        return self._conn_by_color.get(color)

    def player_index_for_conn(self, conn_id: str) -> int | None:
        color = self.color_for_conn(conn_id)
        if color is None:
            return None
        for i, player in enumerate(self.game.players):
            if player.color is color:
                return i
        return None

    def current_turn_conn_id(self) -> str | None:
        if not self.game.turn_order:
            return None
        idx = self.game.turn_order[self.game.current_turn_index]
        return self.conn_for_color(self.game.players[idx].color)

    # ---- bot helpers ----

    def is_bot(self, conn_id: str) -> bool:
        return self._is_bot_by_conn.get(conn_id, False)

    def bot_conn_ids(self) -> list[str]:
        return [cid for cid, is_bot in self._is_bot_by_conn.items() if is_bot]

    def human_conn_ids(self) -> list[str]:
        return [cid for cid, is_bot in self._is_bot_by_conn.items() if not is_bot]

    def human_connected_count(self) -> int:
        """Number of humans not marked disconnected. Bots do not count."""
        count = 0
        for cid, color in self._color_by_conn.items():
            if self._is_bot_by_conn.get(cid, False):
                continue
            if color not in self.disconnected_colors:
                count += 1
        return count

    # ---- engine delegation ----

    def roll_initial(self, player_index: int) -> tuple[int, int]:
        return engine.roll_initial(self.game, player_index)

    def roll_dice(self) -> tuple[int, int]:
        return engine.roll_dice(self.game)

    def available_moves(self):
        return engine.available_moves(self.game)

    def apply_move(self, move):
        return engine.apply_move(self.game, move)

    def skip_turn(self) -> None:
        engine.skip_turn(self.game)

    def crown_piece(self, piece_index: int) -> None:
        engine.crown_piece(self.game, piece_index)

    # ---- disconnection ----

    def mark_disconnected(self, conn_id: str) -> None:
        color = self.color_for_conn(conn_id)
        if color is not None:
            self.disconnected_colors.add(color)

    def connected_count(self) -> int:
        return sum(
            1 for color in self._color_by_conn.values()
            if color not in self.disconnected_colors
        )

    def connected_conn_ids(self) -> list[str]:
        return [
            conn_id for conn_id, color in self._color_by_conn.items()
            if color not in self.disconnected_colors
        ]

    def all_conn_ids(self) -> list[str]:
        return list(self._color_by_conn.keys())

    def _current_color(self) -> Color | None:
        if not self.game.turn_order:
            return None
        idx = self.game.turn_order[self.game.current_turn_index]
        return self.game.players[idx].color

    def advance_past_disconnected(self) -> bool:
        if self.connected_count() == 0:
            return False
        for _ in range(len(self.game.turn_order)):
            current_color = self._current_color()
            if current_color is None:
                return False
            if current_color not in self.disconnected_colors:
                return True
            self.game.pending_dice = []
            self.game.consecutive_pairs = 0
            self.game.initial_rolls_remaining = 0
            self.game.current_turn_index = (
                self.game.current_turn_index + 1
            ) % len(self.game.turn_order)
            self.game.phase = GamePhase.ROLLING
        return False

    # ---- serialization ----

    def state_dict(self) -> dict:
        """Return the Game as a JSON-serializable dict.

        Augments each player with `is_bot` so the client can show a "BOT"
        badge per-player without consulting the lobby store (which is
        wiped on page refresh)."""
        d = asdict(self.game)
        d["disconnected_colors"] = sorted(c.value for c in self.disconnected_colors)
        # Map color string → is_bot.
        is_bot_by_color: dict[str, bool] = {}
        for e in self.entries:
            is_bot_by_color[e.color.value] = e.is_bot
        for player in d["players"]:
            player["is_bot"] = is_bot_by_color.get(player["color"], False)
        return d
