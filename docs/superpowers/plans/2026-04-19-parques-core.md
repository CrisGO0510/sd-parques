# Parqués Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar el dominio puro del juego de Parqués colombiano (reglas, entidades, motor, tests) en Python 3.11+, sin red, sin BD, sin UI, sin concurrencia — con cobertura ≥95% en `engine.py`.

**Architecture:** Paquete plano `parques/` con entidades como dataclasses mutables, un motor de funciones puras que opera sobre `Game`, un layout de tablero con constantes + helpers puros, y un set de excepciones de dominio. TDD estricto: test → fail → implement minimal → pass → commit.

**Tech Stack:** Python 3.11+ stdlib, `pytest>=8.0` (dev-only). Sin otras dependencias externas.

**Spec:** `docs/superpowers/specs/2026-04-19-parques-core-design.md`

---

## File Structure

```
sd-parques/
├── parques/
│   ├── __init__.py        # re-exports públicos del paquete
│   ├── entities.py        # Color, PieceState, GamePhase, MoveAction, Piece, Player, Move, MoveResult, Game
│   ├── board.py           # BOARD_SIZE, HOME_STRETCH_SIZE, EXITS, SAFES, HOME_STRETCH_ENTRY + helpers puros
│   ├── engine.py          # new_game, roll_initial, roll_dice, available_moves, apply_move, skip_turn, crown_piece
│   └── exceptions.py      # DomainError, WrongPhase, InvalidMove, DuplicatePlayer
├── tests/
│   ├── __init__.py
│   ├── conftest.py        # ScriptedRandom, fixtures (two_player_game, playing_game, force_dice)
│   ├── test_entities.py   # smoke tests de construcción de dataclasses
│   ├── test_exceptions.py # jerarquía de excepciones
│   ├── test_board.py      # helpers del layout
│   ├── test_engine_turns.py
│   ├── test_engine_movement.py
│   ├── test_engine_capture.py
│   ├── test_engine_home_stretch.py
│   └── test_full_game.py  # simulación end-to-end
└── pyproject.toml
```

**Notas del layout:**
- `entities.py` junta todas las dataclasses porque cada una es corta (5-15 líneas).
- `board.py` separa el **layout estático** de las **reglas** que viven en `engine.py`.
- Tests agrupados por **comportamiento** (turnos, movimiento, captura, recta final), no por clase.

---

## Task 1: Scaffold del proyecto

**Files:**
- Create: `pyproject.toml`, `parques/__init__.py`, `tests/__init__.py`, `tests/test_smoke.py`

> (`tests/conftest.py` se crea más adelante en la Task 5 — no en esta.)

- [ ] **Step 1: Crear `pyproject.toml`**

```toml
[project]
name = "parques"
version = "0.1.0"
description = "Domain core for the distributed Parqués game."
requires-python = ">=3.11"

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["parques*"]
exclude = ["tests*", "_legacy*"]
```

- [ ] **Step 2: Crear el paquete vacío**

```bash
mkdir -p parques tests
touch parques/__init__.py tests/__init__.py
```

- [ ] **Step 3: Crear venv e instalar pytest**

```bash
python3.11 -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

Expected: pytest instalado en `.venv/bin/pytest`.

- [ ] **Step 4: Escribir test de humo**

`tests/test_smoke.py`:
```python
def test_smoke():
    assert True
```

- [ ] **Step 5: Correr el smoke**

Run: `.venv/bin/pytest`
Expected: `1 passed`.

- [ ] **Step 6: Añadir entradas relevantes al `.gitignore`**

Al final de `.gitignore` (si no están ya):
```
.venv/
*.egg-info/
__pycache__/
.pytest_cache/
```

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml parques/__init__.py tests/__init__.py tests/test_smoke.py .gitignore
git commit -m "chore: scaffold parques package with pytest"
```

---

## Task 2: Entities — enums y dataclasses

**Files:**
- Create: `parques/entities.py`
- Create: `tests/test_entities.py`

- [ ] **Step 1: Escribir tests de entidades**

`tests/test_entities.py`:
```python
from parques.entities import (
    Color, PieceState, GamePhase, MoveAction,
    Piece, Player, Move, MoveResult, Game,
)


def test_color_enum_has_four_values():
    assert set(Color) == {Color.RED, Color.BLUE, Color.GREEN, Color.YELLOW}


def test_piece_defaults_to_jail_with_no_position():
    piece = Piece(index=0)
    assert piece.state is PieceState.IN_JAIL
    assert piece.circuit_position is None
    assert piece.home_stretch_position is None


def test_player_gets_four_pieces_by_default():
    player = Player(name="Alice", color=Color.RED)
    assert len(player.pieces) == 4
    assert [p.index for p in player.pieces] == [0, 1, 2, 3]
    assert all(p.state is PieceState.IN_JAIL for p in player.pieces)


def test_game_defaults_to_setup_phase():
    alice = Player(name="Alice", color=Color.RED)
    bob = Player(name="Bob", color=Color.BLUE)
    game = Game(players=[alice, bob])
    assert game.phase is GamePhase.SETUP
    assert game.pending_dice == []
    assert game.turn_order == []
    assert game.consecutive_pairs == 0
    assert game.winner is None


def test_move_and_moveresult_construct():
    move = Move(piece_index=0, dice_value=5, action=MoveAction.ADVANCE)
    assert move.action is MoveAction.ADVANCE
    result = MoveResult(action=MoveAction.CAPTURE)
    assert result.captured is None
    assert result.reached_goal is False
```

- [ ] **Step 2: Verificar que fallan**

Run: `.venv/bin/pytest tests/test_entities.py -v`
Expected: `ImportError: cannot import name 'Color' from 'parques.entities'` (el archivo no existe).

- [ ] **Step 3: Implementar `parques/entities.py`**

```python
"""Domain entities for the parques game core."""
from dataclasses import dataclass, field
from enum import Enum


class Color(str, Enum):
    RED = "red"
    BLUE = "blue"
    GREEN = "green"
    YELLOW = "yellow"


class PieceState(str, Enum):
    IN_JAIL = "in_jail"
    ON_BOARD = "on_board"
    IN_HOME_STRETCH = "in_home_stretch"
    CROWNED = "crowned"


class GamePhase(str, Enum):
    SETUP = "setup"
    ROLLING = "rolling"
    MOVING = "moving"
    CROWNING = "crowning"
    FINISHED = "finished"


class MoveAction(str, Enum):
    EXIT_JAIL = "exit_jail"
    ADVANCE = "advance"
    CAPTURE = "capture"
    ENTER_HOME_STRETCH = "enter_home_stretch"
    REACH_GOAL = "reach_goal"


@dataclass
class Piece:
    index: int
    state: PieceState = PieceState.IN_JAIL
    circuit_position: int | None = None
    home_stretch_position: int | None = None


@dataclass
class Player:
    name: str
    color: Color
    pieces: list[Piece] = field(
        default_factory=lambda: [Piece(i) for i in range(4)]
    )


@dataclass
class Move:
    piece_index: int
    dice_value: int
    action: MoveAction


@dataclass
class MoveResult:
    action: MoveAction
    captured: Piece | None = None
    reached_goal: bool = False
    triggered_crowning: bool = False


@dataclass
class Game:
    players: list[Player]
    phase: GamePhase = GamePhase.SETUP
    turn_order: list[int] = field(default_factory=list)
    current_turn_index: int = 0
    pending_dice: list[int] = field(default_factory=list)
    initial_rolls: dict[int, int] = field(default_factory=dict)
    initial_rolls_remaining: int = 0
    consecutive_pairs: int = 0
    winner: int | None = None
```

- [ ] **Step 4: Verificar que pasan**

Run: `.venv/bin/pytest tests/test_entities.py -v`
Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
git add parques/entities.py tests/test_entities.py
git commit -m "feat: entities module with enums and dataclasses"
```

---

## Task 3: Exceptions

**Files:**
- Create: `parques/exceptions.py`
- Create: `tests/test_exceptions.py`

- [ ] **Step 1: Escribir tests**

`tests/test_exceptions.py`:
```python
import pytest
from parques.exceptions import (
    DomainError, WrongPhase, InvalidMove, DuplicatePlayer,
)


def test_domain_error_is_exception():
    assert issubclass(DomainError, Exception)


def test_all_domain_errors_inherit_from_domain_error():
    assert issubclass(WrongPhase, DomainError)
    assert issubclass(InvalidMove, DomainError)
    assert issubclass(DuplicatePlayer, DomainError)


def test_errors_can_be_raised_with_message():
    with pytest.raises(WrongPhase, match="not in SETUP"):
        raise WrongPhase("not in SETUP")
```

- [ ] **Step 2: Verificar que fallan**

Run: `.venv/bin/pytest tests/test_exceptions.py -v`
Expected: ImportError.

- [ ] **Step 3: Implementar `parques/exceptions.py`**

```python
"""Domain-level exceptions for parques."""


class DomainError(Exception):
    """Base class for all parques domain errors."""


class WrongPhase(DomainError):
    """An operation was called in the wrong GamePhase."""


class InvalidMove(DomainError):
    """The supplied Move is not among engine.available_moves()."""


class DuplicatePlayer(DomainError):
    """Two players share the same name or the same color."""
```

- [ ] **Step 4: Verificar que pasan**

Run: `.venv/bin/pytest tests/test_exceptions.py -v`
Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add parques/exceptions.py tests/test_exceptions.py
git commit -m "feat: domain exceptions"
```

---

