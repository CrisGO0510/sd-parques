# Modelo de jugadores: 2 humanos + 2 bots fijos — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Regla de commits de este repo:** SOLO el usuario hace `git commit` / `git push`.
> Los pasos "Commit" de este plan significan: ejecutar el `git add` indicado y
> **presentar** el mensaje de commit propuesto para que el usuario lo confirme.
> NO ejecutar `git commit`.

**Goal:** Cambiar el modelo de partida a un máximo de 2 jugadores humanos + 2 bots fijos (Camila=GREEN, Bryan=YELLOW), eliminando los comandos `add_bot`/`remove_bot`, y reiniciar el lobby cuando se va el último humano.

**Architecture:** El `Lobby` se siembra con los 2 bots al construirse (única fuente de verdad). El `Server` elimina las ramas de añadir/quitar bots y reinicia el `Lobby` cuando no quedan humanos. El protocolo retira los dos comandos. El cliente (tipos, store, página) deja de ofrecer añadir/quitar bots y los bots llegan solos en `lobby_update`.

**Tech Stack:** Python 3.11 + pytest (backend); Vue 3 + TypeScript + Pinia + Vitest (cliente). Spec: `docs/superpowers/specs/2026-06-02-parques-jugadores-bots-fijos-design.md`.

---

## Archivos afectados

**Backend (`server/`):**
- `server/lobby.py` — sembrar bots fijos; `MAX_HUMANS`/`FIXED_BOTS`; quitar `add_bot`/`remove_bot`/`clear_bots`/`MAX_BOTS`/`_BOT_NAME_BY_COLOR`; ajustar `join`/`can_start`.
- `server/protocol.py` — quitar `add_bot`/`remove_bot` de `COMMAND_SCHEMAS`.
- `server/server.py` — quitar import `MAX_BOTS`; quitar ramas `add_bot`/`remove_bot`; reemplazar `clear_bots` por reinicio de lobby; helper `_reset_lobby_if_no_humans`.

**Tests backend (`tests_server/`):**
- `test_lobby_bots.py` — reescrito al nuevo modelo.
- `test_lobby.py` — ajustes de join/colores/can_start.
- `test_protocol_bots.py` — reescrito (tipos ya no válidos).
- `test_server_bots.py` — reescrito (sin add/remove bot; reinicio de lobby).
- `test_session_bots.py` — datos de bot a Camila/Bryan (opcional, coherencia).

**Cliente (`client/src/`):**
- `types/protocol.ts` — quitar `ADD_BOT`/`REMOVE_BOT` del enum y del union.
- `stores/lobby.ts` — quitar `addBot`/`removeBot`; ajustar `canStart`.
- `stores/lobby.test.ts` — ajustar expectativas.
- `pages/LobbyPage.vue` — quitar UI de añadir/quitar bot.

---

## Task 1: `Lobby` siembra los 2 bots fijos y aplica `MAX_HUMANS`

**Files:**
- Modify: `server/lobby.py`
- Test: `tests_server/test_lobby_bots.py` (reescritura completa)

- [ ] **Step 1: Reescribir el test al nuevo modelo**

Reemplaza **todo** el contenido de `tests_server/test_lobby_bots.py` por:

