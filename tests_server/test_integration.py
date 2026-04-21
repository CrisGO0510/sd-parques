"""End-to-end integration tests using real TCP sockets."""
from __future__ import annotations

from tests.conftest import ScriptedRandom


def test_lobby_flow_end_to_end(server_factory, client_factory):
    rng = ScriptedRandom([6, 5, 3, 4])  # initial rolls
    host, port = server_factory(rng=rng)

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


def test_game_ends_when_everyone_disconnects_except_one(server_factory, client_factory):
    rng = ScriptedRandom([6, 5, 3, 4])
    host, port = server_factory(rng=rng)

    alice = client_factory(host, port)
    bob = client_factory(host, port)

    alice.send({"type": "join", "username": "Alice"})
    bob.send({"type": "join", "username": "Bob"})
    alice.drain(timeout=0.5)
    bob.drain(timeout=0.5)
    alice.send({"type": "select_color", "color": "red"})
    bob.send({"type": "select_color", "color": "blue"})
    alice.drain(timeout=0.5)
    bob.drain(timeout=0.5)
    alice.send({"type": "start_game"})
    alice.drain(timeout=0.5)
    bob.drain(timeout=0.5)

    # Bob disconnects.
    bob.close()

    # Alice should eventually receive a game_over.
    msgs = alice.drain(expected_count=5, timeout=2.0)
    game_overs = [m for m in msgs if m["type"] == "game_over"]
    assert game_overs
    assert game_overs[0]["winner_username"] == "Alice"
