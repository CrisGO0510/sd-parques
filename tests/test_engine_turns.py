import pytest

from core import engine
from core.entities import Color, GamePhase, Move, MoveAction, PieceState
from core.exceptions import DuplicatePlayer, WrongPhase
from tests.conftest import force_dice


def test_new_game_sets_setup_phase_and_four_pieces_in_jail():
    game = engine.new_game([("Alice", Color.RED), ("Bob", Color.BLUE)])
    assert game.phase is GamePhase.SETUP
    assert len(game.players) == 2
    for player in game.players:
        assert all(p.state is PieceState.IN_JAIL for p in player.pieces)


def test_new_game_rejects_fewer_than_two_players():
    with pytest.raises(ValueError):
        engine.new_game([("Solo", Color.RED)])


def test_new_game_rejects_more_than_four_players():
    players = [
        ("A", Color.RED), ("B", Color.BLUE),
        ("C", Color.GREEN), ("D", Color.YELLOW),
        ("E", Color.RED),
    ]
    with pytest.raises(ValueError):
        engine.new_game(players)


def test_new_game_rejects_duplicate_names():
    with pytest.raises(DuplicatePlayer, match="name"):
        engine.new_game([("Alice", Color.RED), ("Alice", Color.BLUE)])


def test_new_game_rejects_duplicate_colors():
    with pytest.raises(DuplicatePlayer, match="color"):
        engine.new_game([("Alice", Color.RED), ("Bob", Color.RED)])


def test_roll_initial_collects_rolls_and_transitions_to_rolling(scripted_rng):
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([3, 4, 6, 5]),  # Alice=7, Bob=11 → Bob first
    )
    assert engine.roll_initial(game, 0) == 7
    assert game.phase is GamePhase.SETUP
    assert engine.roll_initial(game, 1) == 11
    assert game.phase is GamePhase.ROLLING
    assert game.turn_order == [1, 0]  # Bob (index 1) first
    assert game.current_turn_index == 0


def test_roll_initial_rejects_out_of_phase(scripted_rng):
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([3, 4, 6, 5]),
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)  # now in ROLLING
    with pytest.raises(WrongPhase):
        engine.roll_initial(game, 0)


def test_roll_initial_rejects_second_roll_by_same_player(scripted_rng):
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([3, 4, 6, 5]),
    )
    engine.roll_initial(game, 0)
    with pytest.raises(ValueError):
        engine.roll_initial(game, 0)


def test_roll_initial_rejects_invalid_player_index(scripted_rng):
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([]),
    )
    with pytest.raises(ValueError):
        engine.roll_initial(game, 9)


def test_roll_dice_fills_pending_dice_and_moves_to_moving(scripted_rng):
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([6, 5, 3, 4, 2, 3]),
    )
    engine.roll_initial(game, 0)   # Alice=11
    engine.roll_initial(game, 1)   # Bob=7 → Alice first
    # Alice has pieces out of jail? No, still all in jail.
    # But first roll sets initial_rolls_remaining=3.
    d1, d2 = engine.roll_dice(game)
    assert (d1, d2) == (2, 3)
    assert game.pending_dice == [2, 3]
    # Not a pair and all pieces in jail → counts against the 3 opportunities.
    # (full behaviour tested in Task 9)


def test_roll_dice_rejects_wrong_phase(two_player_game):
    with pytest.raises(WrongPhase):
        engine.roll_dice(two_player_game)


def test_all_in_jail_initializes_three_opportunities(scripted_rng):
    # Alice wins first turn. All pieces in jail. First roll non-pair (2,3).
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([6, 5, 3, 4,  # initial rolls: Alice=11, Bob=7
                          2, 3]),      # Alice's first actual roll
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)
    engine.roll_dice(game)
    assert game.initial_rolls_remaining == 2  # started at 3, consumed 1


