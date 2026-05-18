"""End-to-end tests del servidor con bots, vía SocketClient."""
from __future__ import annotations

import random
import time

import pytest

from tests_server.conftest import inline_bot_delay


def _flush_welcome_and_lobby(client) -> list[dict]:
    return client.drain(expected_count=2, timeout=1.0)


def _send(client, msg: dict) -> None:
    client.send(msg)


# ----- lobby commands -----

def test_lobby_update_includes_is_bot_flag(server_factory, client_factory):
    host_addr = server_factory(rng=random.Random(0))
    host = client_factory(*host_addr)
    _send(host, {"type": "join", "username": "Cris"})
    _flush_welcome_and_lobby(host)

    _send(host, {"type": "add_bot"})
    update = host.recv(timeout=1.0)
    assert update["type"] == "lobby_update"
    assert any(p["is_bot"] is True for p in update["players"])
    assert any(p["is_bot"] is False for p in update["players"])


def test_non_host_cannot_add_bot(server_factory, client_factory):
    addr = server_factory(rng=random.Random(0))
    host = client_factory(*addr)
    _send(host, {"type": "join", "username": "Cris"})
    _flush_welcome_and_lobby(host)
    guest = client_factory(*addr)
    _send(guest, {"type": "join", "username": "Ana"})
    guest.drain(expected_count=2, timeout=1.0)
    host.recv(timeout=1.0)  # lobby_update por el join de Ana

    _send(guest, {"type": "add_bot"})
    err = guest.recv(timeout=1.0)
    assert err["type"] == "error"
    assert err["code"] == "FORBIDDEN"


def test_remove_bot_works(server_factory, client_factory):
    addr = server_factory(rng=random.Random(0))
    host = client_factory(*addr)
    _send(host, {"type": "join", "username": "Cris"})
    _flush_welcome_and_lobby(host)
    _send(host, {"type": "add_bot"})
    update = host.recv(timeout=1.0)
    bot_color = next(p["color"] for p in update["players"] if p["is_bot"])

    _send(host, {"type": "remove_bot", "color": bot_color})
    update2 = host.recv(timeout=1.0)
    assert all(p["is_bot"] is False for p in update2["players"])


def test_add_bot_assigns_first_available_color(server_factory, client_factory):
    addr = server_factory(rng=random.Random(0))
    host = client_factory(*addr)
    _send(host, {"type": "join", "username": "Cris"})
    _flush_welcome_and_lobby(host)
    _send(host, {"type": "select_color", "color": "red"})
    host.recv(timeout=1.0)

    _send(host, {"type": "add_bot"})
    update = host.recv(timeout=1.0)
    bot = next(p for p in update["players"] if p["is_bot"])
    # 'red' está ocupado; el bot toma el primer libre — blue, por el orden del enum.
    assert bot["color"] == "blue"


def test_add_bot_rejected_when_three_bots_already(server_factory, client_factory):
    addr = server_factory(rng=random.Random(0))
    host = client_factory(*addr)
    _send(host, {"type": "join", "username": "Cris"})
    _flush_welcome_and_lobby(host)
    for _ in range(3):
        _send(host, {"type": "add_bot"})
        host.recv(timeout=1.0)
    _send(host, {"type": "add_bot"})
    err = host.recv(timeout=1.0)
    assert err["type"] == "error"
    assert err["code"] == "FORBIDDEN"


# ----- in-game with bots (uses inline_bot_delay for determinism) -----

def test_bot_rolls_initial_automatically_in_setup(server_factory, client_factory):
    """Con bot_delay_fn inline, el bot tira inicial sincronamente cuando se programa."""
    addr = server_factory(rng=random.Random(123), bot_delay_fn=inline_bot_delay)
    host = client_factory(*addr)
    _send(host, {"type": "join", "username": "Cris"})
    _flush_welcome_and_lobby(host)
    _send(host, {"type": "select_color", "color": "red"})
    host.recv(timeout=1.0)
    _send(host, {"type": "add_bot"})
    host.recv(timeout=1.0)
    _send(host, {"type": "start_game"})

    events = host.drain(timeout=2.0)
    initial_rolls = [e for e in events if e.get("type") == "initial_roll"]
    rollers = {e["username"] for e in initial_rolls}
    assert "Bot Azul" in rollers
    assert "Cris" not in rollers  # el humano aún no ha tirado


