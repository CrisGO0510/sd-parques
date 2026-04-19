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