## Task 4: Board — constantes y helpers puros

**Files:**
- Create: `parques/board.py`
- Create: `tests/test_board.py`

**Constantes del layout** (verificables con el enunciado + variante colombiana tradicional):
- `BOARD_SIZE = 96` (circuito principal, posiciones 0..95).
- `HOME_STRETCH_SIZE = 8` (recta final por color, posiciones 0..7, siendo 7 la meta).
- `EXITS`: posición de salida por color. Propuesta equidistante: `{RED: 0, BLUE: 24, GREEN: 48, YELLOW: 72}`.
- `HOME_STRETCH_ENTRY`: casilla **anterior** a la desviación por color. Propuesta: `{RED: 71, BLUE: 95, GREEN: 23, YELLOW: 47}` (7 casillas antes del cuadrante siguiente).
- `SAFES`: las 12 posiciones de seguro. Propuesta: los 4 exits (0, 24, 48, 72) + 8 casillas intermedias (6, 18, 30, 42, 54, 66, 78, 90).

> Estos valores implementan la asunción #1 del spec. Si el profesor especifica otros, se ajustan sin cambiar el resto del código.

- [ ] **Step 1: Escribir tests del board**

`tests/test_board.py`:
```python
import pytest
from parques.board import (
    BOARD_SIZE, HOME_STRETCH_SIZE,
    EXITS, SAFES, HOME_STRETCH_ENTRY,
    is_safe, exit_position, home_stretch_entry_for, next_position,
)
from parques.entities import Color


def test_board_size_is_96():
    assert BOARD_SIZE == 96


def test_home_stretch_size_is_8():
    assert HOME_STRETCH_SIZE == 8


def test_exits_one_per_color():
    assert set(EXITS.keys()) == set(Color)
    assert len(set(EXITS.values())) == 4


def test_safes_contains_twelve_cells():
    assert len(SAFES) == 12


def test_safes_contains_all_exits():
    for exit_pos in EXITS.values():
        assert exit_pos in SAFES


def test_is_safe_returns_true_for_every_safe_cell():
    for pos in SAFES:
        assert is_safe(pos)


def test_is_safe_returns_false_for_non_safe_cell():
    non_safe = next(i for i in range(BOARD_SIZE) if i not in SAFES)
    assert not is_safe(non_safe)


def test_exit_position_returns_mapped_value():
    assert exit_position(Color.RED) == EXITS[Color.RED]


def test_home_stretch_entry_for_returns_mapped_value():
    assert home_stretch_entry_for(Color.BLUE) == HOME_STRETCH_ENTRY[Color.BLUE]


def test_next_position_advances_within_range():
    assert next_position(0, 5) == 5


def test_next_position_wraps_around():
    assert next_position(94, 5) == 3


def test_next_position_lands_exactly_on_zero_after_full_loop():
    assert next_position(0, BOARD_SIZE) == 0


def test_next_position_rejects_negative_steps():
    with pytest.raises(ValueError):
        next_position(10, -1)
```

- [ ] **Step 2: Verificar que fallan**

Run: `.venv/bin/pytest tests/test_board.py -v`
Expected: ImportError.

- [ ] **Step 3: Implementar `parques/board.py`**

```python
"""Board layout constants and pure helpers."""
from parques.entities import Color

BOARD_SIZE = 96
HOME_STRETCH_SIZE = 8

EXITS: dict[Color, int] = {
    Color.RED: 0,
    Color.BLUE: 24,
    Color.GREEN: 48,
    Color.YELLOW: 72,
}

# Last circuit cell before diverging into the home stretch for each color.
# Chosen so each color runs a full loop (95 cells) before entering.
HOME_STRETCH_ENTRY: dict[Color, int] = {
    Color.RED: 71,
    Color.BLUE: 95,
    Color.GREEN: 23,
    Color.YELLOW: 47,
}

SAFES: frozenset[int] = frozenset({
    0, 6, 18, 24, 30, 42, 48, 54, 66, 72, 78, 90,
})


def is_safe(position: int) -> bool:
    """Return True if the circuit cell is a safe cell (no capture)."""
    return position in SAFES


def exit_position(color: Color) -> int:
    """Circuit cell where a piece lands when leaving jail."""
    return EXITS[color]


def home_stretch_entry_for(color: Color) -> int:
    """Last circuit cell before diverging into the color's home stretch."""
    return HOME_STRETCH_ENTRY[color]


def next_position(position: int, steps: int) -> int:
    """Advance `steps` cells on the circuit with wrap-around 95 → 0."""
    if steps < 0:
        raise ValueError("steps must be non-negative")
    return (position + steps) % BOARD_SIZE
```

- [ ] **Step 4: Verificar que pasan**

Run: `.venv/bin/pytest tests/test_board.py -v`
Expected: `13 passed`.

- [ ] **Step 5: Commit**

```bash
git add parques/board.py tests/test_board.py
git commit -m "feat: board layout constants and helpers"
```

---

## Task 5: Conftest — ScriptedRandom y fixtures

**Files:**
- Create: `tests/conftest.py`

- [ ] **Step 1: Implementar `tests/conftest.py`**

```python
"""Shared fixtures and helpers for parques tests."""
from __future__ import annotations

import pytest

from parques.entities import Color, GamePhase


class ScriptedRandom:
    """A minimal rng that returns pre-scripted dice values.

    Implements the `randint(a, b)` method the engine uses; ignores the
    bounds and pops from `sequence` in order. Raises IndexError when
    the script is exhausted.
    """

    def __init__(self, sequence: list[int]):
        self._sequence = list(sequence)

    def randint(self, a: int, b: int) -> int:
        if not self._sequence:
            raise IndexError("ScriptedRandom sequence exhausted")
        return self._sequence.pop(0)


@pytest.fixture
def scripted_rng():
    """Factory that builds ScriptedRandom from a list of ints."""
    def _make(sequence: list[int]) -> ScriptedRandom:
        return ScriptedRandom(sequence)
    return _make


@pytest.fixture
def two_player_game(scripted_rng):
    """Fresh game in SETUP phase with Alice (RED) and Bob (BLUE)."""
    from parques import engine
    return engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([]),
    )


def force_dice(game, d1: int, d2: int) -> None:
    """Test helper: put `[d1, d2]` into pending_dice and set MOVING phase.

    Use in unit tests that need a specific dice state without going
    through roll_dice (which has triple-pair / all-in-jail side effects).
    """
    game.pending_dice = [d1, d2]
    game.phase = GamePhase.MOVING
```

- [ ] **Step 2: Verificar que pytest lo carga sin error**

Run: `.venv/bin/pytest tests/ -v`
Expected: los tests existentes siguen pasando, no hay errores de import en `conftest.py`. El fixture `two_player_game` fallará al usarse porque `parques.engine` no existe todavía — no importa, aún no lo usamos.

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "test: scripted rng and fixtures"
```

---

## Task 6: Engine — `new_game`

**Files:**
- Create: `parques/engine.py`
- Create: `tests/test_engine_turns.py`

- [ ] **Step 1: Escribir tests**

`tests/test_engine_turns.py`:
```python
import pytest

from parques import engine
from parques.entities import Color, GamePhase, PieceState
from parques.exceptions import DuplicatePlayer


def test_new_game_sets_setup_phase_and_four_pieces_in_jail():
    game = engine.new_game([("Alice", Color.RED), ("Bob", Color.BLUE)])
    assert game.phase is GamePhase.SETUP
    assert len(game.players) == 2
    for player in game.players:
        assert all(p.state is PieceState.IN_JAIL for p in player.pieces)


def test_new_game_rejects_fewer_than_two_players():
    with pytest.raises(ValueError):
        engine.new_game([("Solo", Color.RED)])


def test_new_game_rejects_more_than_four_players():
    players = [
        ("A", Color.RED), ("B", Color.BLUE),
        ("C", Color.GREEN), ("D", Color.YELLOW),
        ("E", Color.RED),
    ]
    with pytest.raises(ValueError):
        engine.new_game(players)


def test_new_game_rejects_duplicate_names():
    with pytest.raises(DuplicatePlayer, match="name"):
        engine.new_game([("Alice", Color.RED), ("Alice", Color.BLUE)])


def test_new_game_rejects_duplicate_colors():
    with pytest.raises(DuplicatePlayer, match="color"):
        engine.new_game([("Alice", Color.RED), ("Bob", Color.RED)])
```

- [ ] **Step 2: Verificar que fallan**

Run: `.venv/bin/pytest tests/test_engine_turns.py -v`
Expected: ImportError (no `parques.engine`).

- [ ] **Step 3: Implementar `new_game`**

Crear `parques/engine.py`:
```python
"""Game engine: pure-function rules operating on a mutable Game."""
from __future__ import annotations

import random

from parques.entities import (
    Color, Game, GamePhase, Player,
)
# Re-export domain exceptions as engine.X for ergonomic use in tests/clients.
from parques.exceptions import (  # noqa: F401
    DomainError, DuplicatePlayer, InvalidMove, WrongPhase,
)


def new_game(
    players: list[tuple[str, Color]],
    *,
    rng: random.Random | None = None,
) -> Game:
    """Create a new game in SETUP phase."""
    if not 2 <= len(players) <= 4:
        raise ValueError("parques requires between 2 and 4 players")

    names = [name for name, _ in players]
    colors = [color for _, color in players]
    if len(set(names)) != len(names):
        raise DuplicatePlayer("duplicate name")
    if len(set(colors)) != len(colors):
        raise DuplicatePlayer("duplicate color")

    game = Game(
        players=[Player(name=name, color=color) for name, color in players],
    )
    game._rng = rng or random.Random()  # type: ignore[attr-defined]
    return game