```python
"""Pruebas de Lobby con los 2 bots fijos (Camila=GREEN, Bryan=YELLOW)."""
from __future__ import annotations

import pytest

from core.entities import Color
from core.exceptions import DuplicatePlayer
from server.lobby import (
    BOT_CONN_PREFIX,
    FIXED_BOTS,
    MAX_HUMANS,
    Lobby,
    LobbyFull,
    is_bot_conn_id,
)


def test_is_bot_conn_id_detects_prefix():
    assert is_bot_conn_id("bot:green") is True
    assert is_bot_conn_id("c1") is False
    assert is_bot_conn_id("") is False


def test_fresh_lobby_has_two_fixed_bots():
    lobby = Lobby()
    bots = [p for p in lobby.players() if p.is_bot]
    assert len(bots) == 2
    by_color = {p.color: p for p in bots}
    assert by_color[Color.GREEN].username == "Camila"
    assert by_color[Color.YELLOW].username == "Bryan"


def test_fixed_bots_have_synthetic_conn_ids_and_are_not_host():
    lobby = Lobby()
    bots = {p.color: p for p in lobby.players() if p.is_bot}
    assert bots[Color.GREEN].conn_id == f"{BOT_CONN_PREFIX}green"
    assert bots[Color.YELLOW].conn_id == f"{BOT_CONN_PREFIX}yellow"
    assert all(not p.is_host for p in bots.values())


def test_fresh_lobby_has_no_humans_and_no_host():
    lobby = Lobby()
    assert [p for p in lobby.players() if not p.is_bot] == []
    assert lobby.host_conn_id() is None


def test_first_human_becomes_host():
    lobby = Lobby()
    human = lobby.join("c1", "Cris")
    assert human.is_host is True
    assert lobby.host_conn_id() == "c1"


def test_join_rejects_third_human():
    lobby = Lobby()
    lobby.join("c1", "Cris")
    lobby.join("c2", "Ana")
    with pytest.raises(LobbyFull):
        lobby.join("c3", "Eve")


def test_max_humans_is_two():
    assert MAX_HUMANS == 2


def test_available_colors_excludes_bot_colors():
    lobby = Lobby()
    available = lobby.available_colors()
    assert Color.GREEN not in available
    assert Color.YELLOW not in available
    assert set(available) == {Color.RED, Color.BLUE}


def test_human_cannot_take_a_bot_color():
    lobby = Lobby()
    lobby.join("c1", "Cris")
    with pytest.raises(DuplicatePlayer):
        lobby.select_color("c1", Color.GREEN)


def test_can_start_requires_at_least_one_human_with_color():
    lobby = Lobby()
    assert lobby.can_start() is False  # solo bots, sin humanos
    lobby.join("c1", "Cris")
    assert lobby.can_start() is False  # humano sin color
    lobby.select_color("c1", Color.RED)
    assert lobby.can_start() is True   # 1 humano con color + 2 bots


def test_fixed_bots_lists_camila_and_bryan():
    assert FIXED_BOTS == {Color.GREEN: "Camila", Color.YELLOW: "Bryan"}
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `python -m pytest tests_server/test_lobby_bots.py -v`
Expected: FAIL (ImportError de `FIXED_BOTS`/`MAX_HUMANS`, o bots no sembrados).

- [ ] **Step 3: Reescribir `server/lobby.py`**

Reemplaza **todo** el contenido de `server/lobby.py` por:

```python
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
```

- [ ] **Step 4: Ejecutar el test y verificar que pasa**

Run: `python -m pytest tests_server/test_lobby_bots.py -v`
Expected: PASS (todos).

- [ ] **Step 5: Commit (lo ejecuta el usuario)**

```bash
git add server/lobby.py tests_server/test_lobby_bots.py
```
Mensaje propuesto:
`feat(lobby): sembrar 2 bots fijos (Camila/Bryan) y limitar a 2 humanos`

---

## Task 2: Ajustar `tests_server/test_lobby.py` al nuevo modelo

Los tests genéricos del lobby asumen un lobby vacío y 4 humanos posibles. Hay que ajustarlos: ahora el lobby arranca con 2 bots, máx. 2 humanos, y GREEN/YELLOW están ocupados.

**Files:**
- Test: `tests_server/test_lobby.py`

- [ ] **Step 1: Reescribir los tests afectados**

Reemplaza **todo** el contenido de `tests_server/test_lobby.py` por:

```python
import pytest

from server.lobby import Lobby, LobbyFull, LobbyError
from core.exceptions import DuplicatePlayer
from core.entities import Color


def _humans(lobby: Lobby):
    return [p for p in lobby.players() if not p.is_bot]


def test_first_joiner_is_host():
    lobby = Lobby()
    p = lobby.join("c1", "Alice")
    assert p.username == "Alice"
    assert p.is_host is True
    assert p.color is None


def test_second_joiner_is_not_host():
    lobby = Lobby()
    lobby.join("c1", "Alice")
    p = lobby.join("c2", "Bob")
    assert p.is_host is False


def test_rejects_duplicate_username():
    lobby = Lobby()
    lobby.join("c1", "Alice")
    with pytest.raises(DuplicatePlayer, match="name"):
        lobby.join("c2", "Alice")


def test_rejects_third_human():
    lobby = Lobby()
    lobby.join("c1", "Alice")
    lobby.join("c2", "Bob")
    with pytest.raises(LobbyFull):
        lobby.join("c3", "Eve")


def test_leave_removes_player():
    lobby = Lobby()
    lobby.join("c1", "Alice")
    lobby.join("c2", "Bob")
    lobby.leave("c1")
    assert not lobby.has_conn("c1")
    assert lobby.has_conn("c2")


def test_leave_promotes_next_human_host():
    lobby = Lobby()
    lobby.join("c1", "Alice")  # host
    lobby.join("c2", "Bob")
    lobby.leave("c1")
    assert lobby.host_conn_id() == "c2"


def test_leave_nonexistent_is_noop():
    lobby = Lobby()
    lobby.leave("unknown")  # does not raise


def test_players_returns_bots_then_join_order():
    lobby = Lobby()
    lobby.join("c1", "Alice")
    lobby.join("c2", "Bob")
    human_names = [p.username for p in _humans(lobby)]
    assert human_names == ["Alice", "Bob"]


