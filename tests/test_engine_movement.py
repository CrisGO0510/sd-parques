import pytest

from core import engine
from core.board import EXITS
from core.entities import (
    Color, GamePhase, Move, MoveAction, MoveResult, PieceState,
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
    # One piece on board + 2 distinct dice → 3 ADVANCE moves: d=3, d=4,
    # and d=7 (use both dice as a single sum move).
    assert sorted((m.piece_index, m.dice_value, m.action) for m in moves) == [
        (0, 3, MoveAction.ADVANCE),
        (0, 4, MoveAction.ADVANCE),
        (0, 7, MoveAction.ADVANCE),
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


def test_available_moves_includes_single_exit_jail_on_pair(scripted_rng):
    # With a pair rolled and any jailed piece, available_moves should emit
    # exactly ONE EXIT_JAIL move — applying it frees all jailed pieces at
    # once, so multiple per-piece moves would be redundant.
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([6, 5, 3, 4]),
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)
    force_dice(game, 4, 4)
    game.consecutive_pairs = 1
    moves = engine.available_moves(game)
    exit_moves = [m for m in moves if m.action is MoveAction.EXIT_JAIL]
    assert len(exit_moves) == 1


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


def test_apply_move_exit_jail_releases_all_jailed_pieces(scripted_rng):
    # All 4 pieces in jail + pair → EXIT_JAIL frees all of them at once.
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
    for piece in game.players[0].pieces:
        assert piece.state is PieceState.ON_BOARD
        assert piece.circuit_position == EXITS[Color.RED]
    assert game.pending_dice == []   # both dice consumed by the pair
    assert game.phase is GamePhase.ROLLING  # re-roll (pair)


def test_apply_move_exit_jail_releases_only_jailed_pieces(scripted_rng):
    # Some pieces already on board — EXIT_JAIL frees the rest but leaves
    # on-board pieces untouched.
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([6, 5, 3, 4]),
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)
    # Place Alice's piece 0 on the board at position 20 (not an exit).
    alice = game.players[0]
    alice.pieces[0].state = PieceState.ON_BOARD
    alice.pieces[0].circuit_position = 20
    force_dice(game, 3, 3)
    game.consecutive_pairs = 1

    move = Move(piece_index=1, dice_value=6, action=MoveAction.EXIT_JAIL)
    engine.apply_move(game, move)
    # Piece 0 stays where it was.
    assert alice.pieces[0].state is PieceState.ON_BOARD
    assert alice.pieces[0].circuit_position == 20
    # Pieces 1, 2, 3 now on board at Red's exit.
    for piece in alice.pieces[1:]:
        assert piece.state is PieceState.ON_BOARD
        assert piece.circuit_position == EXITS[Color.RED]
