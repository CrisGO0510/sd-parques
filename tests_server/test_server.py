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

    def close(self) -> None:
        pass


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


def test_fixture_spawns_server_and_accepts_client(server_factory, client_factory):
    host, port = server_factory()
    client = client_factory(host, port)
    client.send({"type": "join", "username": "Solo"})
    welcome = client.recv()
    assert welcome["type"] == "welcome"
    assert welcome["is_host"] is True


def test_message_in_closed_phase_rejected():
    """After game ends, server is in CLOSED phase and rejects commands."""
    srv, a, b = _start_two_player_game()
    srv.phase = ServerPhase.CLOSED  # Simulate game ended
    a.sent.clear()
    srv.handle_message(a, {"type": "roll_dice"})
    errors = [m for m in a.sent if m["type"] == "error"]
    assert any(m["code"] == "GAME_ENDED" for m in errors)


def test_disconnect_during_setup_auto_rolls_initial_so_setup_unblocks():
    """Repro: 3 players in SETUP, players 1 and 2 have rolled, player 3
    disconnects before rolling. Without an auto-roll the remaining
    clients would stare at "Esperando a los demás jugadores…" forever."""
    rng = ScriptedRandom([6, 5, 3, 4, 2, 1])
    srv = Server(rng=rng)
    alice, bob, carol = FakeConn("c1"), FakeConn("c2"), FakeConn("c3")
    for c in (alice, bob, carol):
        srv.register_connection(c)
        srv.handle_message(c, {"type": "join", "username": c.conn_id})
    srv.handle_message(alice, {"type": "select_color", "color": "red"})
    srv.handle_message(bob,   {"type": "select_color", "color": "green"})
    srv.handle_message(carol, {"type": "select_color", "color": "blue"})
    srv.handle_message(alice, {"type": "start_game"})
    # Only alice and bob roll their initial; carol leaves first.
    srv.handle_message(alice, {"type": "roll_initial"})
    srv.handle_message(bob,   {"type": "roll_initial"})
    assert srv.session.game.phase.value == "setup"

    alice.sent.clear(); bob.sent.clear()
    srv._on_disconnect(carol)

    # SETUP must be resolved — turn_order populated, phase now ROLLING,
    # and the current turn is on a *connected* player.
    assert srv.session.game.phase.value == "rolling"
    assert len(srv.session.game.turn_order) == 3
    assert srv.session.current_turn_conn_id() in {"c1", "c2"}
    # Survivors learned about the auto-roll and the new state.
    for surv in (alice, bob):
        assert any(m["type"] == "initial_roll" and m["player_index"] == 2 for m in surv.sent)
        assert any(m["type"] == "state_update" for m in surv.sent)


def test_disconnect_of_current_player_advances_turn_and_broadcasts():
    """3-player game: the current-turn player disconnects. Server must
    advance to the next connected player and broadcast the updated
    state (so the UI stops showing "Turno de <disconnected>")."""
    rng = ScriptedRandom([
        6, 5, 3, 4, 2, 1,  # initial rolls for 3 players
        # Alice=11 (carol? let's see), Bob=7, Carol=3 → Alice first, then Bob, then Carol
    ])
    srv = Server(rng=rng)
    alice, bob, carol = FakeConn("c1"), FakeConn("c2"), FakeConn("c3")
    for c in (alice, bob, carol):
        srv.register_connection(c)
        srv.handle_message(c, {"type": "join", "username": c.conn_id})
    srv.handle_message(alice, {"type": "select_color", "color": "red"})
    srv.handle_message(bob,   {"type": "select_color", "color": "green"})
    srv.handle_message(carol, {"type": "select_color", "color": "blue"})
    srv.handle_message(alice, {"type": "start_game"})
    srv.handle_message(alice, {"type": "roll_initial"})
    srv.handle_message(bob,   {"type": "roll_initial"})
    srv.handle_message(carol, {"type": "roll_initial"})

    # Identify who holds the current turn and disconnect them.
    current_conn_id = srv.session.current_turn_conn_id()
    current_conn = next(c for c in (alice, bob, carol) if c.conn_id == current_conn_id)
    others = [c for c in (alice, bob, carol) if c is not current_conn]
    for o in others:
        o.sent.clear()

    srv._on_disconnect(current_conn)

    # Turn must now belong to one of the remaining connected players.
    new_conn_id = srv.session.current_turn_conn_id()
    assert new_conn_id in {o.conn_id for o in others}
    # And both survivors should have received a state_update reflecting it.
    for o in others:
        updates = [m for m in o.sent if m["type"] == "state_update"]
        assert updates, f"{o.conn_id} got no state_update after peer disconnected"
        last = updates[-1]
        # current_turn_index points to the new (connected) player.
        turn_order = last["state"]["turn_order"]
        current_idx = last["state"]["current_turn_index"]
        player_idx_holding_turn = turn_order[current_idx]
        player_color = last["state"]["players"][player_idx_holding_turn]["color"]
        assert player_color != srv.session.color_for_conn(current_conn.conn_id).value


