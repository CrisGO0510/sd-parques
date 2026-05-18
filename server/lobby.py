"""Lobby: tracks players waiting for a game to start."""
from __future__ import annotations

from dataclasses import dataclass, field

from core.entities import Color
from core.exceptions import DomainError, DuplicatePlayer


class LobbyError(DomainError):
    """Base for lobby-specific errors."""


class LobbyFull(LobbyError):
    """The lobby already has 4 players, or the bot cap has been reached."""


MAX_PLAYERS = 4
MAX_BOTS = 3
BOT_CONN_PREFIX = "bot:"

_BOT_NAME_BY_COLOR: dict[Color, str] = {
    Color.RED:    "Bot Rojo",
    Color.BLUE:   "Bot Azul",
    Color.GREEN:  "Bot Verde",
    Color.YELLOW: "Bot Amarillo",
}


def is_bot_conn_id(conn_id: str) -> bool:
    return conn_id.startswith(BOT_CONN_PREFIX)


@dataclass
class LobbyPlayer:
    conn_id: str
    username: str
    is_host: bool = False
    color: Color | None = None
    is_bot: bool = False


@dataclass
class Lobby:
    _players: list[LobbyPlayer] = field(default_factory=list)

    def join(self, conn_id: str, username: str) -> LobbyPlayer:
        if len(self._players) >= MAX_PLAYERS:
            raise LobbyFull("lobby is full (max 4 players)")
        if any(p.username == username for p in self._players):
            raise DuplicatePlayer(f"duplicate name: {username}")
        # Invariante: host siempre humano. Si no hay host (caso del primer
        # humano que entra a un lobby vacío o con solo bots), este humano
        # asume host.
        has_host = any(p.is_host for p in self._players)
        player = LobbyPlayer(
            conn_id=conn_id,
            username=username,
            is_host=not has_host,
            is_bot=False,
        )
        self._players.append(player)
        return player

    def add_bot(self, color: Color) -> LobbyPlayer:
        # Chequear cota de bots primero — si ya hay 3 bots con la sala no llena,
        # el rechazo debe ser por la regla de bots, no por capacidad.
        bot_count = sum(1 for p in self._players if p.is_bot)
        if bot_count >= MAX_BOTS:
            raise LobbyFull(f"max {MAX_BOTS} bots")
        if len(self._players) >= MAX_PLAYERS:
            raise LobbyFull("lobby is full (max 4 players)")
        if any(p.color is color for p in self._players):
            raise DuplicatePlayer(f"color {color.value} already taken")
        bot = LobbyPlayer(
            conn_id=f"{BOT_CONN_PREFIX}{color.value}",
            username=_BOT_NAME_BY_COLOR[color],
            is_host=False,
            color=color,
            is_bot=True,
        )
        self._players.append(bot)
        return bot

    def remove_bot(self, conn_id: str) -> None:
        target = self.get_by_conn(conn_id)
        if target is None:
            raise LobbyError(f"connection {conn_id} not in lobby")
        if not target.is_bot:
            raise LobbyError(f"connection {conn_id} is not a bot")
        self._players = [p for p in self._players if p.conn_id != conn_id]

    def clear_bots(self) -> None:
        """Remove every bot. Used when the last human leaves the lobby."""
        self._players = [p for p in self._players if not p.is_bot]

    def leave(self, conn_id: str) -> None:
        was_host = any(p.conn_id == conn_id and p.is_host for p in self._players)
        self._players = [p for p in self._players if p.conn_id != conn_id]
        if was_host:
            for p in self._players:
                if not p.is_bot:
                    p.is_host = True
                    break

    def has_conn(self, conn_id: str) -> bool:
        return any(p.conn_id == conn_id for p in self._players)

    def host_conn_id(self) -> str | None:
        for p in self._players:
            if p.is_host:
                return p.conn_id
        return None

    def players(self) -> list[LobbyPlayer]:
        return list(self._players)

    def get_by_conn(self, conn_id: str) -> LobbyPlayer | None:
        for p in self._players:
            if p.conn_id == conn_id:
                return p
        return None

    def select_color(self, conn_id: str, color: Color) -> None:
        player = self.get_by_conn(conn_id)
        if player is None:
            raise LobbyError(f"connection {conn_id} not in lobby")
        if any(p.color is color and p.conn_id != conn_id for p in self._players):
            raise DuplicatePlayer(f"color {color.value} already taken")
        player.color = color

    def available_colors(self) -> list[Color]:
        taken = {p.color for p in self._players if p.color is not None}
        return [c for c in Color if c not in taken]

    def can_start(self) -> bool:
        if not 2 <= len(self._players) <= MAX_PLAYERS:
            return False
        if not all(p.color is not None for p in self._players):
            return False
        if not any(not p.is_bot for p in self._players):
            return False
        return True