```

> **Nota:** `_rng` se pega como atributo privado al `Game` (no está en la dataclass declarada). Es un vehículo interno del motor; el cliente no lo toca. Alternativa más pura: pasar `rng` a cada función como parámetro — se rechaza porque ensucia toda la API con un argumento de infra.

- [ ] **Step 4: Verificar que pasan**

Run: `.venv/bin/pytest tests/test_engine_turns.py -v`
Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
git add parques/engine.py tests/test_engine_turns.py
git commit -m "feat: engine.new_game with validation"
```

---

## Task 7: Engine — `roll_initial`

**Files:**
- Modify: `parques/engine.py`
- Modify: `tests/test_engine_turns.py`

- [ ] **Step 1: Extender tests**

Añadir al final de `tests/test_engine_turns.py`:
```python
from parques.exceptions import WrongPhase


def test_roll_initial_collects_rolls_and_transitions_to_rolling(scripted_rng):
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([3, 4, 6, 5]),  # Alice=7, Bob=11 → Bob first
    )
    assert engine.roll_initial(game, 0) == 7
    assert game.phase is GamePhase.SETUP
    assert engine.roll_initial(game, 1) == 11
    assert game.phase is GamePhase.ROLLING
    assert game.turn_order == [1, 0]  # Bob (index 1) first
    assert game.current_turn_index == 0


def test_roll_initial_rejects_out_of_phase(scripted_rng):
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([3, 4, 6, 5]),
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)  # now in ROLLING
    with pytest.raises(WrongPhase):
        engine.roll_initial(game, 0)


def test_roll_initial_rejects_second_roll_by_same_player(scripted_rng):
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([3, 4, 6, 5]),
    )
    engine.roll_initial(game, 0)
    with pytest.raises(ValueError):
        engine.roll_initial(game, 0)


def test_roll_initial_rejects_invalid_player_index(scripted_rng):
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([]),
    )
    with pytest.raises(ValueError):
        engine.roll_initial(game, 9)
```

- [ ] **Step 2: Verificar que fallan**

Run: `.venv/bin/pytest tests/test_engine_turns.py -v`
Expected: `AttributeError: module 'parques.engine' has no attribute 'roll_initial'`.

- [ ] **Step 3: Implementar `roll_initial`**

Añadir a `parques/engine.py`:
```python
from parques.exceptions import WrongPhase


def roll_initial(game: Game, player_index: int) -> int:
    """SETUP phase: player rolls to help decide turn order."""
    if game.phase is not GamePhase.SETUP:
        raise WrongPhase("not in SETUP phase")
    if not 0 <= player_index < len(game.players):
        raise ValueError(f"player_index out of range: {player_index}")
    if player_index in game.initial_rolls:
        raise ValueError(f"player {player_index} already rolled")

    rng = game._rng  # type: ignore[attr-defined]
    total = rng.randint(1, 6) + rng.randint(1, 6)
    game.initial_rolls[player_index] = total

    if len(game.initial_rolls) == len(game.players):
        _resolve_turn_order(game)

    return total


def _resolve_turn_order(game: Game) -> None:
    """Sort players by initial-roll total descending. Ties preserve
    the original player order (stable sort)."""
    game.turn_order = sorted(
        game.initial_rolls.keys(),
        key=lambda idx: game.initial_rolls[idx],
        reverse=True,
    )
    game.current_turn_index = 0
    game.phase = GamePhase.ROLLING
```

> **Decisión:** desempate por orden de inscripción (stable sort). Asunción #5 del spec; si el profesor prefiere relanzamiento, se cambia aquí.

- [ ] **Step 4: Verificar que pasan**

Run: `.venv/bin/pytest tests/test_engine_turns.py -v`
Expected: `9 passed`.

- [ ] **Step 5: Commit**

```bash
git add parques/engine.py tests/test_engine_turns.py
git commit -m "feat: engine.roll_initial sets turn order"
```

---

## Task 8: Engine — `roll_dice` caso base (sin pares, sin cárcel total)

**Files:**
- Modify: `parques/engine.py`
- Modify: `tests/test_engine_turns.py`

- [ ] **Step 1: Extender tests**

Añadir a `tests/test_engine_turns.py`:
```python
def test_roll_dice_fills_pending_dice_and_moves_to_moving(scripted_rng):
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([6, 5, 3, 4, 2, 3]),
    )
    engine.roll_initial(game, 0)   # Alice=11
    engine.roll_initial(game, 1)   # Bob=7 → Alice first
    # Alice has pieces out of jail? No, still all in jail.
    # But first roll sets initial_rolls_remaining=3.
    d1, d2 = engine.roll_dice(game)
    assert (d1, d2) == (2, 3)
    assert game.pending_dice == [2, 3]
    # Not a pair and all pieces in jail → counts against the 3 opportunities.
    # (full behaviour tested in Task 9)


def test_roll_dice_rejects_wrong_phase(two_player_game):
    with pytest.raises(WrongPhase):
        engine.roll_dice(two_player_game)
```

- [ ] **Step 2: Verificar que fallan**

Run: `.venv/bin/pytest tests/test_engine_turns.py -v`
Expected: `AttributeError: no attribute 'roll_dice'`.

- [ ] **Step 3: Implementar `roll_dice` base**

Añadir a `engine.py`:
```python
from parques.entities import PieceState


def roll_dice(game: Game) -> tuple[int, int]:
    """ROLLING phase: current player rolls both dice."""
    if game.phase is not GamePhase.ROLLING:
        raise WrongPhase("not in ROLLING phase")

    rng = game._rng  # type: ignore[attr-defined]
    d1 = rng.randint(1, 6)
    d2 = rng.randint(1, 6)

    # TODO in later tasks: handle pairs, triple-pair, all-in-jail 3-rolls.
    game.pending_dice = [d1, d2]
    game.phase = GamePhase.MOVING
    return d1, d2


def _current_player(game: Game) -> Player:
    return game.players[game.turn_order[game.current_turn_index]]


def _all_in_jail(player: Player) -> bool:
    return all(p.state is PieceState.IN_JAIL for p in player.pieces)
```

> Los helpers `_current_player` y `_all_in_jail` se usarán en tareas siguientes; los metemos ahora para tener la forma.

- [ ] **Step 4: Verificar que pasan**

Run: `.venv/bin/pytest tests/test_engine_turns.py -v`
Expected: `11 passed`.

- [ ] **Step 5: Commit**

```bash
git add parques/engine.py tests/test_engine_turns.py
git commit -m "feat: engine.roll_dice base case"
```

---

## Task 9: Engine — `roll_dice` caso "todas en cárcel" con 3 oportunidades

**Files:**
- Modify: `parques/engine.py`
- Modify: `tests/test_engine_turns.py`

**Comportamiento esperado:**
- Si al entrar a `roll_dice` el jugador actual tiene las 4 fichas en cárcel y `initial_rolls_remaining == 0`: se inicializa a 3.
- Si `initial_rolls_remaining > 0` y el tiro **no es par**: decrementar; si llega a 0 → pasar turno (volver a `ROLLING` con el siguiente jugador) y descartar `pending_dice`.
- Si sale par: salir del modo 3-oportunidades (`initial_rolls_remaining = 0`), normal.

- [ ] **Step 1: Extender tests**

```python
def test_all_in_jail_initializes_three_opportunities(scripted_rng):
    # Alice wins first turn. All pieces in jail. First roll non-pair (2,3).
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([6, 5, 3, 4,  # initial rolls: Alice=11, Bob=7
                          2, 3]),      # Alice's first actual roll
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)
    engine.roll_dice(game)
    assert game.initial_rolls_remaining == 2  # started at 3, consumed 1


def test_three_non_pair_rolls_pass_turn(scripted_rng):
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([6, 5, 3, 4,  # initial rolls
                          2, 3, 1, 4, 5, 6,  # Alice's 3 non-pairs
                          1, 2]),            # Bob's first roll
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)

    # Alice's 1st non-pair
    engine.roll_dice(game)
    game.pending_dice = []                    # pretend she had no move → skipped
    game.phase = GamePhase.ROLLING             # manual transition for this unit test
    assert game.current_turn_index == 0       # still Alice

    # 2nd non-pair
    engine.roll_dice(game)
    game.pending_dice = []
    game.phase = GamePhase.ROLLING

    # 3rd non-pair → turn passes
    engine.roll_dice(game)
    assert game.current_turn_index == 1       # now Bob
    assert game.phase is GamePhase.ROLLING
    assert game.initial_rolls_remaining == 0
    # Bob rolls
    engine.roll_dice(game)
    # Bob also has all pieces in jail → starts his own 3 opportunities
    assert game.initial_rolls_remaining == 2


def test_pair_clears_three_opportunity_counter(scripted_rng):
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([6, 5, 3, 4, 4, 4]),  # Alice first, rolls pair 4-4
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)
    engine.roll_dice(game)
    assert game.initial_rolls_remaining == 0    # never entered counter mode
    assert game.pending_dice == [4, 4]
    assert game.consecutive_pairs == 1
```

> **Nota:** los tests que necesitan transicionar manualmente de MOVING a ROLLING lo hacen hasta que `apply_move` esté implementado (Task 13+). Luego se refactorizan si es más limpio.

- [ ] **Step 2: Verificar fallos**

