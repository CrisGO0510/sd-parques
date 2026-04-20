"""Game engine: pure-function rules operating on a mutable Game."""
from __future__ import annotations

import random

from parques.entities import (
    Color, Game, GamePhase, Player, PieceState,
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


def roll_dice(game: Game) -> tuple[int, int]:
    """ROLLING phase: current player rolls both dice."""
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
        if game.consecutive_pairs >= 3:
            # Triple pair: skip movement, go to CROWNING.
            game.pending_dice = []
            game.phase = GamePhase.CROWNING
            return d1, d2
    else:
        game.consecutive_pairs = 0

    game.pending_dice = [d1, d2]
    game.phase = GamePhase.MOVING
    return d1, d2


def _advance_turn(game: Game) -> None:
    """Move to next player; reset per-turn counters."""
    game.consecutive_pairs = 0
    game.initial_rolls_remaining = 0
    game.current_turn_index = (game.current_turn_index + 1) % len(game.turn_order)
    game.phase = GamePhase.ROLLING


def _current_player(game: Game) -> Player:
    return game.players[game.turn_order[game.current_turn_index]]


def _all_in_jail(player: Player) -> bool:
    return all(p.state is PieceState.IN_JAIL for p in player.pieces)