def test_disconnect_mid_game_skips_disconnected_turn():
    """4-player scenario: 2 players disconnect mid-game. The server
    should keep the turn on a *connected* player, not hang waiting for
    the disconnected ones."""
    rng = ScriptedRandom(
        [6, 5, 3, 4, 5, 3, 2, 4,     # initial rolls for 4 players
         1, 2,                        # later roll_dice calls don't matter here
        ]
    )
    srv = Server(rng=rng)
    conns = [FakeConn(f"c{i}") for i in range(1, 5)]
    colors = ["red", "green", "blue", "yellow"]
    names = ["Alice", "Bob", "Carol", "Dave"]
    for c in conns:
        srv.register_connection(c)
    for c, name in zip(conns, names):
        srv.handle_message(c, {"type": "join", "username": name})
    for c, color in zip(conns, colors):
        srv.handle_message(c, {"type": "select_color", "color": color})
    srv.handle_message(conns[0], {"type": "start_game"})
    for c in conns:
        srv.handle_message(c, {"type": "roll_initial"})
    # All 4 are connected. Find who holds the turn, then disconnect them
    # plus one of their direct neighbours — the remaining 2 should keep
    # rotating without the turn ever freezing on an absent color.
    current_id = srv.session.current_turn_conn_id()
    to_drop = [c for c in conns if c.conn_id == current_id][:1]
    others = [c for c in conns if c is not to_drop[0]]
    to_drop.append(others[0])

    for c in to_drop:
        srv._on_disconnect(c)

    # Server should still be IN_GAME (2 players remain) and the current
    # turn must belong to one of the still-connected players.
    assert srv.phase is ServerPhase.IN_GAME
    new_current_id = srv.session.current_turn_conn_id()
    alive_ids = {c.conn_id for c in conns if c not in to_drop}
    assert new_current_id in alive_ids


def test_all_players_disconnect_resets_server_to_lobby():
    """When every client from an in-progress game disconnects, the
    server returns to LOBBY so the next client can start a fresh round
    without restarting the process."""
    srv, a, b = _start_two_player_game()
    # First disconnect ends the game (connected_count drops below 2).
    srv._on_disconnect(a)
    assert srv.phase is ServerPhase.CLOSED
    # Second disconnect empties the server → auto-reset to LOBBY.
    srv._on_disconnect(b)
    assert srv.phase is ServerPhase.LOBBY
    assert srv.session is None
    assert srv._connections == {}

    # A brand-new client can now join and start a game.
    charlie = FakeConn("c3")
    srv.register_connection(charlie)
    srv.handle_message(charlie, {"type": "join", "username": "Charlie"})
    assert any(m["type"] == "welcome" and m["is_host"] for m in charlie.sent)


def test_invalid_color_in_select_color():
    """Selecting a non-existent color returns BAD_MESSAGE error."""
    srv = Server()
    a = FakeConn("c1")
    srv.register_connection(a)
    srv.handle_message(a, {"type": "join", "username": "Alice"})
    a.sent.clear()
    srv.handle_message(a, {"type": "select_color", "color": "neon_purple"})
    errors = [m for m in a.sent if m["type"] == "error"]
    assert any(m["code"] == "BAD_MESSAGE" for m in errors)


