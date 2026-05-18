"""Tests para piece_progress y most_advanced_piece_index."""
from __future__ import annotations

import random

import pytest

from core import engine
from core.entities import Color, GamePhase, PieceState
from server.recommender import most_advanced_piece_index, piece_progress


def _setup_two_player_game():
    game = engine.new_game(
        [("A", Color.RED), ("B", Color.BLUE)],
        rng=random.Random(42),
    )
    game.initial_rolls = {0: 12, 1: 6}
    game.turn_order = [0, 1]
    game.current_turn_index = 0
    game.phase = GamePhase.ROLLING
    return game


def test_piece_progress_uses_circuit_position_for_on_board():
    game = _setup_two_player_game()
    player = game.players[0]
    player.pieces[0].state = PieceState.ON_BOARD
    player.pieces[0].circuit_position = 15
    assert piece_progress(game, player_index=0, piece_index=0) == 15


def test_piece_progress_boosts_home_stretch():
    game = _setup_two_player_game()
    player = game.players[0]
    player.pieces[0].state = PieceState.IN_HOME_STRETCH
    player.pieces[0].home_stretch_position = 3
    assert piece_progress(game, player_index=0, piece_index=0) >= 1000


def test_piece_progress_jail_is_zero():
    game = _setup_two_player_game()
    assert piece_progress(game, player_index=0, piece_index=0) == 0


def test_most_advanced_piece_index_picks_highest_progress():
    game = _setup_two_player_game()
    player = game.players[0]
    player.pieces[0].state = PieceState.ON_BOARD
    player.pieces[0].circuit_position = 5
    player.pieces[1].state = PieceState.ON_BOARD
    player.pieces[1].circuit_position = 20
    player.pieces[2].state = PieceState.IN_HOME_STRETCH
    player.pieces[2].home_stretch_position = 1
    assert most_advanced_piece_index(game, player_index=0) == 2


def test_most_advanced_piece_index_skips_crowned():
    game = _setup_two_player_game()
    player = game.players[0]
    player.pieces[0].state = PieceState.CROWNED
    player.pieces[1].state = PieceState.ON_BOARD
    player.pieces[1].circuit_position = 5
    assert most_advanced_piece_index(game, player_index=0) == 1


def test_most_advanced_piece_index_tie_breaks_by_lowest_index():
    game = _setup_two_player_game()
    player = game.players[0]
    player.pieces[0].state = PieceState.ON_BOARD
    player.pieces[0].circuit_position = 5
    player.pieces[1].state = PieceState.ON_BOARD
    player.pieces[1].circuit_position = 5
    assert most_advanced_piece_index(game, player_index=0) == 0


def test_most_advanced_piece_index_raises_when_all_crowned():
    game = _setup_two_player_game()
    for p in game.players[0].pieces:
        p.state = PieceState.CROWNED
    with pytest.raises(ValueError):
        most_advanced_piece_index(game, player_index=0)