Run: `.venv/bin/pytest tests/test_engine_turns.py::test_all_in_jail_initializes_three_opportunities -v`
Expected: FAIL (still 0).

- [ ] **Step 3: Ampliar `roll_dice`**

Reemplazar el cuerpo de `roll_dice`:
```python
def roll_dice(game: Game) -> tuple[int, int]:
    if game.phase is not GamePhase.ROLLING:
        raise WrongPhase("not in ROLLING phase")

    rng = game._rng  # type: ignore[attr-defined]
    d1 = rng.randint(1, 6)
    d2 = rng.randint(1, 6)
    is_pair = d1 == d2

    player = _current_player(game)

    # Handle "all pieces in jail" 3-opportunities mode.
    if _all_in_jail(player):
        if game.initial_rolls_remaining == 0 and not is_pair:
            # Entering the mode with a non-pair roll: set to 3 then decrement.
            game.initial_rolls_remaining = 3
        if not is_pair:
            game.initial_rolls_remaining -= 1
            if game.initial_rolls_remaining <= 0:
                # Exhausted: pass turn, keep dice discarded.
                game.initial_rolls_remaining = 0
                game.pending_dice = []
                game.consecutive_pairs = 0
                _advance_turn(game)
                return d1, d2
        else:
            # Pair clears the counter — play normally.
            game.initial_rolls_remaining = 0

    if is_pair:
        game.consecutive_pairs += 1
    else:
        game.consecutive_pairs = 0

    # TODO Task 10: triple-pair → CROWNING path.
    game.pending_dice = [d1, d2]
    game.phase = GamePhase.MOVING
    return d1, d2


def _advance_turn(game: Game) -> None:
    """Move to next player; reset per-turn counters."""
    game.consecutive_pairs = 0
    game.initial_rolls_remaining = 0
    game.current_turn_index = (game.current_turn_index + 1) % len(game.turn_order)
    game.phase = GamePhase.ROLLING
```

- [ ] **Step 4: Verificar que pasan**

Run: `.venv/bin/pytest tests/test_engine_turns.py -v`
Expected: `14 passed`.

- [ ] **Step 5: Commit**

```bash
git add parques/engine.py tests/test_engine_turns.py
git commit -m "feat: roll_dice handles all-in-jail three-opportunities"
```

---

## Task 10: Engine — `roll_dice` detección de triple par → CROWNING

**Files:**
- Modify: `parques/engine.py`
- Modify: `tests/test_engine_turns.py`

- [ ] **Step 1: Extender tests**

```python
def test_third_consecutive_pair_triggers_crowning(scripted_rng):
    # Alice wins first turn. Rolls 3-3 (pair), 5-5 (pair), 6-6 (pair).
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([6, 5, 3, 4,  # initial rolls
                          3, 3, 5, 5, 6, 6]),
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)

    engine.roll_dice(game)     # 3-3 → MOVING, pairs=1
    assert game.phase is GamePhase.MOVING
    assert game.consecutive_pairs == 1
    # Pretend Alice moved and emptied pending_dice; she re-rolls.
    game.pending_dice = []
    game.phase = GamePhase.ROLLING

    engine.roll_dice(game)     # 5-5 → MOVING, pairs=2
    assert game.consecutive_pairs == 2
    game.pending_dice = []
    game.phase = GamePhase.ROLLING

    engine.roll_dice(game)     # 6-6 → CROWNING (no MOVING)
    assert game.phase is GamePhase.CROWNING
    assert game.consecutive_pairs == 3
    assert game.pending_dice == []  # not filled
```

- [ ] **Step 2: Verificar fallos**

Expected: `AssertionError` en `game.phase is CROWNING`.

- [ ] **Step 3: Añadir detección de triple par en `roll_dice`**

En `roll_dice`, justo después de incrementar `consecutive_pairs`:
```python
if is_pair:
    game.consecutive_pairs += 1
    if game.consecutive_pairs >= 3:
        game.pending_dice = []
        game.phase = GamePhase.CROWNING
        return d1, d2
else:
    game.consecutive_pairs = 0
```

- [ ] **Step 4: Verificar que pasan**

Run: `.venv/bin/pytest tests/test_engine_turns.py -v`
Expected: `15 passed`.

- [ ] **Step 5: Commit**

```bash
git add parques/engine.py tests/test_engine_turns.py
git commit -m "feat: triple-pair transitions roll_dice to CROWNING"
```

---

## Task 11: Engine — `available_moves` para ADVANCE (avance básico)

**Files:**
- Modify: `parques/engine.py`
- Create: `tests/test_engine_movement.py`

**Alcance de la tarea:** fichas ya `ON_BOARD`, movimiento que no entra a recta final ni captura ni es `EXIT_JAIL`.

- [ ] **Step 1: Escribir tests**

`tests/test_engine_movement.py`:
```python
import pytest

from parques import engine
from parques.entities import (
    Color, GamePhase, Move, MoveAction, PieceState,
)
from tests.conftest import force_dice


def _game_with_piece_on_board(scripted_rng, color=Color.RED, position=10):
    game = engine.new_game(
        [("Alice", color), ("Bob", Color.BLUE)],
        rng=scripted_rng([6, 5, 3, 4]),  # Alice=11 → first
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)
    # Hand-place Alice's piece 0 on the circuit.
    alice_piece = game.players[0].pieces[0]
    alice_piece.state = PieceState.ON_BOARD
    alice_piece.circuit_position = position
    return game


def test_available_moves_lists_advance_per_die(scripted_rng):
    game = _game_with_piece_on_board(scripted_rng, position=10)
    force_dice(game, 3, 4)
    moves = engine.available_moves(game)
    # One piece on board + 2 dice → 2 ADVANCE moves (same piece, d=3 and d=4).
    assert sorted((m.piece_index, m.dice_value, m.action) for m in moves) == [
        (0, 3, MoveAction.ADVANCE),
        (0, 4, MoveAction.ADVANCE),
    ]


def test_available_moves_returns_empty_outside_moving(two_player_game):
    assert engine.available_moves(two_player_game) == []


def test_available_moves_is_deterministic(scripted_rng):
    """Spec contract: sorted by piece_index asc, then dice_value asc."""
    game = _game_with_piece_on_board(scripted_rng, position=10)
    # Give Alice a second piece on board at a different position.
    alice = game.players[0]
    alice.pieces[2].state = PieceState.ON_BOARD
    alice.pieces[2].circuit_position = 20
    force_dice(game, 3, 5)
    moves = engine.available_moves(game)
    keys = [(m.piece_index, m.dice_value) for m in moves]
    assert keys == sorted(keys)
```

- [ ] **Step 2: Verificar fallos**

Run: `.venv/bin/pytest tests/test_engine_movement.py -v`
Expected: `AttributeError: no attribute 'available_moves'`.

- [ ] **Step 3: Implementar `available_moves` — caso ADVANCE**

En `engine.py`:
```python
from parques.entities import Move, MoveAction


def available_moves(game: Game) -> list[Move]:
    """Return every legal Move the current player can make."""
    if game.phase is not GamePhase.MOVING:
        return []

    player = _current_player(game)
    moves: list[Move] = []

    for piece in player.pieces:
        if piece.state is not PieceState.ON_BOARD:
            continue
        for die in set(game.pending_dice):
            moves.append(Move(
                piece_index=piece.index,
                dice_value=die,
                action=MoveAction.ADVANCE,
            ))

    moves.sort(key=lambda m: (m.piece_index, m.dice_value))
    return moves
```

> **Nota:** `set(game.pending_dice)` deduplica pares — si los dos dados son iguales, no hay dos Moves idénticos. Tareas siguientes añaden EXIT_JAIL, CAPTURE, ENTER_HOME_STRETCH, REACH_GOAL.

- [ ] **Step 4: Verificar que pasan**

Run: `.venv/bin/pytest tests/test_engine_movement.py -v`
Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add parques/engine.py tests/test_engine_movement.py
git commit -m "feat: available_moves for ADVANCE"
```

---

## Task 12: Engine — `available_moves` EXIT_JAIL

**Files:**
- Modify: `parques/engine.py`
- Modify: `tests/test_engine_movement.py`

- [ ] **Step 1: Tests**

```python
def test_available_moves_includes_exit_jail_on_pair(scripted_rng):
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([6, 5, 3, 4]),
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)
    # Alice all in jail. Manually set pending dice to a pair.
    force_dice(game, 4, 4)
    game.consecutive_pairs = 1  # simulate we just rolled the pair
    moves = engine.available_moves(game)
    actions = {m.action for m in moves}
    assert MoveAction.EXIT_JAIL in actions


def test_available_moves_no_exit_jail_without_pair(scripted_rng):
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([6, 5, 3, 4]),
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)
    force_dice(game, 3, 5)
    moves = engine.available_moves(game)
    assert MoveAction.EXIT_JAIL not in {m.action for m in moves}
```

- [ ] **Step 2: Verificar fallos**

Expected: `AssertionError: EXIT_JAIL not in ...`.

- [ ] **Step 3: Ampliar `available_moves`**

**Regla:** `EXIT_JAIL` consume **ambos dados del par** (interpretación del spec: "los dados del par se consumen sacando la ficha"). Emitimos **un solo `Move`** con `dice_value = d1 + d2` (p. ej. `8` para 4-4); al aplicarlo, `apply_move` vaciará `pending_dice` en lugar de consumir un solo valor.

Justo antes del loop que añade ADVANCE, agregar:
```python
    is_pair_roll = (
        len(game.pending_dice) == 2
        and game.pending_dice[0] == game.pending_dice[1]
    )

    for piece in player.pieces:
        if piece.state is PieceState.IN_JAIL and is_pair_roll:
            moves.append(Move(
                piece_index=piece.index,
                dice_value=game.pending_dice[0] + game.pending_dice[1],
                action=MoveAction.EXIT_JAIL,
            ))
