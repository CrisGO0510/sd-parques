"""Game engine: pure-function rules operating on a mutable Game."""
from __future__ import annotations

import random

from core.board import (
    BOARD_SIZE, EXITS, HOME_STRETCH_ENTRY, HOME_STRETCH_SIZE,
    is_safe, next_position,
)
from core.entities import (
    Color, Game, GamePhase, Move, MoveAction, MoveResult, Piece, Player, PieceState,
)
# Re-export domain exceptions as engine.X for ergonomic use in tests/clients.
from core.exceptions import (  # noqa: F401
    DomainError, DuplicatePlayer, InvalidMove, WrongPhase,
)


def new_game(
    players: list[tuple[str, Color]],
    *,
    rng: random.Random | None = None,
) -> Game:
    """Create a new game in SETUP phase."""
    if not 2 <= len(players) <= 4:
        raise ValueError("core requires between 2 and 4 players")

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


def skip_turn(game: Game) -> None:
    """MOVING phase: current player skips their turn (no valid moves for pending dice).

    Discards pending dice and passes to the next player.
    """
    if game.phase is not GamePhase.MOVING:
        raise WrongPhase("not in MOVING phase")
    if not game.pending_dice:
        raise ValueError("no pending dice to skip")
    game.pending_dice = []
    _advance_turn(game)


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


def available_moves(game: Game) -> list[Move]:
    """Return every legal Move the current player can make."""
    if game.phase is not GamePhase.MOVING:
        return []

    player = _current_player(game)
    moves: list[Move] = []

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

    # Build a map of enemy-piece positions for capture detection.
    enemy_positions: dict[int, Player] = {}
    for other in game.players:
        if other is player:
            continue
        for p in other.pieces:
            if p.state is PieceState.ON_BOARD and p.circuit_position is not None:
                enemy_positions[p.circuit_position] = other

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

    moves.sort(key=lambda m: (m.piece_index, m.dice_value))
    return moves


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
    elif move.action is MoveAction.EXIT_JAIL:
        piece.state = PieceState.ON_BOARD
        piece.circuit_position = EXITS[player.color]
        # EXIT_JAIL consumes BOTH dice of the pair.
        game.pending_dice = []
        _finish_move_turn_transition(game)
        return MoveResult(action=MoveAction.EXIT_JAIL)
    elif move.action is MoveAction.CAPTURE and piece.state is PieceState.ON_BOARD:
        target = next_position(piece.circuit_position, move.dice_value)
        captured = _capture_at(game, target, player)
        piece.circuit_position = target
        _consume_die(game, move.dice_value)
        _finish_move_turn_transition(game)
        return MoveResult(action=MoveAction.CAPTURE, captured=captured)
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
    else:
        raise NotImplementedError(
            f"Task 15 only handles ADVANCE on circuit; got {move.action}"
        )

    _consume_die(game, move.dice_value)
    _finish_move_turn_transition(game)
    return result


def _consume_die(game: Game, die: int) -> None:
    game.pending_dice.remove(die)


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
        game.pending_dice = []
        return True
    return False


def _finish_move_turn_transition(game: Game) -> None:
    if _check_winner(game):
        return
    if game.pending_dice:
        return  # still MOVING; same player picks next
    # Dice exhausted.
    was_pair = game.consecutive_pairs > 0
    if was_pair and game.consecutive_pairs < 3:
        game.phase = GamePhase.ROLLING   # same player re-rolls
    else:
        _advance_turn(game)


def _crossed_home_entry(start: int, steps: int, entry: int) -> bool:
    """True if moving `steps` from `start` passes through or lands beyond `entry`."""
    distance = (entry - start) % BOARD_SIZE
    return distance < steps


def _home_stretch_overflow(start: int, steps: int, entry: int) -> int:
    """How many cells into the home stretch (0-indexed) the piece lands."""
    distance = (entry - start) % BOARD_SIZE
    return steps - distance - 1


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
