import pytest

from server.session import GameSession, SessionEntry
from core.entities import Color, GamePhase, PieceState
from tests.conftest import ScriptedRandom


def _make_session(rng: ScriptedRandom | None = None) -> GameSession:
    return GameSession(
        entries=[
            SessionEntry("c1", "Alice", Color.RED,  False),
            SessionEntry("c2", "Bob",   Color.BLUE, False),
        ],
        rng=rng or ScriptedRandom([]),
    )


def test_session_creates_game_in_setup_phase():
    session = _make_session()
    assert session.game.phase is GamePhase.SETUP
    assert session.color_for_conn("c1") is Color.RED
    assert session.conn_for_color(Color.BLUE) == "c2"


def test_session_unknown_conn_returns_none():
    session = _make_session()
    assert session.color_for_conn("ghost") is None
    assert session.conn_for_color(Color.GREEN) is None


def test_roll_initial_delegates_to_engine():
    rng = ScriptedRandom([6, 5, 3, 4])  # Alice=11, Bob=7
    session = _make_session(rng)
    alice_idx = session.player_index_for_conn("c1")
    bob_idx = session.player_index_for_conn("c2")
    assert sum(session.roll_initial(alice_idx)) == 11
    assert sum(session.roll_initial(bob_idx)) == 7
    assert session.game.phase is GamePhase.ROLLING


def test_current_turn_conn_id():
    rng = ScriptedRandom([6, 5, 3, 4])
    session = _make_session(rng)
    session.roll_initial(0)
    session.roll_initial(1)
    # Alice (c1) won the initial roll, so turn_order[0] is Alice's index.
    assert session.current_turn_conn_id() == "c1"


def test_state_dict_excludes_rng():
    session = _make_session()
    state = session.state_dict()
    assert "_rng" not in state
    assert "phase" in state
    assert "players" in state


def test_mark_disconnected_stores_color():
    session = _make_session()
    session.mark_disconnected("c1")
    assert Color.RED in session.disconnected_colors


def test_connected_count():
    session = _make_session()
    assert session.connected_count() == 2
    session.mark_disconnected("c1")
    assert session.connected_count() == 1


def test_advance_past_disconnected_skips_rolling():
    rng = ScriptedRandom([6, 5, 3, 4])
    session = _make_session(rng)
    session.roll_initial(0)  # Alice=11
    session.roll_initial(1)  # Bob=7 → Alice first
    assert session.current_turn_conn_id() == "c1"
    # Alice disconnects.
    session.mark_disconnected("c1")
    session.advance_past_disconnected()
    # Should have advanced to Bob (c2).
    assert session.current_turn_conn_id() == "c2"


def test_advance_past_disconnected_stops_if_all_disconnected():
    rng = ScriptedRandom([6, 5, 3, 4])
    session = _make_session(rng)
    session.roll_initial(0)
    session.roll_initial(1)
    session.mark_disconnected("c1")
    session.mark_disconnected("c2")
    # No one left; the session signals game cannot continue.
    assert not session.advance_past_disconnected()
    assert session.connected_count() == 0
