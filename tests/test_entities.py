from core.entities import (
    Color, PieceState, GamePhase, MoveAction,
    Piece, Player, Move, MoveResult, Game,
)


def test_color_enum_has_four_values():
    assert set(Color) == {Color.RED, Color.BLUE, Color.GREEN, Color.YELLOW}


def test_piece_defaults_to_jail_with_no_position():
    piece = Piece(index=0)
    assert piece.state is PieceState.IN_JAIL
    assert piece.circuit_position is None
    assert piece.home_stretch_position is None


def test_player_gets_four_pieces_by_default():
    player = Player(name="Alice", color=Color.RED)
    assert len(player.pieces) == 4
    assert [p.index for p in player.pieces] == [0, 1, 2, 3]
    assert all(p.state is PieceState.IN_JAIL for p in player.pieces)


def test_game_defaults_to_setup_phase():
    alice = Player(name="Alice", color=Color.RED)
    bob = Player(name="Bob", color=Color.BLUE)
    game = Game(players=[alice, bob])
    assert game.phase is GamePhase.SETUP
    assert game.pending_dice == []
    assert game.turn_order == []
    assert game.consecutive_pairs == 0
    assert game.winner is None


def test_move_and_moveresult_construct():
    move = Move(piece_index=0, dice_value=5, action=MoveAction.ADVANCE)
    assert move.action is MoveAction.ADVANCE
    result = MoveResult(action=MoveAction.CAPTURE)
    assert result.captured is None
    assert result.reached_goal is False
