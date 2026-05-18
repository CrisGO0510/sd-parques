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


def piece_progress(game: Game, player_index: int, piece_index: int) -> int:
    """Score: higher = closer to the goal.

    - IN_HOME_STRETCH: 1000 + home_stretch_position
    - ON_BOARD:        circuit_position
    - Otherwise:       0
    """
    player = game.players[player_index]
    piece = player.pieces[piece_index]
    if piece.state is PieceState.IN_HOME_STRETCH:
        return 1000 + (piece.home_stretch_position or 0)
    if piece.state is PieceState.ON_BOARD:
        return piece.circuit_position or 0
    return 0


def most_advanced_piece_index(game: Game, player_index: int) -> int:
    """Index of the non-crowned piece with the highest progress.
    Ties are broken by lowest index. Raises ValueError if every piece is CROWNED."""
    player = game.players[player_index]
    best_idx: int | None = None
    best_score = -1
    for i, piece in enumerate(player.pieces):
        if piece.state is PieceState.CROWNED:
            continue
        score = piece_progress(game, player_index, i)
        if score > best_score:
            best_score = score
            best_idx = i
    if best_idx is None:
        raise ValueError("all pieces already crowned")
    return best_idx


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
        if m.action is MoveAction.ADVANCE:
            player_idx = _current_player_index(game)
            if player_idx is None:
                progress = 0
            else:
                progress = -piece_progress(game, player_idx, m.piece_index)
        else:
            progress = 0
        return (priority, progress)

    return min(moves, key=sort_key)