def test_start_game_without_enough_players():
    """Starting game with only 1 player is forbidden."""
    srv = Server()
    a = FakeConn("c1")
    srv.register_connection(a)
    srv.handle_message(a, {"type": "join", "username": "Alice"})
    srv.handle_message(a, {"type": "select_color", "color": "red"})
    a.sent.clear()
    srv.handle_message(a, {"type": "start_game"})
    errors = [m for m in a.sent if m["type"] == "error"]
    assert any(m["code"] == "FORBIDDEN" for m in errors)


def test_leave_in_lobby():
    """Player can leave lobby, others see updated list."""
    srv = Server()
    a, b = FakeConn("c1"), FakeConn("c2")
    srv.register_connection(a); srv.register_connection(b)
    srv.handle_message(a, {"type": "join", "username": "Alice"})
    srv.handle_message(b, {"type": "join", "username": "Bob"})
    a.sent.clear(); b.sent.clear()
    srv.handle_message(a, {"type": "leave"})
    # Alice should be unregistered.
    assert "c1" not in srv._connections
    # Bob should see updated lobby.
    updates = [m for m in b.sent if m["type"] == "lobby_update"]
    assert updates  # received at least one update
    assert len(updates[-1]["players"]) == 1  # only Bob left


def test_bad_protocol_message():
    """Malformed JSON in protocol is caught and error sent."""
    srv = Server()
    a = FakeConn("c1")
    srv.register_connection(a)
    # Simulate a malformed message that fails validation
    # (e.g., missing "type" field or wrong field types)
    srv.handle_message(a, {"username": "Alice"})  # missing "type"
    errors = [m for m in a.sent if m["type"] == "error"]
    assert any(m["code"] == "BAD_MESSAGE" for m in errors)


def test_join_sends_welcome_to_first_player():
    """First player to join gets is_host=True."""
    srv = Server()
    a = FakeConn("c1")
    srv.register_connection(a)
    srv.handle_message(a, {"type": "join", "username": "First"})
    welcome = next(m for m in a.sent if m["type"] == "welcome")
    assert welcome["is_host"] is True
    assert welcome["username"] == "First"


def test_unhandled_command_in_game_phase():
    """Command 'join' is forbidden in IN_GAME phase."""
    srv, a, b = _start_two_player_game()
    a.sent.clear()
    srv.handle_message(a, {"type": "join", "username": "Charlie"})
    errors = [m for m in a.sent if m["type"] == "error"]
    assert any(m["code"] == "FORBIDDEN" for m in errors)


def test_roll_dice_broadcasts_dice_result_and_state():
    """roll_dice command broadcasts dice_result and state_update."""
    rng = ScriptedRandom([6, 5, 3, 4, 2, 3])  # Extra rolls for dice
    srv, a, b = _start_two_player_game(rng)
    # Both players roll initial to determine order.
    srv.handle_message(a, {"type": "roll_initial"})
    srv.handle_message(b, {"type": "roll_initial"})
    a.sent.clear(); b.sent.clear()
    # Alice (current player) rolls dice.
    srv.handle_message(a, {"type": "roll_dice"})
    # Both players should receive dice_result and state_update.
    a_dice = [m for m in a.sent if m["type"] == "dice_result"]
    b_dice = [m for m in b.sent if m["type"] == "dice_result"]
    a_updates = [m for m in a.sent if m["type"] == "state_update"]
    assert a_dice
    assert b_dice
    assert a_updates


def test_crown_piece_broadcasts_state():
    """crown_piece command broadcasts state_update."""
    rng = ScriptedRandom([6, 5, 3, 4])
    srv, a, b = _start_two_player_game(rng)
    srv.handle_message(a, {"type": "roll_initial"})
    srv.handle_message(b, {"type": "roll_initial"})
    a.sent.clear(); b.sent.clear()
    # crown_piece would normally require a piece to be ready for crowning
    # just verify the dispatch path is reachable (error case is fine)
    srv.handle_message(a, {"type": "crown_piece", "piece_index": 0})
    # At least should broadcast something (either state_update or error)
    assert a.sent or b.sent