def test_select_color_assigns():
    lobby = Lobby()
    lobby.join("c1", "Alice")
    lobby.select_color("c1", Color.RED)
    assert lobby.get_by_conn("c1").color is Color.RED


def test_select_color_rejects_duplicate_between_humans():
    lobby = Lobby()
    lobby.join("c1", "Alice")
    lobby.join("c2", "Bob")
    lobby.select_color("c1", Color.RED)
    with pytest.raises(DuplicatePlayer, match="color"):
        lobby.select_color("c2", Color.RED)


def test_select_color_rejects_bot_color():
    lobby = Lobby()
    lobby.join("c1", "Alice")
    with pytest.raises(DuplicatePlayer, match="color"):
        lobby.select_color("c1", Color.GREEN)


def test_select_color_allows_changing_own():
    lobby = Lobby()
    lobby.join("c1", "Alice")
    lobby.select_color("c1", Color.RED)
    lobby.select_color("c1", Color.BLUE)
    assert lobby.get_by_conn("c1").color is Color.BLUE


def test_select_color_unknown_conn_raises():
    lobby = Lobby()
    with pytest.raises(LobbyError):
        lobby.select_color("ghost", Color.RED)


def test_available_colors_is_red_and_blue_only():
    lobby = Lobby()
    lobby.join("c1", "Alice")
    lobby.select_color("c1", Color.RED)
    available = lobby.available_colors()
    assert available == [Color.BLUE]


def test_can_start_with_one_human_and_two_bots():
    lobby = Lobby()
    assert not lobby.can_start()
    lobby.join("c1", "Alice")
    assert not lobby.can_start()       # humano sin color
    lobby.select_color("c1", Color.RED)
    assert lobby.can_start()           # 1 humano con color basta
```

- [ ] **Step 2: Ejecutar y verificar que pasa**

Run: `python -m pytest tests_server/test_lobby.py -v`
Expected: PASS.

- [ ] **Step 3: Commit (lo ejecuta el usuario)**

```bash
git add tests_server/test_lobby.py
```
Mensaje propuesto:
`test(lobby): ajustar pruebas al modelo 2 humanos + 2 bots fijos`

---

## Task 3: Protocolo — eliminar `add_bot` / `remove_bot`

**Files:**
- Modify: `server/protocol.py:44-49` (entradas en `COMMAND_SCHEMAS`)
- Test: `tests_server/test_protocol_bots.py` (reescritura)

- [ ] **Step 1: Reescribir el test**

Reemplaza **todo** el contenido de `tests_server/test_protocol_bots.py` por:

```python
"""add_bot/remove_bot ya no son comandos válidos del protocolo."""
from __future__ import annotations

import pytest

from server.protocol import ProtocolError, validate_command


def test_add_bot_is_unknown_type():
    with pytest.raises(ProtocolError, match="unknown type"):
        validate_command({"type": "add_bot"})


def test_remove_bot_is_unknown_type():
    with pytest.raises(ProtocolError, match="unknown type"):
        validate_command({"type": "remove_bot", "color": "green"})
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `python -m pytest tests_server/test_protocol_bots.py -v`
Expected: FAIL (hoy `add_bot`/`remove_bot` aún son válidos, no se lanza `ProtocolError`).

- [ ] **Step 3: Quitar las dos entradas de `COMMAND_SCHEMAS`**

En `server/protocol.py`, elimina estas dos líneas del dict `COMMAND_SCHEMAS`:

```python
    "add_bot":        {},
    "remove_bot":     {"color": str},
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `python -m pytest tests_server/test_protocol_bots.py -v`
Expected: PASS.

- [ ] **Step 5: Commit (lo ejecuta el usuario)**

```bash
git add server/protocol.py tests_server/test_protocol_bots.py
```
Mensaje propuesto:
`feat(protocol): eliminar comandos add_bot/remove_bot`

---

## Task 4: Server — quitar ramas de bots y reiniciar lobby sin humanos

**Files:**
- Modify: `server/server.py` (import línea 15; ramas `add_bot`/`remove_bot`; bloque `clear_bots` en `_on_disconnect`; rama `leave`; nuevo helper)
- Test: `tests_server/test_server_bots.py` (reescritura)

- [ ] **Step 1: Reescribir el test end-to-end**

Reemplaza **todo** el contenido de `tests_server/test_server_bots.py` por:

```python
"""End-to-end del servidor con el modelo de 2 humanos + 2 bots fijos."""
from __future__ import annotations

import random
import time

import pytest

from tests_server.conftest import inline_bot_delay


