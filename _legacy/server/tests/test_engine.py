from server.game.engine import GameEngine

def test_roll_dice():
    engine = GameEngine(1, ["red", "blue"])
    engine.phase_initial = False
    d1, d2 = engine.roll_dice()
    assert 1 <= d1 <= 6
    assert 1 <= d2 <= 6
    assert engine.phase == "moving"

def test_turn_advances():
    engine = GameEngine(1, ["red", "blue"])
    engine.phase_initial = False
    engine.roll_dice()
    engine.dice = (1, 2)  # non-pair
    engine.board.exit_from_jail("red", 0)
    result = engine.execute_move("red", 0)
    assert engine.current_color == "blue"

def test_pairs_keep_turn():
    engine = GameEngine(1, ["red", "blue"])
    engine.phase_initial = False
    engine.roll_dice()
    engine.dice = (3, 3)  # pair
    # Exit from jail with pair
    result = engine.execute_move("red", 0)
    assert engine.current_color == "red"

def test_wrong_turn_rejected():
    engine = GameEngine(1, ["red", "blue"])
    engine.phase_initial = False
    engine.roll_dice()
    result = engine.execute_move("blue", 0)
    assert "error" in result

def test_get_state():
    engine = GameEngine(1, ["red", "blue"])
    engine.phase_initial = False
    state = engine.get_state()
    assert state["game_id"] == 1
    assert "board" in state
    assert state["current_turn"] == "red"

def test_initial_roll():
    engine = GameEngine(1, ["red", "blue"])
    assert engine.phase_initial is True
    engine.roll_initial("red")
    assert engine.phase_initial is True  # still waiting for blue
    engine.roll_initial("blue")
    assert engine.phase_initial is False  # both rolled, order determined
