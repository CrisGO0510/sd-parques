# Parqués Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **IMPORTANT:** el usuario maneja todos los commits de git. Los subagentes **no** ejecutan `git add`, `git commit`, `git branch` ni ninguna operación git que mute el repo. Donde este plan muestre "git commit", reemplazar por "reportar el diff al controlador". Solo se permiten comandos de lectura (`git status`, `git diff`, `git log`).

**Goal:** Implementar un servidor TCP en Python 3.11+ que expone el motor `core/` a múltiples clientes con `socket` + `threading`, ciclo de vida LOBBY→IN_GAME→CLOSED, protocolo JSON por líneas, y suite de tests en `tests_server/` con ≥90% de cobertura.

**Architecture:** Paquete plano `server/` con módulos por responsabilidad (protocol, connection, lobby, session, server, `__main__`). Un `threading.Lock` global protege lobby + session + fase. Un hilo principal hace `accept()`; cada cliente tiene su hilo daemon. Dispatch de mensajes y emisión de eventos ocurren dentro del lock para preservar orden.

**Tech Stack:** Python 3.11+ stdlib (`socket`, `threading`, `queue`, `json`, `logging`, `argparse`), `pytest>=8.0` (dev-only). Consume `core/` del módulo #1 (ya instalado como paquete editable).

**Spec:** `docs/superpowers/specs/2026-04-20-parques-server-design.md`

---

## File Structure

```
sd-parques/
├── core/                           # motor (intacto)
├── server/                         # NUEVO
│   ├── __init__.py                 # re-exports públicos
│   ├── protocol.py                 # constantes, encode/decode, validate, ProtocolError
│   ├── connection.py               # ClientConnection (socket + buffer + send)
│   ├── lobby.py                    # Lobby (join/host/select_color/can_start)
│   ├── session.py                  # GameSession (wrap de core.Game + conns)
│   ├── server.py                   # Server (accept loop + lock + dispatch)
│   └── __main__.py                 # CLI + logging
├── tests/                          # tests del motor (existentes)
├── tests_server/                   # NUEVO
│   ├── __init__.py
│   ├── conftest.py                 # ScriptedRandom import + fixtures server_factory, TestClient
│   ├── test_protocol.py            # encode/decode/validate
│   ├── test_lobby.py               # Lobby aislado
│   ├── test_session.py             # GameSession aislada
│   └── test_integration.py         # E2E: sockets reales, partida scripted
└── pyproject.toml                  # ajustar include y addopts si hace falta
```

**Responsabilidades de cada archivo:**

| Archivo | Una responsabilidad |
|---|---|
| `protocol.py` | Serialización y validación de mensajes. Sin estado. |
| `connection.py` | Wrapper de un socket: readline bufferizado, send atómico. Sin lógica de juego. |
| `lobby.py` | Estado del lobby antes de iniciar partida. No conoce sockets. |
| `session.py` | Estado de la partida activa: wrap `core.Game`, mapping color↔conn, disconnected set. No conoce sockets. |
| `server.py` | Orquestador: accept loop, lock global, dispatch, emit eventos. Conoce sockets y todo lo demás. |
| `__main__.py` | CLI + bootstrap de logging. Nada más. |

---

## Task 1: Scaffold del servidor

**Files:**
- Create: `server/__init__.py`, `server/__main__.py` (stub), `tests_server/__init__.py`, `tests_server/conftest.py` (stub)
- Modify: `pyproject.toml`

- [ ] **Step 1: Crear directorios y `__init__.py` vacíos**

```bash
mkdir -p server tests_server
touch server/__init__.py tests_server/__init__.py
```

- [ ] **Step 2: `server/__main__.py` stub mínimo**

```python
"""Entry point for the parqués TCP server."""


def main() -> int:
    raise NotImplementedError("Task 15 will implement this.")


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: `tests_server/conftest.py` stub mínimo**

```python
"""Shared fixtures for server tests."""
```

(Los fixtures reales los agrega la Task 14.)

- [ ] **Step 4: Ajustar `pyproject.toml`**

Cambiar:
```toml
[tool.setuptools.packages.find]
include = ["core*"]
exclude = ["tests*", "_legacy*"]
```

Por:
```toml
[tool.setuptools.packages.find]
include = ["core*", "server*"]
exclude = ["tests*", "tests_server*", "_legacy*"]
```

Y en `[tool.pytest.ini_options]` cambiar:
```toml
testpaths = ["tests"]
```

Por:
```toml
testpaths = ["tests", "tests_server"]
```

- [ ] **Step 5: Reinstalar paquete editable**

```bash
.venv/bin/pip install -e '.[dev]' -q
```

- [ ] **Step 6: Verificar no-regresión**

```bash
.venv/bin/pytest -q
```

Expected: `67 passed` (los tests del motor siguen verdes; aún no hay tests de server).

- [ ] **Step 7: Reportar diff (el usuario commite)**

---

## Task 2: `protocol.py` — encode / decode

**Files:**
- Create: `server/protocol.py`, `tests_server/test_protocol.py`

- [ ] **Step 1: Escribir tests de encode/decode**

`tests_server/test_protocol.py`:
```python
import pytest
from server.protocol import (
    ProtocolError, encode, decode,
)


def test_encode_serializes_and_appends_newline():
    payload = {"type": "ping", "n": 1}
    result = encode(payload)
    assert result.endswith(b"\n")
    assert b'"type":"ping"' in result or b'"type": "ping"' in result


def test_decode_parses_valid_json():
    assert decode(b'{"type":"ping"}\n') == {"type": "ping"}


def test_decode_strips_trailing_whitespace():
    assert decode(b'  {"type":"ping"}  \n') == {"type": "ping"}


def test_decode_rejects_non_json():
    with pytest.raises(ProtocolError, match="JSON"):
        decode(b"not json\n")


def test_decode_rejects_non_object():
    with pytest.raises(ProtocolError, match="object"):
        decode(b'[1, 2, 3]\n')


def test_decode_rejects_empty_line():
    with pytest.raises(ProtocolError):
        decode(b"\n")
