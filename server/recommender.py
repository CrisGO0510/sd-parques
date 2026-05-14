"""Recommender: suggests the best move given a list of available moves.

Uses a fixed priority heuristic.

Priority order (highest first):
  1. REACH_GOAL        — crown a piece immediately
  2. CAPTURE           — eat a rival's piece
  3. ENTER_HOME_STRETCH — step into the safe home column
  4. EXIT_JAIL         — release a jailed piece (only on pairs)
  5. ADVANCE           — move the piece that is furthest ahead
"""
from __future__ import annotations

from core.entities import Game, Move, MoveAction, PieceState


# Lower number = higher priority
_PRIORITY: dict[MoveAction, int] = {
    MoveAction.REACH_GOAL:          0,
    MoveAction.CAPTURE:             1,
    MoveAction.ENTER_HOME_STRETCH:  2,
    MoveAction.EXIT_JAIL:           3,
    MoveAction.ADVANCE:             4,
}


def _piece_progress(game: Game, move: Move) -> int:
    """Return a progress score for ADVANCE moves so we prefer
    the piece that is closest to the goal (higher = closer)."""
    player_idx = _current_player_index(game)
    if player_idx is None:
        return 0
    player = game.players[player_idx]
    piece = player.pieces[move.piece_index]
    if piece.state is PieceState.IN_HOME_STRETCH:
        # Already in the home stretch — very close, boost the score.
        return 1000 + (piece.home_stretch_position or 0)
    if piece.state is PieceState.ON_BOARD:
        return piece.circuit_position or 0
    return 0


def _current_player_index(game: Game) -> int | None:
    if not game.turn_order:
        return None
    return game.turn_order[game.current_turn_index]


def recommend(game: Game, moves: list[Move]) -> Move | None:
    """Return the single best move from *moves*, or None if the list is empty."""
    if not moves:
        return None

    def sort_key(m: Move) -> tuple[int, int]:
        priority = _PRIORITY.get(m.action, 99)
        # For advances: prefer the most advanced piece (negate for ascending sort).
        progress = -_piece_progress(game, m) if m.action is MoveAction.ADVANCE else 0
        return (priority, progress)

    return min(moves, key=sort_key)
