"""End-to-end del servidor con el modelo de 2 humanos + 2 bots fijos."""
from __future__ import annotations

import random
import time

import pytest

from tests_server.conftest import inline_bot_delay


def _flush_welcome_and_lobby(client) -> list[dict]:
    return client.drain(expected_count=2, timeout=1.0)


def _send(client, msg: dict) -> None:
    client.send(msg)


# ----- lobby con bots fijos -----

def test_lobby_update_includes_two_fixed_bots(server_factory, client_factory):
    addr = server_factory(rng=random.Random(0))
    host = client_factory(*addr)
    _send(host, {"type": "join", "username": "Cris"})
    events = _flush_welcome_and_lobby(host)
    update = next(e for e in events if e["type"] == "lobby_update")
    bots = [p for p in update["players"] if p["is_bot"]]
    names = {p["username"] for p in bots}
    assert names == {"Camila", "Bryan"}
    assert any(p["is_bot"] is False for p in update["players"])


def test_add_bot_command_is_rejected(server_factory, client_factory):
    addr = server_factory(rng=random.Random(0))
    host = client_factory(*addr)
    _send(host, {"type": "join", "username": "Cris"})
    _flush_welcome_and_lobby(host)
    _send(host, {"type": "add_bot"})
    err = host.recv(timeout=1.0)
    assert err["type"] == "error"
    assert err["code"] == "BAD_MESSAGE"


def test_remove_bot_command_is_rejected(server_factory, client_factory):
    addr = server_factory(rng=random.Random(0))
    host = client_factory(*addr)
    _send(host, {"type": "join", "username": "Cris"})
    _flush_welcome_and_lobby(host)
    _send(host, {"type": "remove_bot", "color": "green"})
    err = host.recv(timeout=1.0)
    assert err["type"] == "error"
    assert err["code"] == "BAD_MESSAGE"


def test_third_human_rejected(server_factory, client_factory):
    addr = server_factory(rng=random.Random(0))
    h1 = client_factory(*addr)
    _send(h1, {"type": "join", "username": "Cris"})
    _flush_welcome_and_lobby(h1)
    h2 = client_factory(*addr)
    _send(h2, {"type": "join", "username": "Ana"})
    h2.drain(expected_count=2, timeout=1.0)
    h1.recv(timeout=1.0)  # lobby_update por el join de Ana
    h3 = client_factory(*addr)
    _send(h3, {"type": "join", "username": "Eve"})
    err = h3.recv(timeout=1.0)
    assert err["type"] == "error"
    assert err["code"] == "LOBBY_FULL"


# ----- inicio con 1 humano -----

def test_single_human_can_start_with_two_bots(server_factory, client_factory):
    addr = server_factory(rng=random.Random(123), bot_delay_fn=inline_bot_delay)
    host = client_factory(*addr)
    _send(host, {"type": "join", "username": "Cris"})
    _flush_welcome_and_lobby(host)
    _send(host, {"type": "select_color", "color": "red"})
    host.recv(timeout=1.0)
    _send(host, {"type": "start_game"})

    events = host.drain(timeout=2.0)
    types = [e.get("type") for e in events]
    assert "game_started" in types
    # los bots Camila/Bryan deben tirar inicial automáticamente
    initial_rolls = [e for e in events if e.get("type") == "initial_roll"]
    rollers = {e["username"] for e in initial_rolls}
    assert {"Camila", "Bryan"} & rollers


# ----- cierre del lobby al irse el último humano -----

def test_lobby_resets_when_last_human_leaves(server_factory, client_factory):
    """Tras irse el único humano, el lobby se reinicia limpio: sigue teniendo
    exactamente los 2 bots y el siguiente humano entra como host."""
    addr = server_factory(rng=random.Random(0))
    host = client_factory(*addr)
    _send(host, {"type": "join", "username": "Cris"})
    _flush_welcome_and_lobby(host)
    _send(host, {"type": "select_color", "color": "red"})
    host.recv(timeout=1.0)

    host.close()
    time.sleep(0.3)

    other = client_factory(*addr)
    _send(other, {"type": "join", "username": "Ana"})
    events = other.drain(expected_count=2, timeout=1.0)
    welcome = next(e for e in events if e["type"] == "welcome")
    assert welcome["is_host"] is True  # lobby limpio: Ana es host
    update = next(e for e in events if e["type"] == "lobby_update")
    bots = [p for p in update["players"] if p["is_bot"]]
    assert {p["username"] for p in bots} == {"Camila", "Bryan"}
    humans = [p for p in update["players"] if not p["is_bot"]]
    assert [p["username"] for p in humans] == ["Ana"]


def test_lobby_resets_on_in_game_disconnect(server_factory, client_factory):
    """Si el único humano deja una partida en curso, el server vuelve a LOBBY
    y un nuevo humano entra limpio (regresión del _reset_to_lobby existente)."""
    addr = server_factory(rng=random.Random(0), bot_delay_fn=inline_bot_delay)
    host = client_factory(*addr)
    _send(host, {"type": "join", "username": "Cris"})
    _flush_welcome_and_lobby(host)
    _send(host, {"type": "select_color", "color": "red"})
    host.recv(timeout=1.0)
    _send(host, {"type": "start_game"})
    host.drain(timeout=1.5)

    host.close()
    time.sleep(0.4)

    other = client_factory(*addr)
    _send(other, {"type": "join", "username": "Ana"})
    events = other.drain(expected_count=2, timeout=1.0)
    welcome = next(e for e in events if e["type"] == "welcome")
    assert welcome["is_host"] is True