```

- [ ] **Step 2: Verificar fallos**

```bash
.venv/bin/pytest tests_server/test_protocol.py -v
```
Expected: `ImportError: cannot import name 'ProtocolError'`.

- [ ] **Step 3: Implementar `server/protocol.py`**

```python
"""Protocol: JSON-per-line messages, encode / decode / validate."""
from __future__ import annotations

import json
from typing import Any


class ProtocolError(ValueError):
    """Raised when an incoming message is malformed or invalid."""


def encode(message: dict[str, Any]) -> bytes:
    """Serialize a dict to a single NDJSON line terminated by '\\n'."""
    return (json.dumps(message, separators=(",", ":")) + "\n").encode("utf-8")


def decode(raw: bytes) -> dict[str, Any]:
    """Parse a single NDJSON line into a dict.

    Raises ProtocolError on malformed or non-object payloads.
    """
    text = raw.strip()
    if not text:
        raise ProtocolError("empty line")
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as e:
        raise ProtocolError(f"not valid JSON: {e}") from e
    if not isinstance(obj, dict):
        raise ProtocolError(f"message must be a JSON object, got {type(obj).__name__}")
    return obj
```

- [ ] **Step 4: Verificar que pasan**

```bash
.venv/bin/pytest tests_server/test_protocol.py -v
```
Expected: `6 passed`.

- [ ] **Step 5: Reportar diff**

---

## Task 3: `protocol.py` — validación de comandos

**Files:**
- Modify: `server/protocol.py`
- Modify: `tests_server/test_protocol.py`

Regla: un `validate(msg)` que chequea `type` contra lista blanca y **campos requeridos por tipo**. Lanza `ProtocolError` con mensaje preciso. No verifica semántica (fase, turno, etc.) — solo shape.

- [ ] **Step 1: Extender tests**

Añadir a `tests_server/test_protocol.py`:
```python
from server.protocol import validate_command, COMMAND_SCHEMAS


def test_validate_accepts_join_with_username():
    validate_command({"type": "join", "username": "Alice"})  # no raises


def test_validate_rejects_unknown_type():
    with pytest.raises(ProtocolError, match="unknown type"):
        validate_command({"type": "dance"})


def test_validate_rejects_missing_type():
    with pytest.raises(ProtocolError, match="'type'"):
        validate_command({})


def test_validate_rejects_join_without_username():
    with pytest.raises(ProtocolError, match="username"):
        validate_command({"type": "join"})


def test_validate_rejects_wrong_field_type():
    with pytest.raises(ProtocolError, match="str"):
        validate_command({"type": "join", "username": 42})


def test_validate_accepts_move_piece_with_three_fields():
    validate_command({
        "type": "move_piece",
        "piece_index": 0,
        "dice_value": 3,
        "action": "advance",
    })


def test_validate_rejects_move_piece_missing_field():
    with pytest.raises(ProtocolError, match="dice_value"):
        validate_command({"type": "move_piece", "piece_index": 0, "action": "advance"})


def test_all_commands_have_schema():
    # Sanity: the schema table is non-empty and contains known types.
    assert "join" in COMMAND_SCHEMAS
    assert "roll_dice" in COMMAND_SCHEMAS
```

- [ ] **Step 2: Fail**

```bash
.venv/bin/pytest tests_server/test_protocol.py -v
```
Expected: fallan los tests nuevos (no existe `validate_command` / `COMMAND_SCHEMAS`).

- [ ] **Step 3: Extender `server/protocol.py`**

Añadir (después de `decode`):
```python
# Command schemas: maps type → {field_name: expected_type}.
# Empty dict means "no fields required beyond type".
COMMAND_SCHEMAS: dict[str, dict[str, type]] = {
    "join":         {"username": str},
    "select_color": {"color": str},
    "start_game":   {},
    "roll_initial": {},
    "roll_dice":    {},
    "move_piece":   {"piece_index": int, "dice_value": int, "action": str},
    "skip_turn":    {},
    "crown_piece":  {"piece_index": int},
    "leave":        {},
}


def validate_command(msg: dict[str, Any]) -> None:
    """Validate an incoming command's shape.

    Raises ProtocolError if type is missing/unknown or required fields
    are missing or of the wrong type.
    """
    msg_type = msg.get("type")
    if msg_type is None:
        raise ProtocolError("missing 'type' field")
    if msg_type not in COMMAND_SCHEMAS:
        raise ProtocolError(f"unknown type: {msg_type}")
    schema = COMMAND_SCHEMAS[msg_type]
    for field, expected in schema.items():
        if field not in msg:
            raise ProtocolError(f"{msg_type}: missing field '{field}'")
        if not isinstance(msg[field], expected):
            raise ProtocolError(
                f"{msg_type}.{field}: expected {expected.__name__}, "
                f"got {type(msg[field]).__name__}"
            )
```

- [ ] **Step 4: Pass**

```bash
.venv/bin/pytest tests_server/test_protocol.py -v
```
Expected: todos los tests pasan (≥14 tests en este archivo).

- [ ] **Step 5: Reportar diff**

---

## Task 4: `lobby.py` — join, host, rechazos

**Files:**
- Create: `server/lobby.py`, `tests_server/test_lobby.py`

Regla: `Lobby` aislado (sin sockets). Almacena jugadores con un `conn_id` opaco (en los tests puede ser una string; en el server real será un id de `ClientConnection`). El primer joiner es host; duplicates lanzan excepción; 5to join falla.

- [ ] **Step 1: Escribir tests**

`tests_server/test_lobby.py`:
```python
import pytest

from server.lobby import Lobby, LobbyFull, LobbyError
from core.exceptions import DuplicatePlayer


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


def test_rejects_fifth_joiner():
    lobby = Lobby()
    for i, name in enumerate(["A", "B", "C", "D"]):
        lobby.join(f"c{i}", name)
    with pytest.raises(LobbyFull):
        lobby.join("c5", "E")


def test_leave_removes_player():
    lobby = Lobby()
    lobby.join("c1", "Alice")
    lobby.join("c2", "Bob")
    lobby.leave("c1")
    assert not lobby.has_conn("c1")
    assert lobby.has_conn("c2")


