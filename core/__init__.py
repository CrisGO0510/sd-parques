"""Parqués core domain package — pure Python, no I/O."""
from core.engine import (
    new_game,
    roll_initial,
    roll_dice,
    available_moves,
    apply_move,
    skip_turn,
    crown_piece,
)
from core.entities import (
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
from core.exceptions import (
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
