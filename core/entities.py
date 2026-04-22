"""Domain entities for the core game core."""
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
    # Every enemy piece that sat on the target cell at capture time (not
    # just one) — own-color pieces legitimately stack on non-safe cells
    # so a capture can evict several at once.
    captured: list[Piece] = field(default_factory=list)
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