def test_leave_promotes_next_host():
    lobby = Lobby()
    lobby.join("c1", "Alice")  # host
    lobby.join("c2", "Bob")
    lobby.leave("c1")
    assert lobby.host_conn_id() == "c2"


def test_leave_nonexistent_is_noop():
    lobby = Lobby()
    lobby.leave("unknown")  # does not raise


def test_players_returns_snapshot_in_join_order():
    lobby = Lobby()
    lobby.join("c1", "Alice")
    lobby.join("c2", "Bob")
    names = [p.username for p in lobby.players()]
    assert names == ["Alice", "Bob"]
```

- [ ] **Step 2: Fail**

```bash
.venv/bin/pytest tests_server/test_lobby.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implementar `server/lobby.py`**

```python
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
```

- [ ] **Step 4: Pass**

```bash
.venv/bin/pytest tests_server/test_lobby.py -v
```
Expected: 8 passed.

- [ ] **Step 5: Reportar diff**

---

## Task 5: `lobby.py` — select_color, can_start

**Files:**
- Modify: `server/lobby.py`, `tests_server/test_lobby.py`

- [ ] **Step 1: Extender tests**

Añadir a `tests_server/test_lobby.py`:
```python
from core.entities import Color


def test_select_color_assigns():
    lobby = Lobby()
    lobby.join("c1", "Alice")
    lobby.select_color("c1", Color.RED)
    assert lobby.get_by_conn("c1").color is Color.RED


def test_select_color_rejects_duplicate():
    lobby = Lobby()
    lobby.join("c1", "Alice")
    lobby.join("c2", "Bob")
    lobby.select_color("c1", Color.RED)
    with pytest.raises(DuplicatePlayer, match="color"):
        lobby.select_color("c2", Color.RED)


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


def test_available_colors_excludes_taken():
    lobby = Lobby()
    lobby.join("c1", "Alice")
    lobby.select_color("c1", Color.RED)
    available = lobby.available_colors()
    assert Color.RED not in available
    assert Color.BLUE in available


def test_can_start_requires_min_two_with_color():
    lobby = Lobby()
    assert not lobby.can_start()
    lobby.join("c1", "Alice")
    lobby.select_color("c1", Color.RED)
    assert not lobby.can_start()  # only 1 player
    lobby.join("c2", "Bob")
    assert not lobby.can_start()  # Bob has no color
    lobby.select_color("c2", Color.BLUE)
    assert lobby.can_start()
```

- [ ] **Step 2: Fail**

- [ ] **Step 3: Extender `server/lobby.py`**

```python
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
```

- [ ] **Step 4: Pass**

```bash
.venv/bin/pytest tests_server/test_lobby.py -v
```
Expected: 14 passed.

- [ ] **Step 5: Reportar diff**

---

## Task 6: `session.py` — GameSession wrap básico

**Files:**
- Create: `server/session.py`, `tests_server/test_session.py`

Regla: `GameSession` envuelve `core.Game` y mapea `conn_id ↔ color`. Delega las operaciones al motor; encapsula `disconnected` set.

- [ ] **Step 1: Tests**

`tests_server/test_session.py`:
```python
import pytest

from server.session import GameSession
from core.entities import Color, GamePhase, PieceState
from tests.conftest import ScriptedRandom


def _make_session(rng: ScriptedRandom | None = None) -> GameSession:
    return GameSession(
        entries=[
            ("c1", "Alice", Color.RED),
            ("c2", "Bob",   Color.BLUE),
        ],
        rng=rng or ScriptedRandom([]),
    )


def test_session_creates_game_in_setup_phase():
    session = _make_session()
    assert session.game.phase is GamePhase.SETUP
    assert session.color_for_conn("c1") is Color.RED
    assert session.conn_for_color(Color.BLUE) == "c2"


def test_session_unknown_conn_returns_none():
    session = _make_session()
    assert session.color_for_conn("ghost") is None
    assert session.conn_for_color(Color.GREEN) is None


def test_roll_initial_delegates_to_engine():
    rng = ScriptedRandom([6, 5, 3, 4])  # Alice=11, Bob=7
    session = _make_session(rng)
    alice_idx = session.player_index_for_conn("c1")
    bob_idx = session.player_index_for_conn("c2")
    assert session.roll_initial(alice_idx) == 11
    assert session.roll_initial(bob_idx) == 7
    assert session.game.phase is GamePhase.ROLLING


def test_current_turn_conn_id():
    rng = ScriptedRandom([6, 5, 3, 4])
    session = _make_session(rng)
    session.roll_initial(0)
    session.roll_initial(1)
    # Alice (c1) won the initial roll, so turn_order[0] is Alice's index.
    assert session.current_turn_conn_id() == "c1"


def test_state_dict_excludes_rng():
    session = _make_session()
    state = session.state_dict()
    assert "_rng" not in state
    assert "phase" in state
    assert "players" in state
```

- [ ] **Step 2: Fail**

- [ ] **Step 3: Implementar `server/session.py`**

```python
"""GameSession: wraps core.Game with conn↔color mapping."""
from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field

from core import engine
from core.entities import Color, Game


@dataclass
class GameSession:
    entries: list[tuple[str, str, Color]]  # (conn_id, username, color) in join order
    rng: random.Random | None = None
    game: Game = field(init=False)
    _conn_by_color: dict[Color, str] = field(init=False)
    _color_by_conn: dict[str, Color] = field(init=False)
    disconnected_colors: set[Color] = field(default_factory=set, init=False)

    def __post_init__(self) -> None:
        self.game = engine.new_game(
            [(username, color) for _, username, color in self.entries],
            rng=self.rng,
        )
        self._conn_by_color = {color: conn_id for conn_id, _, color in self.entries}
        self._color_by_conn = {conn_id: color for conn_id, _, color in self.entries}

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

    # ---- engine delegation ----

    def roll_initial(self, player_index: int) -> int:
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

    # ---- serialization ----

    def state_dict(self) -> dict:
        """Return the Game as a JSON-serializable dict (without _rng)."""
        d = asdict(self.game)
        # asdict already strips non-field attributes like _rng.
        return d
```