def _flush_welcome_and_lobby(client) -> list[dict]:
    return client.drain(expected_count=2, timeout=1.0)


def _send(client, msg: dict) -> None:
    client.send(msg)


# ----- lobby con bots fijos -----

def test_lobby_update_includes_two_fixed_bots(server_factory, client_factory):
    addr = server_factory(rng=random.Random(0))
    host = client_factory(*addr)
    _send(host, {"type": "join", "username": "Cris"})
    events = _flush_welcome_and_lobby(host)
    update = next(e for e in events if e["type"] == "lobby_update")
    bots = [p for p in update["players"] if p["is_bot"]]
    names = {p["username"] for p in bots}
    assert names == {"Camila", "Bryan"}
    assert any(p["is_bot"] is False for p in update["players"])


def test_add_bot_command_is_rejected(server_factory, client_factory):
    addr = server_factory(rng=random.Random(0))
    host = client_factory(*addr)
    _send(host, {"type": "join", "username": "Cris"})
    _flush_welcome_and_lobby(host)
    _send(host, {"type": "add_bot"})
    err = host.recv(timeout=1.0)
    assert err["type"] == "error"
    assert err["code"] == "BAD_MESSAGE"


def test_remove_bot_command_is_rejected(server_factory, client_factory):
    addr = server_factory(rng=random.Random(0))
    host = client_factory(*addr)
    _send(host, {"type": "join", "username": "Cris"})
    _flush_welcome_and_lobby(host)
    _send(host, {"type": "remove_bot", "color": "green"})
    err = host.recv(timeout=1.0)
    assert err["type"] == "error"
    assert err["code"] == "BAD_MESSAGE"


def test_third_human_rejected(server_factory, client_factory):
    addr = server_factory(rng=random.Random(0))
    h1 = client_factory(*addr)
    _send(h1, {"type": "join", "username": "Cris"})
    _flush_welcome_and_lobby(h1)
    h2 = client_factory(*addr)
    _send(h2, {"type": "join", "username": "Ana"})
    h2.drain(expected_count=2, timeout=1.0)
    h1.recv(timeout=1.0)  # lobby_update por el join de Ana
    h3 = client_factory(*addr)
    _send(h3, {"type": "join", "username": "Eve"})
    err = h3.recv(timeout=1.0)
    assert err["type"] == "error"
    assert err["code"] == "LOBBY_FULL"


# ----- inicio con 1 humano -----

def test_single_human_can_start_with_two_bots(server_factory, client_factory):
    addr = server_factory(rng=random.Random(123), bot_delay_fn=inline_bot_delay)
    host = client_factory(*addr)
    _send(host, {"type": "join", "username": "Cris"})
    _flush_welcome_and_lobby(host)
    _send(host, {"type": "select_color", "color": "red"})
    host.recv(timeout=1.0)
    _send(host, {"type": "start_game"})

    events = host.drain(timeout=2.0)
    types = [e.get("type") for e in events]
    assert "game_started" in types
    # los bots Camila/Bryan deben tirar inicial automáticamente
    initial_rolls = [e for e in events if e.get("type") == "initial_roll"]
    rollers = {e["username"] for e in initial_rolls}
    assert {"Camila", "Bryan"} & rollers


# ----- cierre del lobby al irse el último humano -----

def test_lobby_resets_when_last_human_leaves(server_factory, client_factory):
    """Tras irse el único humano, el lobby se reinicia limpio: sigue teniendo
    exactamente los 2 bots y el siguiente humano entra como host."""
    addr = server_factory(rng=random.Random(0))
    host = client_factory(*addr)
    _send(host, {"type": "join", "username": "Cris"})
    _flush_welcome_and_lobby(host)
    _send(host, {"type": "select_color", "color": "red"})
    host.recv(timeout=1.0)

    host.close()
    time.sleep(0.3)

    other = client_factory(*addr)
    _send(other, {"type": "join", "username": "Ana"})
    events = other.drain(expected_count=2, timeout=1.0)
    welcome = next(e for e in events if e["type"] == "welcome")
    assert welcome["is_host"] is True  # lobby limpio: Ana es host
    update = next(e for e in events if e["type"] == "lobby_update")
    bots = [p for p in update["players"] if p["is_bot"]]
    assert {p["username"] for p in bots} == {"Camila", "Bryan"}
    humans = [p for p in update["players"] if not p["is_bot"]]
    assert [p["username"] for p in humans] == ["Ana"]


