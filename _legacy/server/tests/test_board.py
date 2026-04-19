import pytest
from server.game.board import Board, Piece
from server.game.constants import EXIT_POSITIONS, SAFE_POSITIONS

def test_initial_state():
    board = Board(["red", "blue"])
    for color in ["red", "blue"]:
        for piece in board.pieces[color]:
            assert piece.state == "jail"
            assert piece.position == -1

def test_exit_from_jail():
    board = Board(["red"])
    board.exit_from_jail("red", 0)
    piece = board.get_piece("red", 0)
    assert piece.state == "board"
    assert piece.position == EXIT_POSITIONS["red"]

def test_move_piece():
    board = Board(["red"])
    board.exit_from_jail("red", 0)
    result = board.move_piece("red", 0, 5)
    piece = board.get_piece("red", 0)
    assert piece.state == "board"
    assert piece.position == 5
    assert result["action"] == "move"

def test_capture():
    board = Board(["red", "blue"])
    board.exit_from_jail("red", 0)
    board.exit_from_jail("blue", 0)
    result = board.move_piece("red", 0, 17)
    assert result["action"] == "eat"
    blue_piece = board.get_piece("blue", 0)
    assert blue_piece.state == "jail"

def test_no_capture_on_safe():
    board = Board(["red", "blue"])
    board.exit_from_jail("red", 0)
    board.exit_from_jail("blue", 0)
    board.move_piece("blue", 0, 5)  # 17 + 5 = 22 (safe)
    result = board.move_piece("red", 0, 22)
    assert result["action"] == "move"
    blue_piece = board.get_piece("blue", 0)
    assert blue_piece.state == "board"

def test_all_finished():
    board = Board(["red"])
    for piece in board.pieces["red"]:
        piece.state = "finished"
    assert board.all_finished("red") is True

def test_to_dict():
    board = Board(["red"])
    d = board.to_dict()
    assert "red" in d
    assert len(d["red"]) == 4