- [ ] **Step 4: Pass**

```bash
.venv/bin/pytest tests_server/test_session.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Reportar diff**

---

## Task 7: `session.py` — desconexión y auto-skip

**Files:**
- Modify: `server/session.py`, `tests_server/test_session.py`

Regla: cuando una conexión se marca disconnected, sus turnos se saltan automáticamente. Exponer un `advance_past_disconnected()` helper que el Server llama tras cada mutación para que el turno "salte" sobre desconectados.

- [ ] **Step 1: Tests**

Añadir a `tests_server/test_session.py`:
```python
from core.entities import GamePhase, Move, MoveAction


def test_mark_disconnected_stores_color():
    session = _make_session()
    session.mark_disconnected("c1")
    assert Color.RED in session.disconnected_colors


def test_connected_count():
    session = _make_session()
    assert session.connected_count() == 2
    session.mark_disconnected("c1")
    assert session.connected_count() == 1


def test_advance_past_disconnected_skips_rolling():
    rng = ScriptedRandom([6, 5, 3, 4])
    session = _make_session(rng)
    session.roll_initial(0)  # Alice=11
    session.roll_initial(1)  # Bob=7 → Alice first
    assert session.current_turn_conn_id() == "c1"
    # Alice disconnects.
    session.mark_disconnected("c1")
    session.advance_past_disconnected()
    # Should have advanced to Bob (c2).
    assert session.current_turn_conn_id() == "c2"


def test_advance_past_disconnected_stops_if_all_disconnected():
    rng = ScriptedRandom([6, 5, 3, 4])
    session = _make_session(rng)
    session.roll_initial(0)
    session.roll_initial(1)
    session.mark_disconnected("c1")
    session.mark_disconnected("c2")
    # No one left; the session signals game cannot continue.
    assert not session.advance_past_disconnected()
    assert session.connected_count() == 0
```

- [ ] **Step 2: Fail**

- [ ] **Step 3: Ampliar `server/session.py`**

```python
from core.entities import GamePhase, PieceState


    def mark_disconnected(self, conn_id: str) -> None:
        color = self.color_for_conn(conn_id)
        if color is not None:
            self.disconnected_colors.add(color)

    def connected_count(self) -> int:
        return sum(
            1 for color in self._color_by_conn.values()
            if color not in self.disconnected_colors
        )

    def _current_color(self) -> Color | None:
        if not self.game.turn_order:
            return None
        idx = self.game.turn_order[self.game.current_turn_index]
        return self.game.players[idx].color

    def connected_conn_ids(self) -> list[str]:
        """Public accessor so the Server can iterate without reaching for _color_by_conn."""
        return [
            conn_id for conn_id, color in self._color_by_conn.items()
            if color not in self.disconnected_colors
        ]

    def all_conn_ids(self) -> list[str]:
        """Every conn_id registered in this session (connected or not)."""
        return list(self._color_by_conn.keys())

    def advance_past_disconnected(self) -> bool:
        """If current turn belongs to a disconnected color, advance until
        it belongs to a connected one (or return False if everyone's out).

        Returns True if a connected player now holds the turn, False otherwise.
        """
        if self.connected_count() == 0:
            return False
        for _ in range(len(self.game.turn_order)):
            current_color = self._current_color()
            if current_color is None:
                return False
            if current_color not in self.disconnected_colors:
                return True
            # Advance one turn; mimic engine._advance_turn behavior.
            self.game.consecutive_pairs = 0
            self.game.initial_rolls_remaining = 0
            self.game.current_turn_index = (
                self.game.current_turn_index + 1
            ) % len(self.game.turn_order)
            self.game.phase = GamePhase.ROLLING
        return False  # all disconnected in this rotation
```

- [ ] **Step 4: Pass**

```bash
.venv/bin/pytest tests_server/test_session.py -v
```

- [ ] **Step 5: Reportar diff**

---

## Task 8: `connection.py` — ClientConnection con readline buffer

**Files:**
- Create: `server/connection.py`, `tests_server/test_connection.py`

Regla: envoltorio de un socket TCP con un buffer para dividir por `\n`. Tests con sockets reales en `localhost` puerto 0.

- [ ] **Step 1: Tests**

`tests_server/test_connection.py`:
```python
import socket
import threading

import pytest

from server.connection import ClientConnection


