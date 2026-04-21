import socket
import threading
import time

import pytest
from dataclasses import dataclass, field

from server.protocol import encode
from server.server import Server, ServerPhase
from tests.conftest import ScriptedRandom


@dataclass
class FakeConn:
    conn_id: str
    sent: list[dict] = field(default_factory=list)

    def send(self, data: bytes) -> None:
        import json
        self.sent.append(json.loads(data.decode("utf-8").rstrip("\n")))


def _seed_rng() -> ScriptedRandom:
    return ScriptedRandom([6, 5, 3, 4])  # Alice=11, Bob=7


def test_server_starts_in_lobby():
    srv = Server(host="127.0.0.1", port=0)
    assert srv.phase is ServerPhase.LOBBY
    assert srv.lobby is not None
    assert srv.session is None


def test_server_lock_exists():
    srv = Server(host="127.0.0.1", port=0)
    assert srv.lock is not None
    # Acquire/release works (not deadlocked):
    with srv.lock:
        pass


def test_join_welcomes_and_broadcasts_lobby_update():
    srv = Server()
    alice = FakeConn("c1")
    srv.register_connection(alice)
    srv.handle_message(alice, {"type": "join", "username": "Alice"})
    assert any(m["type"] == "welcome" and m["is_host"] for m in alice.sent)
    assert any(m["type"] == "lobby_update" for m in alice.sent)


def test_second_join_is_not_host_and_both_see_update():
    srv = Server()
    alice, bob = FakeConn("c1"), FakeConn("c2")
    for c in (alice, bob):
        srv.register_connection(c)
    srv.handle_message(alice, {"type": "join", "username": "Alice"})
    srv.handle_message(bob,   {"type": "join", "username": "Bob"})
    # Bob gets welcome with is_host=False.
    bob_welcome = next(m for m in bob.sent if m["type"] == "welcome")
    assert bob_welcome["is_host"] is False
    # Alice gets a second lobby_update after Bob joins.
    alice_updates = [m for m in alice.sent if m["type"] == "lobby_update"]
    assert len(alice_updates) == 2


def test_duplicate_username_rejected_with_error():
    srv = Server()
    a, b = FakeConn("c1"), FakeConn("c2")
    srv.register_connection(a); srv.register_connection(b)
    srv.handle_message(a, {"type": "join", "username": "X"})
    srv.handle_message(b, {"type": "join", "username": "X"})
    errors = [m for m in b.sent if m["type"] == "error"]
    assert any(m["code"] == "DUPLICATE_PLAYER" for m in errors)


def test_select_color_broadcasts_update():
    srv = Server()
    a = FakeConn("c1")
    srv.register_connection(a)
    srv.handle_message(a, {"type": "join", "username": "Alice"})
    a.sent.clear()
    srv.handle_message(a, {"type": "select_color", "color": "red"})
    assert any(
        m["type"] == "lobby_update"
        and any(p.get("color") == "red" for p in m["players"])
        for m in a.sent
    )


def test_start_game_by_non_host_forbidden():
    srv = Server()
    a, b = FakeConn("c1"), FakeConn("c2")
    srv.register_connection(a); srv.register_connection(b)
    srv.handle_message(a, {"type": "join", "username": "Alice"})
    srv.handle_message(b, {"type": "join", "username": "Bob"})
    srv.handle_message(a, {"type": "select_color", "color": "red"})
    srv.handle_message(b, {"type": "select_color", "color": "blue"})
    b.sent.clear()
    srv.handle_message(b, {"type": "start_game"})  # Bob is not host
    assert any(m["type"] == "error" and m["code"] == "FORBIDDEN" for m in b.sent)


def test_start_game_by_host_transitions_to_in_game():
    srv = Server(rng=_seed_rng())
    a, b = FakeConn("c1"), FakeConn("c2")
    srv.register_connection(a); srv.register_connection(b)
    srv.handle_message(a, {"type": "join", "username": "Alice"})
    srv.handle_message(b, {"type": "join", "username": "Bob"})
    srv.handle_message(a, {"type": "select_color", "color": "red"})
    srv.handle_message(b, {"type": "select_color", "color": "blue"})
    a.sent.clear(); b.sent.clear()
    srv.handle_message(a, {"type": "start_game"})
    assert srv.phase is ServerPhase.IN_GAME
    # Both clients should have received a game_started event.
    assert any(m["type"] == "game_started" for m in a.sent)
    assert any(m["type"] == "game_started" for m in b.sent)
    # And a state_update right after.
    assert any(m["type"] == "state_update" for m in a.sent)


def _start_two_player_game(rng=None):
    """Helper: server con 2 clientes joineados, coloreados, y start_game hecho."""
    srv = Server(rng=rng or _seed_rng())
    a, b = FakeConn("c1"), FakeConn("c2")
    srv.register_connection(a); srv.register_connection(b)
    srv.handle_message(a, {"type": "join", "username": "Alice"})
    srv.handle_message(b, {"type": "join", "username": "Bob"})
    srv.handle_message(a, {"type": "select_color", "color": "red"})
    srv.handle_message(b, {"type": "select_color", "color": "blue"})
    srv.handle_message(a, {"type": "start_game"})
    a.sent.clear(); b.sent.clear()
    return srv, a, b


def test_roll_initial_broadcasts():
    srv, a, b = _start_two_player_game()
    srv.handle_message(a, {"type": "roll_initial"})
    assert any(m["type"] == "initial_roll" for m in a.sent)
    assert any(m["type"] == "initial_roll" for m in b.sent)
    # state_update should also be broadcast.
    assert any(m["type"] == "state_update" for m in a.sent)


def test_roll_dice_not_my_turn_is_wrong_phase_or_forbidden():
    # Alice won the initial order; Bob trying to roll should be rejected.
    rng = _seed_rng()  # Alice first
    srv, a, b = _start_two_player_game(rng)
    srv.handle_message(a, {"type": "roll_initial"})
    srv.handle_message(b, {"type": "roll_initial"})
    b.sent.clear()
    srv.handle_message(b, {"type": "roll_dice"})  # not Bob's turn
    assert any(m["type"] == "error" for m in b.sent)


def test_unknown_conn_sending_game_command_without_join_is_rejected():
    srv, a, b = _start_two_player_game()
    ghost = FakeConn("ghost")
    srv.register_connection(ghost)
    srv.handle_message(ghost, {"type": "roll_dice"})
    assert any(m["type"] == "error" for m in ghost.sent)


def test_server_binds_and_accepts_connection():
    srv = Server(host="127.0.0.1", port=0)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    srv.wait_ready(timeout=1.0)
    assert srv.port > 0
    # Just connect and close — should not crash the server.
    sock = socket.create_connection(("127.0.0.1", srv.port), timeout=1.0)
    sock.close()
    time.sleep(0.1)  # let the server's handler see the disconnect
    srv.shutdown()
    thread.join(timeout=2.0)
    assert not thread.is_alive()