```

- [ ] **Step 4: Verificar que pasan**

Run: `.venv/bin/pytest tests/test_engine_movement.py -v`
Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
git add parques/engine.py tests/test_engine_movement.py
git commit -m "feat: available_moves EXIT_JAIL with pairs"
```

---

## Task 13: Engine — `available_moves` CAPTURE (detección de captura)

**Files:**
- Modify: `parques/engine.py`
- Create: `tests/test_engine_capture.py`

**Regla:** si la casilla destino de un ADVANCE tiene una ficha **rival** en casilla **no segura, no salida**, el action del Move es `CAPTURE` en vez de `ADVANCE`.

- [ ] **Step 1: Tests**

`tests/test_engine_capture.py`:
```python
import pytest
from parques import engine
from parques.entities import Color, Move, MoveAction, PieceState
from parques.board import is_safe
from tests.conftest import force_dice


def _game_setup(scripted_rng):
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([6, 5, 3, 4]),
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)
    return game


def test_move_onto_rival_on_normal_cell_is_capture(scripted_rng):
    game = _game_setup(scripted_rng)
    # Alice's piece at 10 (not safe), Bob's piece at 13 (not safe).
    alice = game.players[0].pieces[0]
    alice.state = PieceState.ON_BOARD
    alice.circuit_position = 10
    bob = game.players[1].pieces[0]
    bob.state = PieceState.ON_BOARD
    bob.circuit_position = 13
    assert not is_safe(13), "test precondition: target not safe"

    force_dice(game, 3, 5)
    moves = engine.available_moves(game)
    capture_moves = [m for m in moves if m.action is MoveAction.CAPTURE]
    assert len(capture_moves) == 1
    assert capture_moves[0].piece_index == alice.index
    assert capture_moves[0].dice_value == 3


def test_move_onto_rival_on_safe_cell_is_plain_advance(scripted_rng):
    game = _game_setup(scripted_rng)
    # Find a safe cell reachable by dice=5 from some position.
    safe_target = 6  # from the SAFES set
    alice = game.players[0].pieces[0]
    alice.state = PieceState.ON_BOARD
    alice.circuit_position = safe_target - 5
    bob = game.players[1].pieces[0]
    bob.state = PieceState.ON_BOARD
    bob.circuit_position = safe_target

    force_dice(game, 5, 1)
    moves = engine.available_moves(game)
    # The 5 move lands on a safe cell where a rival sits → ADVANCE, not CAPTURE.
    relevant = [m for m in moves if m.dice_value == 5 and m.piece_index == 0]
    assert len(relevant) == 1
    assert relevant[0].action is MoveAction.ADVANCE


def test_move_onto_own_piece_is_plain_advance(scripted_rng):
    game = _game_setup(scripted_rng)
    alice0 = game.players[0].pieces[0]
    alice1 = game.players[0].pieces[1]
    alice0.state = PieceState.ON_BOARD
    alice0.circuit_position = 10
    alice1.state = PieceState.ON_BOARD
    alice1.circuit_position = 13

    force_dice(game, 3, 5)
    moves = engine.available_moves(game)
    # Alice piece 0 + dice 3 → lands on her own piece 1 at 13 → ADVANCE.
    m = next(m for m in moves if m.piece_index == 0 and m.dice_value == 3)
    assert m.action is MoveAction.ADVANCE
```

- [ ] **Step 2: Verificar fallos**

Expected: cast el action de ADVANCE sigue siendo ADVANCE aunque debería ser CAPTURE.

- [ ] **Step 3: Refinar `available_moves`**

Cambiar el bloque que añade ADVANCE:
```python
    from parques.board import is_safe, next_position, EXITS

    enemy_positions: dict[int, Player] = {}
    for other in game.players:
        if other is player:
            continue
        for p in other.pieces:
            if p.state is PieceState.ON_BOARD and p.circuit_position is not None:
                enemy_positions[p.circuit_position] = other

    for piece in player.pieces:
        if piece.state is not PieceState.ON_BOARD:
            continue
        for die in set(game.pending_dice):
            target = next_position(piece.circuit_position, die)
            action = MoveAction.ADVANCE
            # Capture detection (Task 13).
            # is_safe() already covers the 4 exits (they're in SAFES).
            if target in enemy_positions and not is_safe(target):
                action = MoveAction.CAPTURE
            moves.append(Move(
                piece_index=piece.index,
                dice_value=die,
                action=action,
            ))
```

- [ ] **Step 4: Verificar**

Run: `.venv/bin/pytest tests/ -v`
Expected: todos los tests previos + los 3 nuevos pasan.

- [ ] **Step 5: Commit**

```bash
git add parques/engine.py tests/test_engine_capture.py
git commit -m "feat: available_moves detects CAPTURE"
```

---

## Task 14: Engine — `available_moves` ENTER_HOME_STRETCH + REACH_GOAL

**Files:**
- Modify: `parques/engine.py`
- Create: `tests/test_engine_home_stretch.py`

**Reglas:**
- Si el avance cruza o toca la `home_stretch_entry_for(color)`, el action es `ENTER_HOME_STRETCH`.
- Si la ficha ya está en `IN_HOME_STRETCH` y el dado la lleva exactamente a `HOME_STRETCH_SIZE - 1` (posición 7), el action es `REACH_GOAL`.
- Si el dado la lleva a una posición válida dentro de `0..6` (no la meta), es `ADVANCE` dentro de home stretch — usamos el mismo action `ADVANCE` pero interpretado como movimiento en recta final.
- Si el dado la pasa (ej. está en 6 y saca 5), **omitir** ese `Move` (no legal).

> **Ajuste:** en lugar de reusar `ADVANCE` para "avanzar dentro de la recta final", mantenemos la semántica clara con dos opciones: (a) un action nuevo `ADVANCE_HOME_STRETCH`, o (b) reusar `ADVANCE` y que `apply_move` mire el estado actual de la ficha. Escogemos **(b)** — consistencia con el spec que define solo 5 acciones.

- [ ] **Step 1: Tests**

`tests/test_engine_home_stretch.py`:
```python
import pytest
from parques import engine
from parques.board import HOME_STRETCH_ENTRY, HOME_STRETCH_SIZE
from parques.entities import Color, MoveAction, PieceState
from tests.conftest import force_dice


def _game_setup(scripted_rng):
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([6, 5, 3, 4]),
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)
    return game


def test_advance_over_home_entry_becomes_enter_home_stretch(scripted_rng):
    game = _game_setup(scripted_rng)
    red_entry = HOME_STRETCH_ENTRY[Color.RED]  # 71
    piece = game.players[0].pieces[0]
    piece.state = PieceState.ON_BOARD
    piece.circuit_position = red_entry - 2  # 69

    force_dice(game, 3, 5)
    moves = engine.available_moves(game)
    # With 3 dice → target is 72, which is past entry 71 → ENTER_HOME_STRETCH.
    m = next(m for m in moves if m.dice_value == 3)
    assert m.action is MoveAction.ENTER_HOME_STRETCH


def test_piece_in_home_stretch_reaching_goal_exactly(scripted_rng):
    game = _game_setup(scripted_rng)
    piece = game.players[0].pieces[0]
    piece.state = PieceState.IN_HOME_STRETCH
    piece.home_stretch_position = HOME_STRETCH_SIZE - 3  # 5

    force_dice(game, 2, 4)
    moves = engine.available_moves(game)
    # dice=2 → lands on 7 (goal) → REACH_GOAL; dice=4 would overshoot → skipped.
    actions_by_die = {m.dice_value: m.action for m in moves if m.piece_index == 0}
    assert actions_by_die == {2: MoveAction.REACH_GOAL}


def test_piece_in_home_stretch_advance_does_not_overshoot(scripted_rng):
    game = _game_setup(scripted_rng)
    piece = game.players[0].pieces[0]
    piece.state = PieceState.IN_HOME_STRETCH
    piece.home_stretch_position = 4

    force_dice(game, 2, 5)
    moves = engine.available_moves(game)
    # dice=2 → lands on 6, still in home stretch (not goal) → ADVANCE.
    # dice=5 → overshoots 7 → skipped.
    dice_emitted = {m.dice_value for m in moves if m.piece_index == 0}
    assert dice_emitted == {2}
    advance = next(m for m in moves if m.piece_index == 0 and m.dice_value == 2)
    assert advance.action is MoveAction.ADVANCE


def test_piece_in_home_stretch_protected_no_capture(scripted_rng):
    # Nothing to do: the enemy cannot have a circuit_position == home stretch
    # index, since home stretch positions are indexed separately. A piece in
    # home_stretch is out of the circuit. This test just asserts it.
    game = _game_setup(scripted_rng)
    piece = game.players[0].pieces[0]
    piece.state = PieceState.IN_HOME_STRETCH
    piece.home_stretch_position = 3
    force_dice(game, 2, 3)
    # Bob with a piece on the circuit — irrelevant to Alice's HS piece.
    game.players[1].pieces[0].state = PieceState.ON_BOARD
    game.players[1].pieces[0].circuit_position = 5
    moves = engine.available_moves(game)
    assert all(m.action is not MoveAction.CAPTURE for m in moves)
```

