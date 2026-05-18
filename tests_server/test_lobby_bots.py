"""Pruebas de Lobby con bots."""
from __future__ import annotations

import pytest

from core.entities import Color
from server.lobby import (
    BOT_CONN_PREFIX,
    Lobby,
    LobbyError,
    LobbyFull,
    is_bot_conn_id,
)


def test_is_bot_conn_id_detects_prefix():
    assert is_bot_conn_id("bot:red") is True
    assert is_bot_conn_id("c1") is False
    assert is_bot_conn_id("") is False


def test_add_bot_assigns_synthetic_conn_id_and_username():
    lobby = Lobby()
    lobby.join("c1", "Cris")
    bot = lobby.add_bot(Color.BLUE)
    assert bot.conn_id == f"{BOT_CONN_PREFIX}blue"
    assert bot.username == "Bot Azul"
    assert bot.color is Color.BLUE
    assert bot.is_bot is True
    assert bot.is_host is False


def test_add_bot_translates_color_names_to_spanish():
    lobby = Lobby()
    lobby.join("c1", "Cris")
    assert lobby.add_bot(Color.RED).username == "Bot Rojo"
    assert lobby.add_bot(Color.GREEN).username == "Bot Verde"
    assert lobby.add_bot(Color.YELLOW).username == "Bot Amarillo"


def test_add_bot_fills_lobby_with_one_human_and_three_bots():
    """1 humano + 3 bots = sala llena; el cuarto bot lo rechaza LobbyFull."""
    lobby = Lobby()
    lobby.join("c1", "Cris")
    lobby.add_bot(Color.BLUE)
    lobby.add_bot(Color.GREEN)
    lobby.add_bot(Color.YELLOW)
    assert len(lobby.players()) == 4
    with pytest.raises(LobbyFull):
        lobby.add_bot(Color.RED)


def test_add_bot_respects_three_bot_cap_even_when_lobby_has_room():
    """0 humanos + 3 bots: la regla 'max bots' rechaza el cuarto antes que
    la regla de capacidad. El server normalmente normaliza este estado con
    clear_bots, pero la cota del lobby debe ser robusta."""
    lobby = Lobby()
    lobby.add_bot(Color.BLUE)
    lobby.add_bot(Color.GREEN)
    lobby.add_bot(Color.YELLOW)
    assert len(lobby.players()) == 3
    with pytest.raises(LobbyFull) as exc:
        lobby.add_bot(Color.RED)
    assert "max" in str(exc.value).lower() and "bot" in str(exc.value).lower()


def test_remove_bot_deletes_only_bots():
    lobby = Lobby()
    lobby.join("c1", "Cris")
    bot = lobby.add_bot(Color.BLUE)
    lobby.remove_bot(bot.conn_id)
    assert all(p.conn_id != bot.conn_id for p in lobby.players())


def test_remove_bot_refuses_human():
    lobby = Lobby()
    lobby.join("c1", "Cris")
    with pytest.raises(LobbyError):
        lobby.remove_bot("c1")


def test_clear_bots_removes_all_bots_keeps_humans():
    lobby = Lobby()
    lobby.join("c1", "Cris")
    lobby.add_bot(Color.BLUE)
    lobby.add_bot(Color.GREEN)
    lobby.clear_bots()
    assert [p.username for p in lobby.players()] == ["Cris"]


def test_host_is_first_human_not_bot():
    lobby = Lobby()
    human = lobby.join("c1", "Cris")
    bot = lobby.add_bot(Color.BLUE)
    assert human.is_host is True
    assert bot.is_host is False
    assert lobby.host_conn_id() == "c1"


def test_host_passes_to_next_human_skipping_bots_on_leave():
    lobby = Lobby()
    lobby.join("c1", "Cris")
    lobby.add_bot(Color.BLUE)
    lobby.join("c2", "Ana")
    lobby.leave("c1")
    assert lobby.host_conn_id() == "c2"


def test_host_conn_id_returns_none_when_no_humans_left():
    lobby = Lobby()
    lobby.join("c1", "Cris")
    lobby.add_bot(Color.BLUE)
    lobby.leave("c1")
    assert lobby.host_conn_id() is None


def test_can_start_requires_at_least_one_human():
    lobby = Lobby()
    lobby.join("c1", "Cris")
    lobby.add_bot(Color.BLUE)
    lobby.select_color("c1", Color.RED)
    assert lobby.can_start() is True
    lobby.leave("c1")
    # Quedan bots con color, sin humanos:
    assert lobby.can_start() is False