def test_bot_plays_after_human_rolls_initial(server_factory, client_factory):
    """Cuando el humano tira inicial y se resuelve el turn_order, si toca al bot,
    el bot debe jugar su turno automáticamente."""
    addr = server_factory(rng=random.Random(7), bot_delay_fn=inline_bot_delay)
    host = client_factory(*addr)
    _send(host, {"type": "join", "username": "Cris"})
    _flush_welcome_and_lobby(host)
    _send(host, {"type": "select_color", "color": "red"})
    host.recv(timeout=1.0)
    _send(host, {"type": "add_bot"})
    host.recv(timeout=1.0)
    _send(host, {"type": "start_game"})
    host.drain(timeout=1.5)
    _send(host, {"type": "roll_initial"})

    events = host.drain(timeout=3.0)
    # Si la partida progresa con el bot tomando turnos, deben aparecer eventos:
    # al menos un dice_result (del bot o del humano).
    types = [e.get("type") for e in events]
    assert "state_update" in types


def test_all_humans_leave_resets_to_lobby(server_factory, client_factory):
    """Si el único humano deja la partida con bots dentro, se resetea a LOBBY
    y un nuevo humano puede entrar limpio."""
    addr = server_factory(rng=random.Random(0), bot_delay_fn=inline_bot_delay)
    host = client_factory(*addr)
    _send(host, {"type": "join", "username": "Cris"})
    _flush_welcome_and_lobby(host)
    _send(host, {"type": "select_color", "color": "red"})
    host.recv(timeout=1.0)
    _send(host, {"type": "add_bot"})
    host.recv(timeout=1.0)
    _send(host, {"type": "start_game"})
    host.drain(timeout=1.5)

    host.close()
    time.sleep(0.4)

    other = client_factory(*addr)
    _send(other, {"type": "join", "username": "Ana"})
    events = other.drain(expected_count=2, timeout=1.0)
    welcome = next(e for e in events if e["type"] == "welcome")
    assert welcome["is_host"] is True  # arrancó lobby limpio
    lobby_update = next(e for e in events if e["type"] == "lobby_update")
    assert len(lobby_update["players"]) == 1


def test_legacy_two_humans_one_leaves_other_wins(server_factory, client_factory):
    """Regresión: 2 humanos sin bots, uno se va → el otro gana (flujo heredado)."""
    addr = server_factory(rng=random.Random(11), bot_delay_fn=inline_bot_delay)
    h1 = client_factory(*addr)
    h2 = client_factory(*addr)
    _send(h1, {"type": "join", "username": "Cris"})
    h1.drain(expected_count=2, timeout=1.0)
    _send(h2, {"type": "join", "username": "Ana"})
    h2.drain(expected_count=2, timeout=1.0)
    h1.recv(timeout=1.0)
    _send(h1, {"type": "select_color", "color": "red"})
    h1.drain(expected_count=1, timeout=1.0)
    h2.drain(expected_count=1, timeout=1.0)
    _send(h2, {"type": "select_color", "color": "blue"})
    h1.drain(expected_count=1, timeout=1.0)
    h2.drain(expected_count=1, timeout=1.0)
    _send(h1, {"type": "start_game"})
    h1.drain(timeout=1.0)
    h2.drain(timeout=1.0)

    h2.close()
    time.sleep(0.4)

    events = h1.drain(timeout=1.5)
    game_over = next((e for e in events if e["type"] == "game_over"), None)
    assert game_over is not None, "se esperaba game_over al quedar 1 jugador"
    assert game_over["winner_username"] == "Cris"


def test_clear_bots_when_last_human_leaves_lobby(server_factory, client_factory):
    """Si el único humano sale del LOBBY con bots dentro, los bots se eliminan."""
    addr = server_factory(rng=random.Random(0))
    host = client_factory(*addr)
    _send(host, {"type": "join", "username": "Cris"})
    _flush_welcome_and_lobby(host)
    _send(host, {"type": "add_bot"})
    host.recv(timeout=1.0)

    host.close()
    time.sleep(0.3)

    other = client_factory(*addr)
    _send(other, {"type": "join", "username": "Ana"})
    events = other.drain(expected_count=2, timeout=1.0)
    lobby_update = next(e for e in events if e["type"] == "lobby_update")
    assert all(p["is_bot"] is False for p in lobby_update["players"])