- [ ] **Step 2: Verificar fallos**

Expected: varios asserts fallan porque `available_moves` aún no genera moves para IN_HOME_STRETCH ni detecta ENTER_HOME_STRETCH.

- [ ] **Step 3: Refactorizar el loop de fichas (decisión de action en una sola pasada)**

> **Refactor importante:** el loop que Task 13 dejó tiene `if piece.state is not PieceState.ON_BOARD: continue` como guard. Lo reemplazamos por un `if/elif` explícito que maneje ON_BOARD y IN_HOME_STRETCH. Además, para las fichas ON_BOARD decidimos el `action` **en una sola pasada** (no emitimos ADVANCE y luego lo reemplazamos con ENTER_HOME_STRETCH vía filter — eso era frágil).

Reemplazar el loop completo de fichas por:
```python
    for piece in player.pieces:
        if piece.state is PieceState.ON_BOARD:
            entry = HOME_STRETCH_ENTRY[player.color]
            for die in set(game.pending_dice):
                # 1) Does this move cross the home-stretch entry?
                if _crossed_home_entry(piece.circuit_position, die, entry):
                    overflow = _home_stretch_overflow(
                        piece.circuit_position, die, entry,
                    )
                    if overflow == HOME_STRETCH_SIZE - 1:
                        action = MoveAction.REACH_GOAL
                    elif overflow < HOME_STRETCH_SIZE:
                        action = MoveAction.ENTER_HOME_STRETCH
                    else:
                        continue  # overshoot → this die can't be used
                # 2) Plain circuit move (may be a capture).
                else:
                    target = next_position(piece.circuit_position, die)
                    if target in enemy_positions and not is_safe(target):
                        action = MoveAction.CAPTURE
                    else:
                        action = MoveAction.ADVANCE
                moves.append(Move(
                    piece_index=piece.index, dice_value=die, action=action,
                ))

        elif piece.state is PieceState.IN_HOME_STRETCH:
            for die in set(game.pending_dice):
                new_pos = piece.home_stretch_position + die
                if new_pos == HOME_STRETCH_SIZE - 1:
                    moves.append(Move(piece.index, die, MoveAction.REACH_GOAL))
                elif new_pos < HOME_STRETCH_SIZE - 1:
                    moves.append(Move(piece.index, die, MoveAction.ADVANCE))
                # else: overshoot, skip this die

        # IN_JAIL is handled by the EXIT_JAIL block (Task 12), CROWNED pieces never move.
```

> **Nota:** este refactor sustituye también el bloque que Task 13 añadió para ADVANCE/CAPTURE — la decisión de `CAPTURE` vs `ADVANCE` vive ahora en la rama "plain circuit move" de arriba. Los tests de Task 13 siguen pasando porque los casos de captura siguen detectándose; solo cambia la forma del código.

Añadir helpers:
```python
def _crossed_home_entry(start: int, steps: int, entry: int) -> bool:
    """True if moving `steps` from `start` passes through or lands beyond `entry`."""
    # Distance from start to entry following the circuit:
    distance = (entry - start) % BOARD_SIZE
    return distance < steps


def _home_stretch_overflow(start: int, steps: int, entry: int) -> int:
    """How many cells into the home stretch (0-indexed) the piece lands."""
    distance = (entry - start) % BOARD_SIZE
    return steps - distance - 1
```

Añadir imports al tope:
```python
from parques.board import (
    BOARD_SIZE, EXITS, HOME_STRETCH_ENTRY, HOME_STRETCH_SIZE,
    is_safe, next_position,
)
```

- [ ] **Step 4: Verificar**

Run: `.venv/bin/pytest tests/ -v`
Expected: tests nuevos y existentes pasan.

- [ ] **Step 5: Commit**

```bash
git add parques/engine.py tests/test_engine_home_stretch.py
git commit -m "feat: available_moves for home stretch entry and goal"
```

---

## Task 15: Engine — `apply_move` ADVANCE (efecto + transición de turno)

**Files:**
- Modify: `parques/engine.py`
- Modify: `tests/test_engine_movement.py`

- [ ] **Step 1: Tests**

```python
from parques.entities import MoveResult


def test_apply_move_advance_consumes_one_die_and_updates_piece(scripted_rng):
    game = _game_with_piece_on_board(scripted_rng, position=10)
    force_dice(game, 3, 5)
    move = Move(piece_index=0, dice_value=3, action=MoveAction.ADVANCE)
    result = engine.apply_move(game, move)
    assert result.action is MoveAction.ADVANCE
    assert game.players[0].pieces[0].circuit_position == 13
    assert game.pending_dice == [5]
    assert game.phase is GamePhase.MOVING


def test_apply_move_advances_turn_when_dice_exhausted_non_pair(scripted_rng):
    game = _game_with_piece_on_board(scripted_rng, position=10)
    force_dice(game, 3, 5)
    engine.apply_move(game, Move(0, 3, MoveAction.ADVANCE))
    engine.apply_move(game, Move(0, 5, MoveAction.ADVANCE))
    assert game.phase is GamePhase.ROLLING
    assert game.current_turn_index == 1  # Bob's turn


def test_apply_move_rolling_again_after_pair(scripted_rng):
    game = _game_with_piece_on_board(scripted_rng, position=10)
    force_dice(game, 4, 4)
    game.consecutive_pairs = 1  # simulate roll_dice having bumped it
    engine.apply_move(game, Move(0, 4, MoveAction.ADVANCE))
    engine.apply_move(game, Move(0, 4, MoveAction.ADVANCE))
    assert game.phase is GamePhase.ROLLING
    assert game.current_turn_index == 0  # still Alice


def test_apply_move_rejects_unknown_move(scripted_rng):
    game = _game_with_piece_on_board(scripted_rng, position=10)
    force_dice(game, 3, 5)
    with pytest.raises(engine.InvalidMove):
        engine.apply_move(game, Move(0, 6, MoveAction.ADVANCE))  # no die 6
```

- [ ] **Step 2: Verificar fallos**

Expected: `AttributeError: no attribute 'apply_move'`.

- [ ] **Step 3: Implementar `apply_move` básico (ADVANCE)**

```python
from parques.exceptions import InvalidMove


def apply_move(game: Game, move: Move) -> MoveResult:
    if game.phase is not GamePhase.MOVING:
        raise WrongPhase("not in MOVING phase")
    if move not in available_moves(game):
        raise InvalidMove(f"move not in available_moves: {move!r}")

    player = _current_player(game)
    piece = player.pieces[move.piece_index]

    result: MoveResult
    if move.action is MoveAction.ADVANCE and piece.state is PieceState.ON_BOARD:
        piece.circuit_position = next_position(piece.circuit_position, move.dice_value)
        result = MoveResult(action=MoveAction.ADVANCE)
    else:
        raise NotImplementedError(
            f"Task 15 only handles ADVANCE on circuit; got {move.action}"
        )

    _consume_die(game, move.dice_value)
    _finish_move_turn_transition(game)
    return result


def _consume_die(game: Game, die: int) -> None:
    game.pending_dice.remove(die)


def _finish_move_turn_transition(game: Game) -> None:
    if game.pending_dice:
        return  # still MOVING; same player picks next
    # Dice exhausted.
    was_pair = game.consecutive_pairs > 0
    if was_pair and game.consecutive_pairs < 3:
        game.phase = GamePhase.ROLLING   # same player re-rolls
    else:
        _advance_turn(game)
```

> **Nota:** el re-export de `InvalidMove`, `WrongPhase`, `DuplicatePlayer` en `engine.py` ya se hizo en Task 6 — los tests pueden usar `engine.InvalidMove` sin import extra.

- [ ] **Step 4: Verificar**

Run: `.venv/bin/pytest tests/ -v`
Expected: tests nuevos pasan.

- [ ] **Step 5: Commit**

```bash
git add parques/engine.py tests/test_engine_movement.py
git commit -m "feat: apply_move handles ADVANCE and turn transitions"
```

---

## Task 16: Engine — `apply_move` EXIT_JAIL

**Files:**
- Modify: `parques/engine.py`
- Modify: `tests/test_engine_movement.py`

- [ ] **Step 1: Tests**

```python
from parques.board import EXITS


def test_apply_move_exit_jail_places_piece_on_exit_and_consumes_pair(scripted_rng):
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([6, 5, 3, 4]),
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)
    force_dice(game, 4, 4)
    game.consecutive_pairs = 1

    total = 4 + 4
    move = Move(piece_index=0, dice_value=total, action=MoveAction.EXIT_JAIL)
    engine.apply_move(game, move)
    piece = game.players[0].pieces[0]
    assert piece.state is PieceState.ON_BOARD
    assert piece.circuit_position == EXITS[Color.RED]
    assert game.pending_dice == []   # both dice consumed by the pair
    assert game.phase is GamePhase.ROLLING  # re-roll (pair)
```

- [ ] **Step 2: Fail**

Expected: `NotImplementedError`.

- [ ] **Step 3: Implementar rama EXIT_JAIL**

En `apply_move`, añadir antes del `else: raise NotImplementedError`:
```python
    elif move.action is MoveAction.EXIT_JAIL:
        piece.state = PieceState.ON_BOARD
        piece.circuit_position = EXITS[player.color]
        # EXIT_JAIL consumes BOTH dice of the pair.
        game.pending_dice = []
        _finish_move_turn_transition(game)
        return MoveResult(action=MoveAction.EXIT_JAIL)
```