def test_lobby_resets_on_in_game_disconnect(server_factory, client_factory):
    """Si el único humano deja una partida en curso, el server vuelve a LOBBY
    y un nuevo humano entra limpio (regresión del _reset_to_lobby existente)."""
    addr = server_factory(rng=random.Random(0), bot_delay_fn=inline_bot_delay)
    host = client_factory(*addr)
    _send(host, {"type": "join", "username": "Cris"})
    _flush_welcome_and_lobby(host)
    _send(host, {"type": "select_color", "color": "red"})
    host.recv(timeout=1.0)
    _send(host, {"type": "start_game"})
    host.drain(timeout=1.5)

    host.close()
    time.sleep(0.4)

    other = client_factory(*addr)
    _send(other, {"type": "join", "username": "Ana"})
    events = other.drain(expected_count=2, timeout=1.0)
    welcome = next(e for e in events if e["type"] == "welcome")
    assert welcome["is_host"] is True
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `python -m pytest tests_server/test_server_bots.py -v`
Expected: FAIL (las ramas `add_bot`/`remove_bot` aún responden `FORBIDDEN`, no `BAD_MESSAGE`; y el lobby tras reset aún se reinicia con `clear_bots`).

- [ ] **Step 3: Quitar `MAX_BOTS` del import e importar `LobbyFull`**

En `server/server.py` línea 15, cambia:

```python
from server.lobby import Lobby, MAX_BOTS, MAX_PLAYERS
```
por:
```python
from server.lobby import Lobby, LobbyFull
```

- [ ] **Step 3b: Mapear `LobbyFull` al código de error `LOBBY_FULL`**

En `server/server.py`, añade `LobbyFull` al dict `DOMAIN_ERROR_CODES` (líneas 32-36) para que el rechazo del 3.er humano llegue al cliente con código `LOBBY_FULL`:

```python
DOMAIN_ERROR_CODES = {
    DuplicatePlayer: "DUPLICATE_PLAYER",
    WrongPhase:      "WRONG_PHASE",
    InvalidMove:     "INVALID_MOVE",
    LobbyFull:       "LOBBY_FULL",
}
```

- [ ] **Step 4: Eliminar las ramas `add_bot` y `remove_bot`**

En `server/server.py`, dentro de `_dispatch_lobby`, elimina **completos** los dos bloques `elif t == "add_bot": ...` y `elif t == "remove_bot": ...` (actualmente líneas 383-428). Quedando la cadena: `... start_game ...` directamente seguido por `elif t == "leave":`.

- [ ] **Step 5: Reiniciar el lobby en la rama `leave`**

En `server/server.py`, la rama `leave` de `_dispatch_lobby` queda así:

```python
        elif t == "leave":
            self.lobby.leave(conn.conn_id)
            self.unregister_connection(conn.conn_id)
            self._reset_lobby_if_no_humans()
            self._broadcast_lobby(self._lobby_update())
```

- [ ] **Step 6: Reemplazar el bloque `clear_bots` en `_on_disconnect`**

En `server/server.py`, dentro de `_on_disconnect`, la rama `LOBBY` (actualmente líneas 157-165) queda así:

```python
            if self.phase is ServerPhase.LOBBY:
                self.lobby.leave(conn.conn_id)
                self.unregister_connection(conn.conn_id)
                # Si tras la salida no quedan humanos, el lobby se reinicia
                # limpio (vuelve a tener solo los 2 bots fijos).
                self._reset_lobby_if_no_humans()
                self._broadcast_lobby(self._lobby_update())
```

- [ ] **Step 7: Añadir el helper `_reset_lobby_if_no_humans`**

En `server/server.py`, justo después del método `_reset_to_lobby` (termina en `self.session = None`), añade:

```python
    def _reset_lobby_if_no_humans(self) -> None:
        """Si estamos en LOBBY y no queda ningún humano, descarta el lobby
        actual y crea uno nuevo (re-sembrado con los 2 bots fijos), listo para
        nuevos jugadores. Caller must hold `self.lock`."""
        if self.phase is not ServerPhase.LOBBY:
            return
        if any(not p.is_bot for p in self.lobby.players()):
            return
        logger.info("lobby sin humanos → reiniciando lobby")
        self.lobby = Lobby()
```

- [ ] **Step 8: Ejecutar y verificar que pasa**

Run: `python -m pytest tests_server/test_server_bots.py -v`
Expected: PASS.

- [ ] **Step 9: Commit (lo ejecuta el usuario)**

```bash
git add server/server.py tests_server/test_server_bots.py
```
Mensaje propuesto:
`feat(server): quitar add/remove bot y reiniciar lobby sin humanos`

---

## Task 5: Coherencia de nombres en `test_session_bots.py`

`GameSession` es genérico (no cambia), pero los datos de prueba usan "Bot Azul"/blue. Se actualizan a los bots fijos para reflejar el nuevo modelo.

**Files:**
- Test: `tests_server/test_session_bots.py:10-14`

