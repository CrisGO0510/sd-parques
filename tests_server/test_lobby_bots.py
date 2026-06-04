"""Pruebas de Lobby con los 2 bots fijos (Camila=GREEN, Bryan=YELLOW)."""
from __future__ import annotations

import pytest

from core.entities import Color
from core.exceptions import DuplicatePlayer
from server.lobby import (
    BOT_CONN_PREFIX,
    FIXED_BOTS,
    MAX_HUMANS,
    Lobby,
    LobbyFull,
    is_bot_conn_id,
)


def test_is_bot_conn_id_detects_prefix():
    assert is_bot_conn_id("bot:green") is True
    assert is_bot_conn_id("c1") is False
    assert is_bot_conn_id("") is False


def test_fresh_lobby_has_two_fixed_bots():
    lobby = Lobby()
    bots = [p for p in lobby.players() if p.is_bot]
    assert len(bots) == 2
    by_color = {p.color: p for p in bots}
    assert by_color[Color.GREEN].username == "Camila"
    assert by_color[Color.YELLOW].username == "Bryan"


def test_fixed_bots_have_synthetic_conn_ids_and_are_not_host():
    lobby = Lobby()
    bots = {p.color: p for p in lobby.players() if p.is_bot}
    assert bots[Color.GREEN].conn_id == f"{BOT_CONN_PREFIX}green"
    assert bots[Color.YELLOW].conn_id == f"{BOT_CONN_PREFIX}yellow"
    assert all(not p.is_host for p in bots.values())


def test_fresh_lobby_has_no_humans_and_no_host():
    lobby = Lobby()
    assert [p for p in lobby.players() if not p.is_bot] == []
    assert lobby.host_conn_id() is None


def test_first_human_becomes_host():
    lobby = Lobby()
    human = lobby.join("c1", "Cris")
    assert human.is_host is True
    assert lobby.host_conn_id() == "c1"


def test_join_rejects_third_human():
    lobby = Lobby()
    lobby.join("c1", "Cris")
    lobby.join("c2", "Ana")
    with pytest.raises(LobbyFull):
        lobby.join("c3", "Eve")


def test_max_humans_is_two():
    assert MAX_HUMANS == 2


def test_available_colors_excludes_bot_colors():
    lobby = Lobby()
    available = lobby.available_colors()
    assert Color.GREEN not in available
    assert Color.YELLOW not in available
    assert set(available) == {Color.RED, Color.BLUE}


def test_human_cannot_take_a_bot_color():
    lobby = Lobby()
    lobby.join("c1", "Cris")
    with pytest.raises(DuplicatePlayer):
        lobby.select_color("c1", Color.GREEN)


def test_can_start_requires_at_least_one_human_with_color():
    lobby = Lobby()
    assert lobby.can_start() is False  # solo bots, sin humanos
    lobby.join("c1", "Cris")
    assert lobby.can_start() is False  # humano sin color
    lobby.select_color("c1", Color.RED)
    assert lobby.can_start() is True   # 1 humano con color + 2 bots


def test_fixed_bots_lists_camila_and_bryan():
    assert FIXED_BOTS == {Color.GREEN: "Camila", Color.YELLOW: "Bryan"}
