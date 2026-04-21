import pytest

from server.lobby import Lobby, LobbyFull, LobbyError
from core.exceptions import DuplicatePlayer
from core.entities import Color


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


def test_rejects_fifth_joiner():
    lobby = Lobby()
    for i, name in enumerate(["A", "B", "C", "D"]):
        lobby.join(f"c{i}", name)
    with pytest.raises(LobbyFull):
        lobby.join("c5", "E")


def test_leave_removes_player():
    lobby = Lobby()
    lobby.join("c1", "Alice")
    lobby.join("c2", "Bob")
    lobby.leave("c1")
    assert not lobby.has_conn("c1")
    assert lobby.has_conn("c2")


def test_leave_promotes_next_host():
    lobby = Lobby()
    lobby.join("c1", "Alice")  # host
    lobby.join("c2", "Bob")
    lobby.leave("c1")
    assert lobby.host_conn_id() == "c2"


def test_leave_nonexistent_is_noop():
    lobby = Lobby()
    lobby.leave("unknown")  # does not raise


def test_players_returns_snapshot_in_join_order():
    lobby = Lobby()
    lobby.join("c1", "Alice")
    lobby.join("c2", "Bob")
    names = [p.username for p in lobby.players()]
    assert names == ["Alice", "Bob"]


def test_select_color_assigns():
    lobby = Lobby()
    lobby.join("c1", "Alice")
    lobby.select_color("c1", Color.RED)
    assert lobby.get_by_conn("c1").color is Color.RED


def test_select_color_rejects_duplicate():
    lobby = Lobby()
    lobby.join("c1", "Alice")
    lobby.join("c2", "Bob")
    lobby.select_color("c1", Color.RED)
    with pytest.raises(DuplicatePlayer, match="color"):
        lobby.select_color("c2", Color.RED)


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


def test_available_colors_excludes_taken():
    lobby = Lobby()
    lobby.join("c1", "Alice")
    lobby.select_color("c1", Color.RED)
    available = lobby.available_colors()
    assert Color.RED not in available
    assert Color.BLUE in available


def test_can_start_requires_min_two_with_color():
    lobby = Lobby()
    assert not lobby.can_start()
    lobby.join("c1", "Alice")
    lobby.select_color("c1", Color.RED)
    assert not lobby.can_start()  # only 1 player
    lobby.join("c2", "Bob")
    assert not lobby.can_start()  # Bob has no color
    lobby.select_color("c2", Color.BLUE)
    assert lobby.can_start()