- [ ] **Step 1: Actualizar el helper `_entries`**

En `tests_server/test_session_bots.py`, reemplaza la función `_entries` y los asserts que dependen de `blue`:

```python
def _entries() -> list[SessionEntry]:
    return [
        SessionEntry(conn_id="c1",        username="Cris",   color=Color.RED,   is_bot=False),
        SessionEntry(conn_id="bot:green", username="Camila", color=Color.GREEN, is_bot=True),
    ]
```

Y en los tests que referencian `"bot:blue"` / `"blue"`, cámbialos a `"bot:green"` / `"green"`:
- `test_bot_conn_ids_and_human_conn_ids_are_disjoint`: `session.bot_conn_ids() == ["bot:green"]`.
- `test_human_connected_count_does_not_count_bots_even_if_marked_disconnected`: `session.mark_disconnected("bot:green")`.
- `test_state_dict_propagates_is_bot_per_player`: `by_color["green"]["is_bot"] is True` (y deja `by_color["red"]["is_bot"] is False`).

- [ ] **Step 2: Ejecutar y verificar que pasa**

Run: `python -m pytest tests_server/test_session_bots.py -v`
Expected: PASS.

- [ ] **Step 3: Commit (lo ejecuta el usuario)**

```bash
git add tests_server/test_session_bots.py
```
Mensaje propuesto:
`test(session): usar bots fijos Camila/Bryan en datos de prueba`

---

## Task 6: Suite backend completa

**Files:** (ninguno nuevo — verificación)

- [ ] **Step 1: Ejecutar toda la suite backend**

Run: `python -m pytest tests/ tests_server/`
Expected: PASS, sin fallos. Si algún otro test (p.ej. `test_server.py`, `test_integration.py`) asumía el modelo viejo, ajústalo siguiendo el mismo patrón (lobby siempre con 2 bots; máx. 2 humanos; 1 humano puede iniciar). `tests_server/test_bot_runner.py` usa `SessionEntry("bot:blue", "Bot Azul", ...)` como dato libre de `GameSession` y **no requiere cambios** (no depende del lobby).

- [ ] **Step 2: Commit si hubo ajustes (lo ejecuta el usuario)**

```bash
git add tests_server/
```
Mensaje propuesto:
`test: alinear suite de servidor con el modelo de 2 humanos + 2 bots`

---

## Task 7: Cliente — quitar `ADD_BOT`/`REMOVE_BOT` y añadir `LOBBY_FULL`

**Files:**
- Modify: `client/src/types/protocol.ts` (enum `ClientCommandType` líneas 20-21; enum `ErrorCode` líneas 49-58; union `ClientCommand` líneas 75-76)
- Modify: `client/src/types/errorMessages.ts`

- [ ] **Step 1: Quitar del enum `ClientCommandType`**

En `client/src/types/protocol.ts`, elimina estas dos líneas:

```typescript
  ADD_BOT = 'add_bot',
  REMOVE_BOT = 'remove_bot',
```

- [ ] **Step 2: Quitar del union `ClientCommand`**

En el mismo archivo, elimina estas dos líneas del tipo `ClientCommand`:

```typescript
  | { type: ClientCommandType.ADD_BOT }
  | { type: ClientCommandType.REMOVE_BOT; color: Color }
```

- [ ] **Step 2b: Añadir el código de error `LOBBY_FULL`**

En el mismo archivo, dentro del enum `ErrorCode`, añade la entrada (p.ej. tras `FORBIDDEN`):

```typescript
  LOBBY_FULL = 'LOBBY_FULL',
```

- [ ] **Step 2c: Añadir mensaje amigable para `LOBBY_FULL`**

En `client/src/types/errorMessages.ts`, añade la entrada al mapa `FRIENDLY_MESSAGES`:

```typescript
const FRIENDLY_MESSAGES: Partial<Record<ErrorCode, string>> = {
  [ErrorCode.DUPLICATE_PLAYER]: 'Ese nombre ya está en uso',
  [ErrorCode.LOBBY_FULL]: 'La sala ya tiene 2 jugadores',
};
```

- [ ] **Step 3: Verificar tipos (fallará por usos en store/página)**

Run: `cd client && npm run typecheck`
Expected: FAIL — `stores/lobby.ts` y `pages/LobbyPage.vue` aún referencian los miembros eliminados. Se arreglan en Tasks 8 y 9.

(Sin commit aquí: se commitea junto con el store y la página tras dejar el typecheck en verde, al final de Task 9.)

---

## Task 8: Cliente — store `lobby.ts` sin add/remove bot y `canStart` corregido

**Files:**
- Modify: `client/src/stores/lobby.ts`
- Test: `client/src/stores/lobby.test.ts`

