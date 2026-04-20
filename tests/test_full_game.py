"""End-to-end smoke: a mini-game driven by scripted dice."""
from parques import engine
from parques.entities import (
    Color, GamePhase, PieceState, Move, MoveAction,
)
from tests.conftest import ScriptedRandom


def test_alice_wins_when_she_crowns_last_piece():
    rng = ScriptedRandom([
        6, 5, 3, 4,    # initial rolls → Alice first
        1, 2,          # Alice's only needed roll
    ])
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=rng,
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)

    # Stage: 3 of Alice's pieces already crowned; 1 piece at HS position 6.
    for i in range(3):
        game.players[0].pieces[i].state = PieceState.CROWNED
    last = game.players[0].pieces[3]
    last.state = PieceState.IN_HOME_STRETCH
    last.home_stretch_position = 6

    engine.roll_dice(game)   # (1, 2)
    assert game.pending_dice == [1, 2]

    moves = engine.available_moves(game)
    goal_moves = [m for m in moves if m.action is MoveAction.REACH_GOAL]
    assert goal_moves, "Alice should be able to reach goal with die 1"
    engine.apply_move(game, goal_moves[0])

    assert game.phase is GamePhase.FINISHED
    assert game.winner == 0
    assert all(p.state is PieceState.CROWNED for p in game.players[0].pieces)
    assert any(p.state is PieceState.IN_JAIL for p in game.players[1].pieces)


def test_bob_also_can_win_in_parallel_script():
    # Mirror test with Bob as winner, to prove the engine isn't hard-wired to Alice.
    rng = ScriptedRandom([3, 4, 6, 5, 1, 2])  # Bob=11, Alice=7 → Bob first
    game = engine.new_game(
        [("Alice", Color.RED), ("Bob", Color.BLUE)],
        rng=rng,
    )
    engine.roll_initial(game, 0)
    engine.roll_initial(game, 1)

    for i in range(3):
        game.players[1].pieces[i].state = PieceState.CROWNED
    last = game.players[1].pieces[3]
    last.state = PieceState.IN_HOME_STRETCH
    last.home_stretch_position = 6

    engine.roll_dice(game)
    moves = engine.available_moves(game)
    goal_moves = [m for m in moves if m.action is MoveAction.REACH_GOAL]
    engine.apply_move(game, goal_moves[0])

    assert game.phase is GamePhase.FINISHED
    assert game.winner == 1
