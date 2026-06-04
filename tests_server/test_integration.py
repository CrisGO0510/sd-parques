"""End-to-end integration tests using real TCP sockets."""
from __future__ import annotations

import random
import time

from tests_server.conftest import inline_bot_delay


def test_lobby_flow_end_to_end(server_factory, client_factory):
    host, port = server_factory(rng=random.Random(0))

    alice = client_factory(host, port)
    bob = client_factory(host, port)

    alice.send({"type": "join", "username": "Alice"})
    bob.send({"type": "join", "username": "Bob"})

    # Drain welcome + lobby_update events.
    alice.drain(expected_count=3, timeout=1.0)
    bob.drain(expected_count=2, timeout=1.0)

    alice.send({"type": "select_color", "color": "red"})
    bob.send({"type": "select_color", "color": "blue"})
    alice.drain(expected_count=2, timeout=1.0)
    bob.drain(expected_count=2, timeout=1.0)

    alice.send({"type": "start_game"})

    alice_started = False
    bob_started = False
    for m in alice.drain(expected_count=3, timeout=1.0):
        if m["type"] == "game_started":
            alice_started = True
    for m in bob.drain(expected_count=3, timeout=1.0):
        if m["type"] == "game_started":
            bob_started = True
    assert alice_started and bob_started


def test_game_resets_to_lobby_when_last_human_leaves(server_factory, client_factory):
    """1 humano + 2 bots: cuando el humano deja la partida, el server vuelve a
    LOBBY y un cliente nuevo entra limpio como host."""
    host, port = server_factory(rng=random.Random(0), bot_delay_fn=inline_bot_delay)

    alice = client_factory(host, port)
    alice.send({"type": "join", "username": "Alice"})
    alice.drain(expected_count=2, timeout=1.0)
    alice.send({"type": "select_color", "color": "red"})
    alice.drain(expected_count=1, timeout=1.0)
    alice.send({"type": "start_game"})
    alice.drain(timeout=0.5)

    alice.close()
    time.sleep(0.4)

    other = client_factory(host, port)
    other.send({"type": "join", "username": "Bob"})
    events = other.drain(expected_count=2, timeout=1.0)
    welcome = next(e for e in events if e["type"] == "welcome")
    assert welcome["is_host"] is True