- [ ] **Step 1: Actualizar el test del store**

Reemplaza **todo** el contenido de `client/src/stores/lobby.test.ts` por:

```typescript
import { setActivePinia, createPinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useLobbyStore } from './lobby';
import { Color } from 'src/types/domain';

describe('lobbyStore', () => {
  beforeEach(() => setActivePinia(createPinia()));

  it('starts empty', () => {
    const s = useLobbyStore();
    expect(s.players).toEqual([]);
    expect(s.isHost).toBe(false);
    expect(s.myColor).toBeNull();
  });

  it('canStart requires >=1 human and every player to have a color', () => {
    const s = useLobbyStore();
    expect(s.canStart).toBe(false);
    // 2 bots con color + 1 humano sin color -> false
    s.updateFromLobbyUpdate(
      [
        { username: 'Camila', color: Color.GREEN,  is_bot: true  },
        { username: 'Bryan',  color: Color.YELLOW, is_bot: true  },
        { username: 'A',      color: null,         is_bot: false },
      ],
      [Color.RED, Color.BLUE],
    );
    expect(s.canStart).toBe(false);
    // humano con color -> true (1 humano basta)
    s.updateFromLobbyUpdate(
      [
        { username: 'Camila', color: Color.GREEN,  is_bot: true  },
        { username: 'Bryan',  color: Color.YELLOW, is_bot: true  },
        { username: 'A',      color: Color.RED,    is_bot: false },
      ],
      [Color.BLUE],
    );
    expect(s.canStart).toBe(true);
  });

  it('canStart is false when there are only bots', () => {
    const s = useLobbyStore();
    s.updateFromLobbyUpdate(
      [
        { username: 'Camila', color: Color.GREEN,  is_bot: true },
        { username: 'Bryan',  color: Color.YELLOW, is_bot: true },
      ],
      [Color.RED, Color.BLUE],
    );
    expect(s.canStart).toBe(false);
  });

  it('reset clears state', () => {
    const s = useLobbyStore();
    s.isHost = true;
    s.myColor = Color.RED;
    s.reset();
    expect(s.isHost).toBe(false);
    expect(s.myColor).toBeNull();
  });

  it('stores is_bot flag from lobby_update', () => {
    const s = useLobbyStore();
    s.updateFromLobbyUpdate(
      [
        { username: 'Cris',   color: Color.RED,   is_bot: false },
        { username: 'Camila', color: Color.GREEN, is_bot: true  },
      ],
      [Color.BLUE],
    );
    expect(s.players[1]!.is_bot).toBe(true);
    expect(s.players[0]!.is_bot).toBe(false);
  });
});
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `cd client && npx vitest run src/stores/lobby.test.ts`
Expected: FAIL (`canStart` actual exige `length >= 2` sin requerir humano; el caso "solo bots" daría `true`).

- [ ] **Step 3: Reescribir `client/src/stores/lobby.ts`**

Reemplaza **todo** el contenido de `client/src/stores/lobby.ts` por:

```typescript
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { Color, LobbyPlayerDto } from 'src/types/domain';

export const useLobbyStore = defineStore('lobby', () => {
  const players         = ref<LobbyPlayerDto[]>([]);
  const availableColors = ref<Color[]>([]);
  const isHost          = ref<boolean>(false);
  const myColor         = ref<Color | null>(null);

  // Puede iniciar si hay al menos 1 humano y todos los jugadores (humanos y
  // bots) tienen color. Los 2 bots fijos ya vienen con color.
  const canStart = computed<boolean>(() =>
    players.value.some(p => !p.is_bot) &&
    players.value.every(p => p.color !== null),
  );

  function updateFromLobbyUpdate(
    newPlayers: LobbyPlayerDto[],
    newAvailable: Color[],
  ): void {
    players.value = newPlayers;
    availableColors.value = newAvailable;
  }

  function reset(): void {
    players.value = [];
    availableColors.value = [];
    isHost.value = false;
    myColor.value = null;
  }

  return { players, availableColors, isHost, myColor, canStart,
           updateFromLobbyUpdate, reset };
});
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `cd client && npx vitest run src/stores/lobby.test.ts`
Expected: PASS.

(Sin commit aquí: el typecheck global sigue rojo por `LobbyPage.vue`. Se commitea al final de Task 9.)

---

## Task 9: Cliente — `LobbyPage.vue` sin UI de añadir/quitar bot

**Files:**
- Modify: `client/src/pages/LobbyPage.vue`

- [ ] **Step 1: Quitar el botón "Quitar bot" de la lista de jugadores**

En `client/src/pages/LobbyPage.vue`, elimina el bloque `<q-item-section side ...>` que renderiza el botón de quitar bot (actualmente líneas 23-34):

