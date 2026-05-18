"""Pruebas de GameSession con bots."""
from __future__ import annotations

import random

from core.entities import Color
from server.session import GameSession, SessionEntry


def _entries() -> list[SessionEntry]:
    return [
        SessionEntry(conn_id="c1",       username="Cris",     color=Color.RED,  is_bot=False),
        SessionEntry(conn_id="bot:blue", username="Bot Azul", color=Color.BLUE, is_bot=True),
    ]


def test_session_accepts_session_entries_with_is_bot():
    session = GameSession(entries=_entries(), rng=random.Random(1))
    assert session.is_bot("bot:blue") is True
    assert session.is_bot("c1") is False


def test_bot_conn_ids_and_human_conn_ids_are_disjoint():
    session = GameSession(entries=_entries(), rng=random.Random(1))
    assert session.bot_conn_ids() == ["bot:blue"]
    assert session.human_conn_ids() == ["c1"]


def test_human_connected_count_ignores_bots():
    session = GameSession(entries=_entries(), rng=random.Random(1))
    assert session.human_connected_count() == 1
    session.mark_disconnected("c1")
    assert session.human_connected_count() == 0


def test_human_connected_count_does_not_count_bots_even_if_marked_disconnected():
    session = GameSession(entries=_entries(), rng=random.Random(1))
    session.mark_disconnected("bot:blue")
    assert session.human_connected_count() == 1


def test_state_dict_propagates_is_bot_per_player():
    session = GameSession(entries=_entries(), rng=random.Random(1))
    state = session.state_dict()
    by_color = {p["color"]: p for p in state["players"]}
    assert by_color["red"]["is_bot"] is False
    assert by_color["blue"]["is_bot"] is True
