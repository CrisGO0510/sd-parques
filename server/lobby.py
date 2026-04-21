"""Lobby: tracks players waiting for a game to start."""
from __future__ import annotations

from dataclasses import dataclass, field

from core.entities import Color
from core.exceptions import DomainError, DuplicatePlayer


class LobbyError(DomainError):
    """Base for lobby-specific errors."""


class LobbyFull(LobbyError):
    """The lobby already has 4 players."""


MAX_PLAYERS = 4


@dataclass
class LobbyPlayer:
    conn_id: str
    username: str
    is_host: bool = False
    color: Color | None = None


@dataclass
class Lobby:
    _players: list[LobbyPlayer] = field(default_factory=list)

    def join(self, conn_id: str, username: str) -> LobbyPlayer:
        if len(self._players) >= MAX_PLAYERS:
            raise LobbyFull("lobby is full (max 4 players)")
        if any(p.username == username for p in self._players):
            raise DuplicatePlayer(f"duplicate name: {username}")
        player = LobbyPlayer(
            conn_id=conn_id,
            username=username,
            is_host=(len(self._players) == 0),
        )
        self._players.append(player)
        return player

    def leave(self, conn_id: str) -> None:
        was_host = any(p.conn_id == conn_id and p.is_host for p in self._players)
        self._players = [p for p in self._players if p.conn_id != conn_id]
        if was_host and self._players:
            self._players[0].is_host = True

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
        return all(p.color is not None for p in self._players)
