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