- [ ] **Step 4: Pass**

Run: `.venv/bin/pytest tests/ -v`

- [ ] **Step 5: Commit**

```bash
git add parques/engine.py tests/test_engine_movement.py
git commit -m "feat: apply_move handles EXIT_JAIL"
```

---

## Task 17: Engine — `apply_move` CAPTURE

**Files:**
- Modify: `parques/engine.py`
- Modify: `tests/test_engine_capture.py`

- [ ] **Step 1: Tests**

```python
def test_apply_move_capture_sends_rival_to_jail(scripted_rng):
    game = _game_setup(scripted_rng)
    alice = game.players[0].pieces[0]
    alice.state = PieceState.ON_BOARD
    alice.circuit_position = 10
    bob = game.players[1].pieces[0]
    bob.state = PieceState.ON_BOARD
    bob.circuit_position = 13

    force_dice(game, 3, 5)
    result = engine.apply_move(game, Move(0, 3, MoveAction.CAPTURE))
    assert result.action is MoveAction.CAPTURE
    assert result.captured is not None
    assert result.captured.index == 0
    assert bob.state is PieceState.IN_JAIL
    assert bob.circuit_position is None
    assert alice.circuit_position == 13
```

- [ ] **Step 2: Fail**

Expected: `NotImplementedError`.

- [ ] **Step 3: Rama CAPTURE**

En `apply_move`:
```python
    elif move.action is MoveAction.CAPTURE and piece.state is PieceState.ON_BOARD:
        target = next_position(piece.circuit_position, move.dice_value)
        captured = _capture_at(game, target, player)
        piece.circuit_position = target
        _consume_die(game, move.dice_value)
        _finish_move_turn_transition(game)
        return MoveResult(action=MoveAction.CAPTURE, captured=captured)


def _capture_at(game: Game, position: int, attacker: Player) -> Piece | None:
    for other in game.players:
        if other is attacker:
            continue
        for p in other.pieces:
            if p.state is PieceState.ON_BOARD and p.circuit_position == position:
                captured_snapshot = Piece(
                    index=p.index,
                    state=PieceState.ON_BOARD,
                    circuit_position=position,
                )
                p.state = PieceState.IN_JAIL
                p.circuit_position = None
                return captured_snapshot
    return None
```

Nota: devolvemos un **snapshot** de la ficha capturada (copia) para que el resultado sea self-contained, no una referencia mutable.

- [ ] **Step 4: Pass**

- [ ] **Step 5: Commit**

```bash
git add parques/engine.py tests/test_engine_capture.py
git commit -m "feat: apply_move handles CAPTURE"
```

---

## Task 18: Engine — `apply_move` ENTER_HOME_STRETCH, REACH_GOAL y ADVANCE dentro de recta final

**Files:**
- Modify: `parques/engine.py`
- Modify: `tests/test_engine_home_stretch.py`

- [ ] **Step 1: Tests**

```python
def test_apply_enter_home_stretch_sets_state_and_position(scripted_rng):
    game = _game_setup(scripted_rng)
    piece = game.players[0].pieces[0]
    piece.state = PieceState.ON_BOARD
    piece.circuit_position = HOME_STRETCH_ENTRY[Color.RED] - 2  # 69
    force_dice(game, 3, 1)
    engine.apply_move(game, Move(0, 3, MoveAction.ENTER_HOME_STRETCH))
    assert piece.state is PieceState.IN_HOME_STRETCH
    assert piece.circuit_position is None
    # Overflow 0 → home_stretch_position 0.
    assert piece.home_stretch_position == 0


def test_apply_advance_within_home_stretch(scripted_rng):
    game = _game_setup(scripted_rng)
    piece = game.players[0].pieces[0]
    piece.state = PieceState.IN_HOME_STRETCH
    piece.home_stretch_position = 3
    force_dice(game, 2, 1)
    engine.apply_move(game, Move(0, 2, MoveAction.ADVANCE))
    assert piece.home_stretch_position == 5
    assert piece.state is PieceState.IN_HOME_STRETCH


def test_apply_reach_goal_marks_piece_crowned(scripted_rng):
    game = _game_setup(scripted_rng)
    piece = game.players[0].pieces[0]
    piece.state = PieceState.IN_HOME_STRETCH
    piece.home_stretch_position = 5
    force_dice(game, 2, 6)
    engine.apply_move(game, Move(0, 2, MoveAction.REACH_GOAL))
    assert piece.state is PieceState.CROWNED
    assert piece.home_stretch_position is None
```

- [ ] **Step 2: Fail**

- [ ] **Step 3: Ramas nuevas en `apply_move`**

```python
    elif move.action is MoveAction.ENTER_HOME_STRETCH and piece.state is PieceState.ON_BOARD:
        entry = HOME_STRETCH_ENTRY[player.color]
        overflow = _home_stretch_overflow(
            piece.circuit_position, move.dice_value, entry,
        )
        piece.state = PieceState.IN_HOME_STRETCH
        piece.circuit_position = None
        piece.home_stretch_position = overflow
        _consume_die(game, move.dice_value)
        _finish_move_turn_transition(game)
        return MoveResult(action=MoveAction.ENTER_HOME_STRETCH)

    elif move.action is MoveAction.REACH_GOAL:
        piece.state = PieceState.CROWNED
        piece.circuit_position = None
        piece.home_stretch_position = None
        _consume_die(game, move.dice_value)
        # Win detection is handled in Task 20.
        _finish_move_turn_transition(game)
        return MoveResult(action=MoveAction.REACH_GOAL, reached_goal=True)

    elif move.action is MoveAction.ADVANCE and piece.state is PieceState.IN_HOME_STRETCH:
        piece.home_stretch_position += move.dice_value
        _consume_die(game, move.dice_value)
        _finish_move_turn_transition(game)
        return MoveResult(action=MoveAction.ADVANCE)
```

- [ ] **Step 4: Pass**

- [ ] **Step 5: Commit**

```bash
git add parques/engine.py tests/test_engine_home_stretch.py
git commit -m "feat: apply_move for home stretch entry, advance, and goal"
```

---

## Task 19: Engine — `skip_turn`

**Files:**
- Modify: `parques/engine.py`
- Modify: `tests/test_engine_turns.py`

- [ ] **Step 1: Tests**

```python
def test_skip_turn_discards_dice_and_passes_to_next_player(scripted_rng):
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([6, 5, 3, 4]),
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)
    force_dice(game, 3, 5)
    engine.skip_turn(game)
    assert game.pending_dice == []
    assert game.phase is GamePhase.ROLLING
    assert game.current_turn_index == 1


def test_skip_turn_rejects_empty_dice(scripted_rng):
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([6, 5, 3, 4]),
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)
    game.phase = GamePhase.MOVING
    game.pending_dice = []
    with pytest.raises(ValueError):
        engine.skip_turn(game)


def test_skip_turn_rejects_wrong_phase(two_player_game):
    with pytest.raises(engine.WrongPhase):
        engine.skip_turn(two_player_game)
```

- [ ] **Step 2: Fail**

- [ ] **Step 3: Implementar**

```python
def skip_turn(game: Game) -> None:
    if game.phase is not GamePhase.MOVING:
        raise WrongPhase("not in MOVING phase")
    if not game.pending_dice:
        raise ValueError("no pending dice to skip")
    game.pending_dice = []
    _advance_turn(game)
```

- [ ] **Step 4: Pass**

- [ ] **Step 5: Commit**

```bash
git add parques/engine.py tests/test_engine_turns.py
git commit -m "feat: engine.skip_turn"
```

---

## Task 20: Engine — `crown_piece` y detección de victoria

**Files:**
- Modify: `parques/engine.py`
- Modify: `tests/test_engine_turns.py`

- [ ] **Step 1: Tests**

```python
def test_crown_piece_moves_selected_piece_to_crowned(scripted_rng):
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([6, 5, 3, 4]),
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)
    game.phase = GamePhase.CROWNING
    engine.crown_piece(game, piece_index=1)
    assert game.players[0].pieces[1].state is PieceState.CROWNED
    assert game.phase is GamePhase.ROLLING   # same player continues
    assert game.consecutive_pairs == 0        # reset after crowning
    assert game.current_turn_index == 0


def test_crown_piece_rejects_already_crowned(scripted_rng):
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([6, 5, 3, 4]),
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)
    game.players[0].pieces[0].state = PieceState.CROWNED
    game.phase = GamePhase.CROWNING
    with pytest.raises(ValueError):
        engine.crown_piece(game, 0)


def test_crown_piece_rejects_invalid_index(scripted_rng):
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([6, 5, 3, 4]),
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)
    game.phase = GamePhase.CROWNING
    with pytest.raises(ValueError):
        engine.crown_piece(game, 42)


def test_fourth_crowned_piece_finishes_game(scripted_rng):
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([6, 5, 3, 4]),
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)
    # Put Alice's first 3 pieces already crowned.
    for i in range(3):
        game.players[0].pieces[i].state = PieceState.CROWNED
    # Alice's last piece one step from the goal, in home stretch.
    last = game.players[0].pieces[3]
    last.state = PieceState.IN_HOME_STRETCH
    last.home_stretch_position = 6
    force_dice(game, 1, 2)
    engine.apply_move(game, Move(3, 1, MoveAction.REACH_GOAL))
    assert game.phase is GamePhase.FINISHED
    assert game.winner == 0
```

- [ ] **Step 2: Fail**