def test_three_non_pair_rolls_pass_turn(scripted_rng):
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([6, 5, 3, 4,  # initial rolls
                          2, 3, 1, 4, 5, 6,  # Alice's 3 non-pairs
                          1, 2]),            # Bob's first roll
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)

    # Alice's 1st non-pair
    engine.roll_dice(game)
    game.pending_dice = []                    # pretend she had no move → skipped
    game.phase = GamePhase.ROLLING             # manual transition for this unit test
    assert game.current_turn_index == 0       # still Alice

    # 2nd non-pair
    engine.roll_dice(game)
    game.pending_dice = []
    game.phase = GamePhase.ROLLING

    # 3rd non-pair → turn passes
    engine.roll_dice(game)
    assert game.current_turn_index == 1       # now Bob
    assert game.phase is GamePhase.ROLLING
    assert game.initial_rolls_remaining == 0
    # Bob rolls
    engine.roll_dice(game)
    # Bob also has all pieces in jail → starts his own 3 opportunities
    assert game.initial_rolls_remaining == 2


def test_pair_clears_three_opportunity_counter(scripted_rng):
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([6, 5, 3, 4, 4, 4]),  # Alice first, rolls pair 4-4
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)
    engine.roll_dice(game)
    assert game.initial_rolls_remaining == 0    # never entered counter mode
    assert game.pending_dice == [4, 4]
    assert game.consecutive_pairs == 1


def test_third_consecutive_pair_triggers_crowning(scripted_rng):
    # Alice wins first turn. Rolls 3-3 (pair), 5-5 (pair), 6-6 (pair).
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([6, 5, 3, 4,  # initial rolls
                          3, 3, 5, 5, 6, 6]),
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)

    engine.roll_dice(game)     # 3-3 → MOVING, pairs=1
    assert game.phase is GamePhase.MOVING
    assert game.consecutive_pairs == 1
    # Pretend Alice moved and emptied pending_dice; she re-rolls.
    game.pending_dice = []
    game.phase = GamePhase.ROLLING

    engine.roll_dice(game)     # 5-5 → MOVING, pairs=2
    assert game.consecutive_pairs == 2
    game.pending_dice = []
    game.phase = GamePhase.ROLLING

    engine.roll_dice(game)     # 6-6 → CROWNING (no MOVING)
    assert game.phase is GamePhase.CROWNING
    assert game.consecutive_pairs == 3
    assert game.pending_dice == []  # not filled


def test_skip_turn_discards_dice_and_passes_to_next_player(scripted_rng):
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([6, 5, 3, 4]),
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)
    force_dice(game, 3, 5)
    engine.skip_turn(game)
    assert game.pending_dice == []
    assert game.phase is GamePhase.ROLLING
    assert game.current_turn_index == 1


def test_skip_turn_rejects_empty_dice(scripted_rng):
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([6, 5, 3, 4]),
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)
    game.phase = GamePhase.MOVING
    game.pending_dice = []
    with pytest.raises(ValueError):
        engine.skip_turn(game)


def test_skip_turn_rejects_wrong_phase(two_player_game):
    with pytest.raises(engine.WrongPhase):
        engine.skip_turn(two_player_game)


def test_crown_piece_moves_selected_piece_to_crowned(scripted_rng):
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([6, 5, 3, 4]),
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)
    game.phase = GamePhase.CROWNING
    engine.crown_piece(game, piece_index=1)
    assert game.players[0].pieces[1].state is PieceState.CROWNED
    assert game.phase is GamePhase.ROLLING   # same player continues
    assert game.consecutive_pairs == 0        # reset after crowning
    assert game.current_turn_index == 0


def test_crown_piece_rejects_already_crowned(scripted_rng):
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([6, 5, 3, 4]),
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)
    game.players[0].pieces[0].state = PieceState.CROWNED
    game.phase = GamePhase.CROWNING
    with pytest.raises(ValueError):
        engine.crown_piece(game, 0)


def test_crown_piece_rejects_invalid_index(scripted_rng):
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([6, 5, 3, 4]),
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)
    game.phase = GamePhase.CROWNING
    with pytest.raises(ValueError):
        engine.crown_piece(game, 42)


def test_fourth_crowned_piece_finishes_game(scripted_rng):
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=scripted_rng([6, 5, 3, 4]),
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)
    # Put Alice's first 3 pieces already crowned.
    for i in range(3):
        game.players[0].pieces[i].state = PieceState.CROWNED
    # Alice's last piece one step from the goal, in home stretch.
    last = game.players[0].pieces[3]
    last.state = PieceState.IN_HOME_STRETCH
    last.home_stretch_position = 6
    force_dice(game, 1, 2)
    engine.apply_move(game, Move(3, 1, MoveAction.REACH_GOAL))
    assert game.phase is GamePhase.FINISHED
    assert game.winner == 0