```html
              <q-item-section side v-if="lobby.isHost && p.is_bot && p.color">
                <q-btn
                  flat
                  dense
                  round
                  icon="close"
                  size="sm"
                  color="negative"
                  :aria-label="`Quitar ${p.username}`"
                  @click="onRemoveBot(p.color)"
                />
              </q-item-section>
```

- [ ] **Step 2: Quitar el botón "Agregar bot"**

En el bloque del host (actualmente líneas 52-63), déjalo así (solo el botón de iniciar):

```html
        <div v-if="lobby.isHost" class="row q-gutter-sm items-center">
          <q-btn color="positive" size="lg" :disable="!lobby.canStart" @click="onStart">
            Iniciar partida
          </q-btn>
        </div>
        <div v-else class="text-caption">Esperando al host…</div>
```

- [ ] **Step 3: Quitar el código de bots del `<script setup>`**

En `client/src/pages/LobbyPage.vue`, elimina:

- Las constantes `MAX_BOTS` y `MAX_PLAYERS` (líneas 139-140).
- El `computed` `canAddBot` (líneas 220-225).
- Las funciones `onAddBot` y `onRemoveBot` (líneas 227-233).

Verifica que ya no quede ninguna referencia a `canAddBot`, `onAddBot`, `onRemoveBot`, `addBot`, `removeBot`, `MAX_BOTS`, `MAX_PLAYERS` en el archivo. El import de `computed` se mantiene solo si sigue usándose; si tras quitar `canAddBot` ya no hay otros `computed`, cámbialo a `import { onMounted } from 'vue';`.

- [ ] **Step 4: Verificar tipos en verde**

Run: `cd client && npm run typecheck`
Expected: PASS (ya no hay referencias a `ADD_BOT`/`REMOVE_BOT` ni a métodos eliminados).

- [ ] **Step 5: Ejecutar lint y tests del cliente**

Run: `cd client && npm run lint && npm test`
Expected: PASS.

- [ ] **Step 6: Commit del cliente completo (lo ejecuta el usuario)**

```bash
git add client/src/types/protocol.ts client/src/types/errorMessages.ts client/src/stores/lobby.ts client/src/stores/lobby.test.ts client/src/pages/LobbyPage.vue
```
Mensaje propuesto:
`feat(client): eliminar UI/lógica de añadir y quitar bots; código LOBBY_FULL`

---

## Task 10: Verificación final de extremo a extremo

**Files:** (ninguno — verificación global)

- [ ] **Step 1: Backend completo**

Run: `python -m pytest tests/ tests_server/`
Expected: PASS, sin fallos.

- [ ] **Step 2: Cliente completo**

Run: `cd client && npm run typecheck && npm run lint && npm test`
Expected: PASS.

- [ ] **Step 3: Humo manual (opcional pero recomendado)**

1. `python -m server --log-level INFO`
2. `cd client && npm run dev`
3. En el navegador: conecta como un humano → en el lobby aparecen **Camila (verde)** y **Bryan (amarillo)**; solo se ofrecen colores **rojo** y **azul**; **no** hay botones de agregar/quitar bot.
4. Selecciona color e **inicia con 1 humano** → la partida arranca con 3 jugadores (tú + 2 bots) y los bots juegan sus turnos.
5. Abre una segunda pestaña como otro humano → entra como 2.º jugador (4 en total). Un tercer humano debe ser rechazado.
6. Sal del lobby siendo el único humano y vuelve a entrar → el lobby está limpio (solo los 2 bots) y entras como host.

- [ ] **Step 4: Commit final si aplica (lo ejecuta el usuario)**

No deberían quedar cambios sin commitear. Si los hay, agrúpalos con un mensaje descriptivo y deja que el usuario commitee.

---

## Notas de cobertura del spec

- Máx. 2 humanos → Task 1 (`MAX_HUMANS`, `join`), Task 4 (`LOBBY_FULL` e2e).
- 2 bots fijos Camila/Bryan desde el inicio → Task 1 (`_seed_bots`, `FIXED_BOTS`), Task 4 (lobby_update).
- Colores intercalados GREEN/YELLOW bots, RED/BLUE humanos → Task 1 (`available_colors`, select_color rechaza color de bot).
- 1 humano puede iniciar → Task 1 (`can_start`), Task 4 (e2e), Task 8 (`canStart` cliente).
- Eliminar `add_bot`/`remove_bot` → Task 3 (protocolo), Task 4 (server), Task 7 (tipos cliente), Tasks 8-9 (store/página).
- Reinicio limpio del lobby al irse el último humano → Task 4 (`_reset_lobby_if_no_humans`, e2e LOBBY e IN_GAME).