- [ ] **Step 3: Implementar `crown_piece` y detección de victoria**

```python
def crown_piece(game: Game, piece_index: int) -> None:
    if game.phase is not GamePhase.CROWNING:
        raise WrongPhase("not in CROWNING phase")
    if not 0 <= piece_index < 4:
        raise ValueError(f"piece_index out of range: {piece_index}")
    player = _current_player(game)
    piece = player.pieces[piece_index]
    if piece.state is PieceState.CROWNED:
        raise ValueError(f"piece {piece_index} already crowned")

    piece.state = PieceState.CROWNED
    piece.circuit_position = None
    piece.home_stretch_position = None

    if _check_winner(game):
        return
    game.consecutive_pairs = 0
    game.phase = GamePhase.ROLLING


def _check_winner(game: Game) -> bool:
    player = _current_player(game)
    if all(p.state is PieceState.CROWNED for p in player.pieces):
        game.winner = game.turn_order[game.current_turn_index]
        game.phase = GamePhase.FINISHED
        game.pending_dice = []  # cosmetic: don't leave leftover dice on a finished game
        return True
    return False
```

Y hacer que `apply_move` llame a `_check_winner` **antes** de la transición de turno — específicamente, después de cualquier mutación. Reemplazar `_finish_move_turn_transition` por:
```python
def _finish_move_turn_transition(game: Game) -> None:
    if _check_winner(game):
        return
    if game.pending_dice:
        return
    was_pair = game.consecutive_pairs > 0
    if was_pair and game.consecutive_pairs < 3:
        game.phase = GamePhase.ROLLING
    else:
        _advance_turn(game)
```

- [ ] **Step 4: Pass**

- [ ] **Step 5: Commit**

```bash
git add parques/engine.py tests/test_engine_turns.py
git commit -m "feat: crown_piece and win detection"
```

---

## Task 21: Engine — refactor final y limpieza

**Files:**
- Modify: `parques/engine.py`
- Modify: `parques/__init__.py`

- [ ] **Step 1: Re-exportar la API pública desde el paquete**

`parques/__init__.py`:
```python
"""Parqués core domain package — pure Python, no I/O."""
from parques.engine import (
    new_game,
    roll_initial,
    roll_dice,
    available_moves,
    apply_move,
    skip_turn,
    crown_piece,
)
from parques.entities import (
    Color,
    PieceState,
    GamePhase,
    MoveAction,
    Piece,
    Player,
    Move,
    MoveResult,
    Game,
)
from parques.exceptions import (
    DomainError,
    WrongPhase,
    InvalidMove,
    DuplicatePlayer,
)

__all__ = [
    # engine
    "new_game", "roll_initial", "roll_dice", "available_moves",
    "apply_move", "skip_turn", "crown_piece",
    # entities
    "Color", "PieceState", "GamePhase", "MoveAction",
    "Piece", "Player", "Move", "MoveResult", "Game",
    # exceptions
    "DomainError", "WrongPhase", "InvalidMove", "DuplicatePlayer",
]
```

- [ ] **Step 2: Verificar imports públicos**

Test rápido manual:
```bash
.venv/bin/python -c "import parques; print(parques.new_game([('A', parques.Color.RED), ('B', parques.Color.BLUE)]))"
```
Expected: imprime un `Game` en fase SETUP.

- [ ] **Step 3: Correr toda la suite**

Run: `.venv/bin/pytest -v`
Expected: todos los tests pasan.

- [ ] **Step 4: Commit**

```bash
git add parques/__init__.py
git commit -m "chore: re-export public API from parques package"
```

---

## Task 22: Test de integración — partida completa con dados scripted

**Files:**
- Create: `tests/test_full_game.py`

**Objetivo:** simular una partida de 2 jugadores hasta el final usando `ScriptedRandom`, y verificar que el resultado sea consistente (hay un ganador, todas sus fichas `CROWNED`, el perdedor no tiene las 4).

Dado que escribir una secuencia de dados que realmente lleve a la victoria es tedioso, el test va a **acelerar** colocando manualmente a Alice a 1 paso de la meta en sus 4 fichas, y luego simular solo los últimos movimientos.

- [ ] **Step 1: Tests**

`tests/test_full_game.py`:
```python
"""End-to-end smoke: a mini-game driven by scripted dice."""
from parques import engine
from parques.entities import (
    Color, GamePhase, PieceState, Move, MoveAction,
)
from tests.conftest import ScriptedRandom


def test_alice_wins_when_she_crowns_last_piece():
    rng = ScriptedRandom([
        6, 5, 3, 4,    # initial rolls → Alice first
        1, 2,          # Alice's only needed roll
    ])
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=rng,
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)

    # Stage: 3 of Alice's pieces already crowned; 1 piece at HS position 6.
    for i in range(3):
        game.players[0].pieces[i].state = PieceState.CROWNED
    last = game.players[0].pieces[3]
    last.state = PieceState.IN_HOME_STRETCH
    last.home_stretch_position = 6

    engine.roll_dice(game)   # (1, 2)
    assert game.pending_dice == [1, 2]

    moves = engine.available_moves(game)
    goal_moves = [m for m in moves if m.action is MoveAction.REACH_GOAL]
    assert goal_moves, "Alice should be able to reach goal with die 1"
    engine.apply_move(game, goal_moves[0])

    assert game.phase is GamePhase.FINISHED
    assert game.winner == 0
    assert all(p.state is PieceState.CROWNED for p in game.players[0].pieces)
    assert any(p.state is PieceState.IN_JAIL for p in game.players[1].pieces)


def test_bob_also_can_win_in_parallel_script():
    # Mirror test with Bob as winner, to prove the engine isn't hard-wired to Alice.
    rng = ScriptedRandom([3, 4, 6, 5, 1, 2])  # Bob=11, Alice=7 → Bob first
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=rng,
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)

    for i in range(3):
        game.players[1].pieces[i].state = PieceState.CROWNED
    last = game.players[1].pieces[3]
    last.state = PieceState.IN_HOME_STRETCH
    last.home_stretch_position = 6

    engine.roll_dice(game)
    moves = engine.available_moves(game)
    goal_moves = [m for m in moves if m.action is MoveAction.REACH_GOAL]
    engine.apply_move(game, goal_moves[0])

    assert game.phase is GamePhase.FINISHED
    assert game.winner == 1
```

- [ ] **Step 2: Correr y verificar**

Run: `.venv/bin/pytest tests/test_full_game.py -v`
Expected: `2 passed`.

- [ ] **Step 3: Correr la suite completa para sanity**

Run: `.venv/bin/pytest -v`
Expected: todos los tests pasan.

- [ ] **Step 4: Cobertura (opcional pero recomendado)**

Instalar pytest-cov:
```bash
.venv/bin/pip install pytest-cov
```

Correr:
```bash
.venv/bin/pytest --cov=parques --cov-report=term-missing
```

Expected: `engine.py` ≥95% cubierto. Si falta cobertura específica, añadir tests hasta llegar.

- [ ] **Step 5: Commit**

```bash
git add tests/test_full_game.py
git commit -m "test: end-to-end mini-game integration tests"
```

---

## Resumen de tareas

| # | Tarea | Archivos clave | TDD |
|---|---|---|---|
| 1 | Scaffold | `pyproject.toml`, `tests/test_smoke.py` | ✔ |
| 2 | Entities | `parques/entities.py` | ✔ |
| 3 | Exceptions | `parques/exceptions.py` | ✔ |
| 4 | Board | `parques/board.py` | ✔ |
| 5 | Conftest | `tests/conftest.py` | — |
| 6 | `new_game` | `parques/engine.py` | ✔ |
| 7 | `roll_initial` | `parques/engine.py` | ✔ |
| 8 | `roll_dice` base | `parques/engine.py` | ✔ |
| 9 | `roll_dice` 3 oportunidades | `parques/engine.py` | ✔ |
| 10 | `roll_dice` triple par | `parques/engine.py` | ✔ |
| 11 | `available_moves` ADVANCE | `parques/engine.py` | ✔ |
| 12 | `available_moves` EXIT_JAIL | `parques/engine.py` | ✔ |
| 13 | `available_moves` CAPTURE | `parques/engine.py` | ✔ |
| 14 | `available_moves` home stretch | `parques/engine.py` | ✔ |
| 15 | `apply_move` ADVANCE | `parques/engine.py` | ✔ |
| 16 | `apply_move` EXIT_JAIL | `parques/engine.py` | ✔ |
| 17 | `apply_move` CAPTURE | `parques/engine.py` | ✔ |
| 18 | `apply_move` home stretch | `parques/engine.py` | ✔ |
| 19 | `skip_turn` | `parques/engine.py` | ✔ |
| 20 | `crown_piece` + victoria | `parques/engine.py` | ✔ |
| 21 | Re-exports `__init__` | `parques/__init__.py` | — |
| 22 | Full-game integration | `tests/test_full_game.py` | ✔ |

**Frecuencia de commits:** uno por tarea (22 commits al final). Mensaje convencional: `feat:` para nueva funcionalidad, `test:` solo-tests, `chore:` scaffold/refactor.

**Criterio de "módulo #1 terminado":**
- Todos los tests pasan (`pytest`).
- Cobertura ≥ 95% en `parques/engine.py` y ≥ 90% global.
- La API pública se puede usar desde `import parques` sin conocer la estructura interna.

Al cerrar el módulo #1, se abre nuevo brainstorming para el módulo #2 (partida local multijugador en terminal).
