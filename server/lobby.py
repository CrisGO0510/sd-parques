"""Lobby: tracks players waiting for a game to start.

Modelo fijo: máximo 2 jugadores humanos + 2 bots fijos (Camila=GREEN,
Bryan=YELLOW). Los bots se siembran al construir el Lobby y nunca se quitan
manualmente; los humanos eligen entre los colores restantes (RED y BLUE).
El orden de turnos queda intercalado: RED (humano) -> GREEN (Camila) ->
BLUE (humano) -> YELLOW (Bryan).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from core.entities import Color
from core.exceptions import DomainError, DuplicatePlayer


class LobbyError(DomainError):
    """Base for lobby-specific errors."""


class LobbyFull(LobbyError):
    """El lobby ya tiene sus 2 jugadores humanos."""


MAX_PLAYERS = 4
MAX_HUMANS = 2
BOT_CONN_PREFIX = "bot:"

# Bots fijos por color. Camila y Bryan ocupan GREEN y YELLOW; los humanos
# eligen entre RED y BLUE.
FIXED_BOTS: dict[Color, str] = {
    Color.GREEN:  "Camila",
    Color.YELLOW: "Bryan",
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


def _seed_bots() -> list[LobbyPlayer]:
    """Crea los 2 bots fijos con su color asignado (se usa al construir el Lobby)."""
    return [
        LobbyPlayer(
            conn_id=f"{BOT_CONN_PREFIX}{color.value}",
            username=name,
            is_host=False,
            color=color,
            is_bot=True,
        )
        for color, name in FIXED_BOTS.items()
    ]


@dataclass
class Lobby:
    _players: list[LobbyPlayer] = field(default_factory=_seed_bots)

    def join(self, conn_id: str, username: str) -> LobbyPlayer:
        human_count = sum(1 for p in self._players if not p.is_bot)
        if human_count >= MAX_HUMANS:
            raise LobbyFull("máximo 2 jugadores")
        if any(p.username == username for p in self._players):
            raise DuplicatePlayer(f"duplicate name: {username}")
        # Invariante: host siempre humano. El primer humano que entra (no hay
        # host, porque los bots no son host) asume host.
        has_host = any(p.is_host for p in self._players)
        player = LobbyPlayer(
            conn_id=conn_id,
            username=username,
            is_host=not has_host,
            is_bot=False,
        )
        self._players.append(player)
        return player

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
        humans = [p for p in self._players if not p.is_bot]
        if not humans:
            return False
        return all(p.color is not None for p in humans)
