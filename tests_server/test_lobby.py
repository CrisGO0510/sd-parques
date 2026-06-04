import pytest

from server.lobby import Lobby, LobbyFull, LobbyError
from core.exceptions import DuplicatePlayer
from core.entities import Color


def _humans(lobby: Lobby):
    return [p for p in lobby.players() if not p.is_bot]


def test_first_joiner_is_host():
    lobby = Lobby()
    p = lobby.join("c1", "Alice")
    assert p.username == "Alice"
    assert p.is_host is True
    assert p.color is None


def test_second_joiner_is_not_host():
    lobby = Lobby()
    lobby.join("c1", "Alice")
    p = lobby.join("c2", "Bob")
    assert p.is_host is False


def test_rejects_duplicate_username():
    lobby = Lobby()
    lobby.join("c1", "Alice")
    with pytest.raises(DuplicatePlayer, match="name"):
        lobby.join("c2", "Alice")


def test_rejects_third_human():
    lobby = Lobby()
    lobby.join("c1", "Alice")
    lobby.join("c2", "Bob")
    with pytest.raises(LobbyFull):
        lobby.join("c3", "Eve")


def test_leave_removes_player():
    lobby = Lobby()
    lobby.join("c1", "Alice")
    lobby.join("c2", "Bob")
    lobby.leave("c1")
    assert not lobby.has_conn("c1")
    assert lobby.has_conn("c2")


def test_leave_promotes_next_human_host():
    lobby = Lobby()
    lobby.join("c1", "Alice")  # host
    lobby.join("c2", "Bob")
    lobby.leave("c1")
    assert lobby.host_conn_id() == "c2"


def test_leave_nonexistent_is_noop():
    lobby = Lobby()
    lobby.leave("unknown")  # does not raise


def test_players_returns_bots_then_join_order():
    lobby = Lobby()
    lobby.join("c1", "Alice")
    lobby.join("c2", "Bob")
    human_names = [p.username for p in _humans(lobby)]
    assert human_names == ["Alice", "Bob"]


def test_select_color_assigns():
    lobby = Lobby()
    lobby.join("c1", "Alice")
    lobby.select_color("c1", Color.RED)
    assert lobby.get_by_conn("c1").color is Color.RED


def test_select_color_rejects_duplicate_between_humans():
    lobby = Lobby()
    lobby.join("c1", "Alice")
    lobby.join("c2", "Bob")
    lobby.select_color("c1", Color.RED)
    with pytest.raises(DuplicatePlayer, match="color"):
        lobby.select_color("c2", Color.RED)


def test_select_color_rejects_bot_color():
    lobby = Lobby()
    lobby.join("c1", "Alice")
    with pytest.raises(DuplicatePlayer, match="color"):
        lobby.select_color("c1", Color.GREEN)


def test_select_color_allows_changing_own():
    lobby = Lobby()
    lobby.join("c1", "Alice")
    lobby.select_color("c1", Color.RED)
    lobby.select_color("c1", Color.BLUE)
    assert lobby.get_by_conn("c1").color is Color.BLUE


def test_select_color_unknown_conn_raises():
    lobby = Lobby()
    with pytest.raises(LobbyError):
        lobby.select_color("ghost", Color.RED)


def test_available_colors_is_red_and_blue_only():
    lobby = Lobby()
    lobby.join("c1", "Alice")
    lobby.select_color("c1", Color.RED)
    available = lobby.available_colors()
    assert available == [Color.BLUE]


def test_can_start_with_one_human_and_two_bots():
    lobby = Lobby()
    assert not lobby.can_start()
    lobby.join("c1", "Alice")
    assert not lobby.can_start()       # humano sin color
    lobby.select_color("c1", Color.RED)
    assert lobby.can_start()           # 1 humano con color basta
