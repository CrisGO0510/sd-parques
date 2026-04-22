import pytest
from core import engine
from core.board import HOME_STRETCH_ENTRY, HOME_STRETCH_SIZE
from core.entities import Color, Move, MoveAction, PieceState
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
    red_entry = HOME_STRETCH_ENTRY[Color.RED]  # 86
    piece = game.players[0].pieces[0]
    piece.state = PieceState.ON_BOARD
    piece.circuit_position = red_entry - 2  # 84

    force_dice(game, 3, 5)
    moves = engine.available_moves(game)
    # With 3 dice → target is entry+1, which is past entry → ENTER_HOME_STRETCH.
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


def test_apply_enter_home_stretch_sets_state_and_position(scripted_rng):
    game = _game_setup(scripted_rng)
    piece = game.players[0].pieces[0]
    piece.state = PieceState.ON_BOARD
    piece.circuit_position = HOME_STRETCH_ENTRY[Color.RED] - 2  # 84
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