def _pair():
    """Create a connected socket pair (server_side, client_side) via a listener."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    host, port = listener.getsockname()
    client = socket.create_connection((host, port))
    server_side, _ = listener.accept()
    listener.close()
    return server_side, client


def test_readline_returns_complete_message():
    server_side, client = _pair()
    try:
        conn = ClientConnection(server_side, conn_id="c1")
        client.sendall(b'{"type":"ping"}\n')
        line = conn.readline()
        assert line == b'{"type":"ping"}\n'
    finally:
        server_side.close()
        client.close()


def test_readline_handles_partial_then_complete():
    server_side, client = _pair()
    try:
        conn = ClientConnection(server_side, conn_id="c1")
        client.sendall(b'{"type":')
        client.sendall(b'"ping"}\n')
        line = conn.readline()
        assert line == b'{"type":"ping"}\n'
    finally:
        server_side.close()
        client.close()


def test_readline_handles_two_messages_in_one_chunk():
    server_side, client = _pair()
    try:
        conn = ClientConnection(server_side, conn_id="c1")
        client.sendall(b'{"type":"a"}\n{"type":"b"}\n')
        first = conn.readline()
        second = conn.readline()
        assert first == b'{"type":"a"}\n'
        assert second == b'{"type":"b"}\n'
    finally:
        server_side.close()
        client.close()


def test_readline_returns_empty_on_clean_close():
    server_side, client = _pair()
    try:
        conn = ClientConnection(server_side, conn_id="c1")
        client.close()
        line = conn.readline()
        assert line == b""
    finally:
        server_side.close()


def test_send_writes_full_message():
    server_side, client = _pair()
    try:
        conn = ClientConnection(server_side, conn_id="c1")
        conn.send(b'{"type":"welcome"}\n')
        received = client.recv(1024)
        assert received == b'{"type":"welcome"}\n'
    finally:
        server_side.close()
        client.close()
```

- [ ] **Step 2: Fail**

- [ ] **Step 3: Implementar `server/connection.py`**

```python
"""ClientConnection: per-socket wrapper with line-buffered read."""
from __future__ import annotations

import socket
import threading


class ClientConnection:
    """Wraps a connected TCP socket.

    Provides readline() (blocks until a newline-terminated line or EOF is received)
    and send() (atomic sendall).
    """

    def __init__(self, sock: socket.socket, *, conn_id: str):
        self.sock = sock
        self.conn_id = conn_id
        self._buffer = b""
        self._send_lock = threading.Lock()

    def readline(self) -> bytes:
        """Return the next line (including \\n) or b"" on EOF.

        Raises whatever socket.recv raises on errors.
        """
        while b"\n" not in self._buffer:
            chunk = self.sock.recv(4096)
            if not chunk:
                # Clean EOF: return anything leftover in the buffer without a newline
                # as empty (we don't deliver incomplete lines — that'd be protocol bug).
                self._buffer = b""
                return b""
            self._buffer += chunk
        line, self._buffer = self._buffer.split(b"\n", 1)
        return line + b"\n"

    def send(self, data: bytes) -> None:
        """Atomically send all bytes. Thread-safe for concurrent emits."""
        with self._send_lock:
            self.sock.sendall(data)

    def close(self) -> None:
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.sock.close()
```

- [ ] **Step 4: Pass**

```bash
.venv/bin/pytest tests_server/test_connection.py -v
```

- [ ] **Step 5: Reportar diff**

---

## Task 9: `server.py` — construcción + fase LOBBY + lock global

**Files:**
- Create: `server/server.py`
- Modify: `tests_server/test_session.py` (o crea `tests_server/test_server_phase.py` si prefieres)

Regla: instancia de `Server` con `host`, `port`, `rng` opcional; arranca en fase LOBBY; expone `phase`, `lobby`, `session`, `lock`.

- [ ] **Step 1: Tests (crear `tests_server/test_server.py`)**

```python
import pytest

from server.server import Server, ServerPhase


def test_server_starts_in_lobby():
    srv = Server(host="127.0.0.1", port=0)
    assert srv.phase is ServerPhase.LOBBY
    assert srv.lobby is not None
    assert srv.session is None


def test_server_lock_exists():
    srv = Server(host="127.0.0.1", port=0)
    assert srv.lock is not None
    # Acquire/release works (not deadlocked):
    with srv.lock:
        pass
```

- [ ] **Step 2: Fail**

- [ ] **Step 3: Implementar stub de `server/server.py`**

```python
"""Server: orchestrates accept loop, lobby, session, and message dispatch."""
from __future__ import annotations

import enum
import random
import threading

from server.lobby import Lobby
from server.session import GameSession


class ServerPhase(str, enum.Enum):
    LOBBY = "lobby"
    IN_GAME = "in_game"
    CLOSED = "closed"


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
        # Connections, listen socket, etc. added in Task 12.
```

- [ ] **Step 4: Pass**

- [ ] **Step 5: Reportar diff**

---

## Task 10: `server.py` — dispatch de comandos en LOBBY

**Files:**
- Modify: `server/server.py`
- Modify: `tests_server/test_server.py`

Regla: método `_dispatch_lobby(conn, msg)` que maneja `join`, `select_color`, `start_game`, `leave`. Sin sockets todavía — los tests usan fake connections.

- [ ] **Step 1: Introducir FakeConnection helper y tests de dispatch**

Añadir al tope de `tests_server/test_server.py`:
```python
from dataclasses import dataclass, field

from server.protocol import encode


@dataclass
class FakeConn:
    conn_id: str
    sent: list[dict] = field(default_factory=list)

    def send(self, data: bytes) -> None:
        import json
        self.sent.append(json.loads(data.decode("utf-8").rstrip("\n")))
```

Y tests:
```python
def test_join_welcomes_and_broadcasts_lobby_update():
    srv = Server()
    alice = FakeConn("c1")
    srv.register_connection(alice)
    srv.handle_message(alice, {"type": "join", "username": "Alice"})
    assert any(m["type"] == "welcome" and m["is_host"] for m in alice.sent)
    assert any(m["type"] == "lobby_update" for m in alice.sent)


def test_second_join_is_not_host_and_both_see_update():
    srv = Server()
    alice, bob = FakeConn("c1"), FakeConn("c2")
    for c in (alice, bob):
        srv.register_connection(c)
    srv.handle_message(alice, {"type": "join", "username": "Alice"})
    srv.handle_message(bob,   {"type": "join", "username": "Bob"})
    # Bob gets welcome with is_host=False.
    bob_welcome = next(m for m in bob.sent if m["type"] == "welcome")
    assert bob_welcome["is_host"] is False
    # Alice gets a second lobby_update after Bob joins.
    alice_updates = [m for m in alice.sent if m["type"] == "lobby_update"]
    assert len(alice_updates) == 2


def test_duplicate_username_rejected_with_error():
    srv = Server()
    a, b = FakeConn("c1"), FakeConn("c2")
    srv.register_connection(a); srv.register_connection(b)
    srv.handle_message(a, {"type": "join", "username": "X"})
    srv.handle_message(b, {"type": "join", "username": "X"})
    errors = [m for m in b.sent if m["type"] == "error"]
    assert any(m["code"] == "DUPLICATE_PLAYER" for m in errors)


def test_select_color_broadcasts_update():
    srv = Server()
    a = FakeConn("c1")
    srv.register_connection(a)
    srv.handle_message(a, {"type": "join", "username": "Alice"})
    a.sent.clear()
    srv.handle_message(a, {"type": "select_color", "color": "red"})
    assert any(
        m["type"] == "lobby_update"
        and any(p.get("color") == "red" for p in m["players"])
        for m in a.sent
    )


def test_start_game_by_non_host_forbidden():
    srv = Server()
    a, b = FakeConn("c1"), FakeConn("c2")
    srv.register_connection(a); srv.register_connection(b)
    srv.handle_message(a, {"type": "join", "username": "Alice"})
    srv.handle_message(b, {"type": "join", "username": "Bob"})
    srv.handle_message(a, {"type": "select_color", "color": "red"})
    srv.handle_message(b, {"type": "select_color", "color": "blue"})
    b.sent.clear()
    srv.handle_message(b, {"type": "start_game"})  # Bob is not host
    assert any(m["type"] == "error" and m["code"] == "FORBIDDEN" for m in b.sent)


def test_start_game_by_host_transitions_to_in_game():
    srv = Server(rng=_seed_rng())
    a, b = FakeConn("c1"), FakeConn("c2")
    srv.register_connection(a); srv.register_connection(b)
    srv.handle_message(a, {"type": "join", "username": "Alice"})
    srv.handle_message(b, {"type": "join", "username": "Bob"})
    srv.handle_message(a, {"type": "select_color", "color": "red"})
    srv.handle_message(b, {"type": "select_color", "color": "blue"})
    a.sent.clear(); b.sent.clear()
    srv.handle_message(a, {"type": "start_game"})
    assert srv.phase is ServerPhase.IN_GAME
    # Both clients should have received a game_started event.
    assert any(m["type"] == "game_started" for m in a.sent)
    assert any(m["type"] == "game_started" for m in b.sent)
    # And a state_update right after.
    assert any(m["type"] == "state_update" for m in a.sent)
```

Añadir helper:
```python
from tests.conftest import ScriptedRandom

def _seed_rng() -> ScriptedRandom:
    return ScriptedRandom([6, 5, 3, 4])  # Alice=11, Bob=7
```

- [ ] **Step 2: Fail**

- [ ] **Step 3: Implementar el dispatch en `server/server.py`**

```python
from typing import Any

from core.entities import Color
from core.exceptions import DomainError, DuplicatePlayer, InvalidMove, WrongPhase
from server.protocol import COMMAND_SCHEMAS, ProtocolError, encode, validate_command


DOMAIN_ERROR_CODES = {
    DuplicatePlayer: "DUPLICATE_PLAYER",
    WrongPhase:      "WRONG_PHASE",
    InvalidMove:     "INVALID_MOVE",
}


class Server:
    # ... (existing __init__)

    def __init__(self, host="0.0.0.0", port=5000, rng=None):
        # ... previous code ...
        self._connections: dict[str, Any] = {}  # conn_id → ClientConnection or FakeConn

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

    def _broadcast_session(self, event: dict) -> None:
        if self.session is None:
            return
        data = encode(event)
        for conn_id in self.session.all_conn_ids():
            conn = self._connections.get(conn_id)
            if conn:
                conn.send(data)

    def _dispatch_game(self, conn, msg: dict) -> None:
        # Implemented in Task 11.
        self._send_error(conn, "WRONG_PHASE", "not implemented")
```

- [ ] **Step 4: Pass**

- [ ] **Step 5: Reportar diff**

---

## Task 11: `server.py` — dispatch de comandos en IN_GAME

**Files:**
- Modify: `server/server.py`
- Modify: `tests_server/test_server.py`

- [ ] **Step 1: Tests**

```python
def _start_two_player_game(rng=None):
    """Helper that arma un server con 2 clientes joineados, coloreados, y start_game."""
    srv = Server(rng=rng or _seed_rng())
    a, b = FakeConn("c1"), FakeConn("c2")
    srv.register_connection(a); srv.register_connection(b)
    srv.handle_message(a, {"type": "join", "username": "Alice"})
    srv.handle_message(b, {"type": "join", "username": "Bob"})
    srv.handle_message(a, {"type": "select_color", "color": "red"})
    srv.handle_message(b, {"type": "select_color", "color": "blue"})
    srv.handle_message(a, {"type": "start_game"})
    a.sent.clear(); b.sent.clear()
    return srv, a, b


def test_roll_initial_broadcasts():
    srv, a, b = _start_two_player_game()
    srv.handle_message(a, {"type": "roll_initial"})
    assert any(m["type"] == "initial_roll" for m in a.sent)
    assert any(m["type"] == "initial_roll" for m in b.sent)
    # state_update should also be broadcast.
    assert any(m["type"] == "state_update" for m in a.sent)


def test_roll_dice_not_my_turn_is_wrong_phase_or_forbidden():
    # Alice won the initial order; Bob trying to roll should be rejected.
    rng = _seed_rng()  # Alice first
    srv, a, b = _start_two_player_game(rng)
    srv.handle_message(a, {"type": "roll_initial"})
    srv.handle_message(b, {"type": "roll_initial"})
    b.sent.clear()
    srv.handle_message(b, {"type": "roll_dice"})  # not Bob's turn
    assert any(m["type"] == "error" for m in b.sent)


def test_unknown_conn_sending_game_command_without_join_is_rejected():
    srv, a, b = _start_two_player_game()
    ghost = FakeConn("ghost")
    srv.register_connection(ghost)
    srv.handle_message(ghost, {"type": "roll_dice"})
    assert any(m["type"] == "error" for m in ghost.sent)
```

- [ ] **Step 2: Fail**

- [ ] **Step 3: Implementar `_dispatch_game`**

```python
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
            total = self.session.roll_initial(player_idx)
            player = self.session.game.players[player_idx]
            self._broadcast_session({
                "type": "initial_roll",
                "player_index": player_idx,
                "username": player.name,
                "total": total,
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
                    "captured":       (
                        {
                            "index":         result.captured.index,
                            "circuit_position": result.captured.circuit_position,
                            "state":         result.captured.state.value,
                        } if result.captured else None
                    ),
                },
            })
            self._broadcast_session({
                "type": "state_update",
                "state": self.session.state_dict(),
            })
            # If the game is over, transition to CLOSED.
            if self.session.game.winner is not None:
                self._broadcast_session({
                    "type": "game_over",
                    "winner_index":    self.session.game.winner,
                    "winner_username": self.session.game.players[self.session.game.winner].name,
                })
                self.phase = ServerPhase.CLOSED
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
                self.phase = ServerPhase.CLOSED
        elif t == "join":
            self._send_error(conn, "FORBIDDEN", "a game is in progress")
        else:
            self._send_error(conn, "WRONG_PHASE", f"{t} not allowed in IN_GAME")

    def _handle_ingame_leave(self, conn) -> None:
        assert self.session is not None
        color = self.session.color_for_conn(conn.conn_id)
        if color is not None:
            self.session.mark_disconnected(conn.conn_id)
            self.unregister_connection(conn.conn_id)
            self._broadcast_session({
                "type": "state_update",
                "state": self.session.state_dict(),
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
                self.phase = ServerPhase.CLOSED
```

- [ ] **Step 4: Pass**

- [ ] **Step 5: Reportar diff**

---

## Task 12: `server.py` — accept loop + threading

**Files:**
- Modify: `server/server.py`

Regla: `serve_forever()` hace `bind/listen/accept` en el thread principal; cada conexión genera un thread daemon que hace `readline` en loop y llama a `handle_message`.

- [ ] **Step 1: Test de arranque (mínimo, sin clientes reales aún)**

Añadir a `tests_server/test_server.py`:
```python
import socket
import time


def test_server_binds_and_accepts_connection():
    srv = Server(host="127.0.0.1", port=0)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    srv.wait_ready(timeout=1.0)
    assert srv.port > 0
    # Just connect and close — should not crash the server.
    sock = socket.create_connection(("127.0.0.1", srv.port), timeout=1.0)
    sock.close()
    time.sleep(0.1)  # let the server's handler see the disconnect
    srv.shutdown()
    thread.join(timeout=2.0)
    assert not thread.is_alive()
```

- [ ] **Step 2: Fail** (métodos no existen)

- [ ] **Step 3: Implementar accept loop**

```python
import logging
import socket

from server.connection import ClientConnection
from server.protocol import decode


logger = logging.getLogger(__name__)


class Server:
    # ... existing ...

    def __init__(self, ...):
        # ... existing init ...
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
        self._ready.set()
        logger.info("listening on %s:%d", self.host, self.port)
        try:
            while not self._shutdown:
                try:
                    sock, addr = self._listen_sock.accept()
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
        conn.close()
```

- [ ] **Step 4: Pass**

- [ ] **Step 5: Reportar diff**

---

## Task 13: Fixtures de integración — `server_factory` + `TestClient`

**Files:**
- Modify: `tests_server/conftest.py`

- [ ] **Step 1: Implementar fixtures**

```python
"""Shared fixtures for server tests."""
from __future__ import annotations

import json
import queue
import socket
import threading
import time

import pytest

from server.server import Server


@pytest.fixture
def server_factory():
    """Spawn a Server in a daemon thread; cleanup on fixture teardown."""
    servers: list[Server] = []

    def _make(rng=None) -> tuple[str, int]:
        srv = Server(host="127.0.0.1", port=0, rng=rng)
        thread = threading.Thread(target=srv.serve_forever, daemon=True)
        thread.start()
        srv.wait_ready(timeout=2.0)
        servers.append(srv)
        return "127.0.0.1", srv.port

    yield _make

    for srv in servers:
        srv.shutdown()


class SocketClient:
    """A synchronous test client that reads/writes NDJSON over a TCP socket.

    Named `SocketClient` (not `TestClient`) so pytest does not try to collect
    it as a test class.
    """

    __test__ = False  # belt-and-suspenders against pytest collection

    def __init__(self, host: str, port: int):
        self.sock = socket.create_connection((host, port), timeout=2.0)
        self.sock.settimeout(2.0)
        self._recv_queue: queue.Queue[dict] = queue.Queue()
        self._alive = True
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()

    def _reader(self) -> None:
        buf = b""
        while self._alive:
            try:
                chunk = self.sock.recv(4096)
            except (socket.timeout, OSError):
                break
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                if line.strip():
                    try:
                        self._recv_queue.put(json.loads(line))
                    except json.JSONDecodeError:
                        pass

    def send(self, msg: dict) -> None:
        line = (json.dumps(msg) + "\n").encode("utf-8")
        self.sock.sendall(line)

    def recv(self, timeout: float = 1.0) -> dict:
        return self._recv_queue.get(timeout=timeout)

    def drain(self, expected_count: int | None = None, timeout: float = 1.0) -> list[dict]:
        """Collect currently-available (or up to N expected) messages."""
        msgs = []
        start = time.monotonic()
        while True:
            try:
                msgs.append(self._recv_queue.get(timeout=0.1))
            except queue.Empty:
                if expected_count is None:
                    return msgs
                if len(msgs) >= expected_count:
                    return msgs
                if time.monotonic() - start > timeout:
                    return msgs

    def close(self) -> None:
        self._alive = False
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.sock.close()


@pytest.fixture
def client_factory():
    """Factory that creates TestClient instances; cleanup on fixture teardown."""
    clients: list[SocketClient] = []

    def _make(host: str, port: int) -> SocketClient:
        c = SocketClient(host, port)
        clients.append(c)
        return c

    yield _make

    for c in clients:
        c.close()
```

- [ ] **Step 2: Smoke test del fixture**

Añadir a `tests_server/test_server.py`:
```python
def test_fixture_spawns_server_and_accepts_client(server_factory, client_factory):
    host, port = server_factory()
    client = client_factory(host, port)
    client.send({"type": "join", "username": "Solo"})
    welcome = client.recv()
    assert welcome["type"] == "welcome"
    assert welcome["is_host"] is True
```

- [ ] **Step 3: Pass**

- [ ] **Step 4: Reportar diff**

---

## Task 14: Test E2E — partida completa

**Files:**
- Create: `tests_server/test_integration.py`

Regla: 2 clientes, join, color, start_game, inject scripted rng que termina la partida en pocas jugadas (similar al `test_full_game.py` del módulo #1 — pre-set 3 fichas coronadas de Alice vía state, pero esta vez no es posible porque el state vive en el server). **Alternativa práctica:** aceptar que el test E2E ejercita solo el setup + algunas jugadas + desconexión → game_over por `<2` conectados.

- [ ] **Step 1: Tests**

`tests_server/test_integration.py`:
```python
from tests.conftest import ScriptedRandom


def test_lobby_flow_end_to_end(server_factory, client_factory):
    rng = ScriptedRandom([6, 5, 3, 4])  # initial rolls
    host, port = server_factory(rng=rng)

    alice = client_factory(host, port)
    bob = client_factory(host, port)

    alice.send({"type": "join", "username": "Alice"})
    bob.send({"type": "join", "username": "Bob"})

    # Drain welcome + lobby_update events.
    alice.drain(expected_count=3, timeout=1.0)
    bob.drain(expected_count=2, timeout=1.0)

    alice.send({"type": "select_color", "color": "red"})
    bob.send({"type": "select_color", "color": "blue"})
    alice.drain(expected_count=2, timeout=1.0)
    bob.drain(expected_count=2, timeout=1.0)

    alice.send({"type": "start_game"})

    alice_started = False
    bob_started = False
    for m in alice.drain(expected_count=3, timeout=1.0):
        if m["type"] == "game_started":
            alice_started = True
    for m in bob.drain(expected_count=3, timeout=1.0):
        if m["type"] == "game_started":
            bob_started = True
    assert alice_started and bob_started


def test_game_ends_when_everyone_disconnects_except_one(server_factory, client_factory):
    rng = ScriptedRandom([6, 5, 3, 4])
    host, port = server_factory(rng=rng)

    alice = client_factory(host, port)
    bob = client_factory(host, port)

    alice.send({"type": "join", "username": "Alice"})
    bob.send({"type": "join", "username": "Bob"})
    alice.drain(timeout=0.5)
    bob.drain(timeout=0.5)
    alice.send({"type": "select_color", "color": "red"})
    bob.send({"type": "select_color", "color": "blue"})
    alice.drain(timeout=0.5)
    bob.drain(timeout=0.5)
    alice.send({"type": "start_game"})
    alice.drain(timeout=0.5)
    bob.drain(timeout=0.5)

    # Bob disconnects.
    bob.close()

    # Alice should eventually receive a game_over.
    msgs = alice.drain(expected_count=5, timeout=2.0)
    game_overs = [m for m in msgs if m["type"] == "game_over"]
    assert game_overs
    assert game_overs[0]["winner_username"] == "Alice"
```

- [ ] **Step 2: Pass**

```bash
.venv/bin/pytest tests_server/test_integration.py -v
```

- [ ] **Step 3: Reportar diff**

---

## Task 15: `__main__.py` — CLI + logging

**Files:**
- Modify: `server/__main__.py`

- [ ] **Step 1: Reemplazar stub por implementación**

```python
"""Entry point: `python -m server`."""
from __future__ import annotations

import argparse
import logging
import sys

from server.server import Server


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s",
    )

    server = Server(host=args.host, port=args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("shutdown requested")
        server.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Smoke manual (opcional, no tests)**

```bash
.venv/bin/python -m server --port 0 --log-level DEBUG &
sleep 0.5
kill %1  # o Ctrl+C
```

Debe loggear `listening on 0.0.0.0:<random-port>` y cerrar limpio.

- [ ] **Step 3: Reportar diff**

---

## Task 16: Re-exports en `server/__init__.py` + cobertura

**Files:**
- Modify: `server/__init__.py`

- [ ] **Step 1: Re-exports**

```python
"""Parqués TCP server — exposes core/ to remote clients over sockets."""
from server.lobby import Lobby, LobbyError, LobbyFull, LobbyPlayer
from server.protocol import ProtocolError, decode, encode, validate_command
from server.server import Server, ServerPhase
from server.session import GameSession

__all__ = [
    "Lobby", "LobbyError", "LobbyFull", "LobbyPlayer",
    "ProtocolError", "decode", "encode", "validate_command",
    "Server", "ServerPhase",
    "GameSession",
]
```

- [ ] **Step 2: Correr la suite completa**

```bash
.venv/bin/pytest -q
```
Expected: todos verdes (motor + server).

- [ ] **Step 3: Medir cobertura**

```bash
.venv/bin/pytest --cov=core --cov=server --cov-report=term-missing
```
Expected: `core/` ≥ 95% (ya logrado en módulo #1), `server/` ≥ 90%. Si falta cobertura puntual en `server/`, agregar 1-2 tests en el archivo apropiado hasta llegar.

- [ ] **Step 4: Reportar diff final**

---

## Resumen de tareas

| # | Tarea | Archivos clave |
|---|---|---|
| 1 | Scaffold | `server/`, `tests_server/`, `pyproject.toml` |
| 2 | Protocol encode/decode | `server/protocol.py` |
| 3 | Protocol validate_command | `server/protocol.py` |
| 4 | Lobby join/host/rechazos | `server/lobby.py` |
| 5 | Lobby select_color/can_start | `server/lobby.py` |
| 6 | GameSession básico | `server/session.py` |
| 7 | GameSession desconexión + auto-skip | `server/session.py` |
| 8 | ClientConnection (sockets) | `server/connection.py` |
| 9 | Server init + LOBBY phase | `server/server.py` |
| 10 | Server dispatch LOBBY | `server/server.py` |
| 11 | Server dispatch IN_GAME | `server/server.py` |
| 12 | Server accept loop + threads | `server/server.py` |
| 13 | Fixtures integración | `tests_server/conftest.py` |
| 14 | Test E2E partida | `tests_server/test_integration.py` |
| 15 | CLI + logging | `server/__main__.py` |
| 16 | Re-exports + cobertura | `server/__init__.py` |

**Criterio de módulo #2 terminado:**
- `.venv/bin/pytest` verde con ≥80 tests totales (67 del motor + ~15-20 del server).
- Cobertura ≥ 90% en `server/`.
- `python -m server` arranca, acepta conexiones, registra logs con `threadName`.
- Test E2E demuestra que dos sockets reales pueden completar el handshake (join → select_color → start_game → game_started).

Siguiente módulo (tras aprobación del usuario): **#3 — UI gráfica Quasar** que consume este servidor. Posiblemente requerirá un puente WebSocket↔TCP o extender el servidor para aceptar conexiones WebSocket directamente.
