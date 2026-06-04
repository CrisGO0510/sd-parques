import random
import socket
import threading
import time

import pytest
from dataclasses import dataclass, field

from server.protocol import encode
from server.server import Server, ServerPhase
from tests_server.conftest import inline_bot_delay


@dataclass
class FakeConn:
    conn_id: str
    sent: list[dict] = field(default_factory=list)

    def send(self, data: bytes) -> None:
        import json
        self.sent.append(json.loads(data.decode("utf-8").rstrip("\n")))

    def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Helpers para el modelo 2 humanos + 2 bots fijos (Camila=GREEN, Bryan=YELLOW).
# Los bots juegan solos; usamos inline_bot_delay para que sus turnos sean
# síncronos y deterministas, y random.Random(seed) para tener dados infinitos.
# ---------------------------------------------------------------------------

def _start_game_2h(seed: int = 0, *, clear: bool = True):
    """Server con 2 humanos (Alice=red, Bob=blue) + 2 bots, partida iniciada.

    Tras start_game los bots ya tiraron su dado inicial (inline). Los humanos
    aún no — usa `_play_to_active` para resolver el SETUP."""
    srv = Server(rng=random.Random(seed), bot_delay_fn=inline_bot_delay)
    a, b = FakeConn("c1"), FakeConn("c2")
    srv.register_connection(a); srv.register_connection(b)
    srv.handle_message(a, {"type": "join", "username": "Alice"})
    srv.handle_message(b, {"type": "join", "username": "Bob"})
    srv.handle_message(a, {"type": "select_color", "color": "red"})
    srv.handle_message(b, {"type": "select_color", "color": "blue"})
    srv.handle_message(a, {"type": "start_game"})
    if clear:
        a.sent.clear(); b.sent.clear()
    return srv, a, b


def _start_game_1h(seed: int = 0, *, clear: bool = True):
    """Server con 1 humano (Alice=red) + 2 bots, partida iniciada."""
    srv = Server(rng=random.Random(seed), bot_delay_fn=inline_bot_delay)
    a = FakeConn("c1")
    srv.register_connection(a)
    srv.handle_message(a, {"type": "join", "username": "Alice"})
    srv.handle_message(a, {"type": "select_color", "color": "red"})
    srv.handle_message(a, {"type": "start_game"})
    if clear:
        a.sent.clear()
    return srv, a


def _play_to_active(srv, *humans):
    """Ambos humanos tiran inicial; el SETUP se resuelve y los bots juegan sus
    turnos automáticamente hasta que el turno cae en un humano."""
    for h in humans:
        srv.handle_message(h, {"type": "roll_initial"})


def _current_human(srv, humans):
    cid = srv.session.current_turn_conn_id()
    return next((h for h in humans if h.conn_id == cid), None)


# ---------------------------------------------------------------------------
# Lobby / dispatch (independientes de la mecánica de juego)
# ---------------------------------------------------------------------------

def test_server_starts_in_lobby():
    srv = Server(host="127.0.0.1", port=0)
    assert srv.phase is ServerPhase.LOBBY
    assert srv.lobby is not None
    assert srv.session is None


def test_server_lock_exists():
    srv = Server(host="127.0.0.1", port=0)
    assert srv.lock is not None
    with srv.lock:
        pass


def test_join_welcomes_and_broadcasts_lobby_update():
    srv = Server()
    alice = FakeConn("c1")
    srv.register_connection(alice)
    srv.handle_message(alice, {"type": "join", "username": "Alice"})
    assert any(m["type"] == "welcome" and m["is_host"] for m in alice.sent)
    assert any(m["type"] == "lobby_update" for m in alice.sent)


def test_lobby_update_shows_two_fixed_bots():
    srv = Server()
    alice = FakeConn("c1")
    srv.register_connection(alice)
    srv.handle_message(alice, {"type": "join", "username": "Alice"})
    update = next(m for m in alice.sent if m["type"] == "lobby_update")
    bots = {p["username"] for p in update["players"] if p["is_bot"]}
    assert bots == {"Camila", "Bryan"}


def test_second_join_is_not_host_and_both_see_update():
    srv = Server()
    alice, bob = FakeConn("c1"), FakeConn("c2")
    for c in (alice, bob):
        srv.register_connection(c)
    srv.handle_message(alice, {"type": "join", "username": "Alice"})
    srv.handle_message(bob,   {"type": "join", "username": "Bob"})
    bob_welcome = next(m for m in bob.sent if m["type"] == "welcome")
    assert bob_welcome["is_host"] is False
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


def test_third_human_rejected_with_lobby_full():
    srv = Server()
    a, b, c = FakeConn("c1"), FakeConn("c2"), FakeConn("c3")
    for conn in (a, b, c):
        srv.register_connection(conn)
    srv.handle_message(a, {"type": "join", "username": "Alice"})
    srv.handle_message(b, {"type": "join", "username": "Bob"})
    c.sent.clear()
    srv.handle_message(c, {"type": "join", "username": "Eve"})
    errors = [m for m in c.sent if m["type"] == "error"]
    assert any(m["code"] == "LOBBY_FULL" for m in errors)


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


def test_human_cannot_select_a_bot_color():
    srv = Server()
    a = FakeConn("c1")
    srv.register_connection(a)
    srv.handle_message(a, {"type": "join", "username": "Alice"})
    a.sent.clear()
    srv.handle_message(a, {"type": "select_color", "color": "green"})  # color de Camila
    errors = [m for m in a.sent if m["type"] == "error"]
    assert any(m["code"] == "DUPLICATE_PLAYER" for m in errors)


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


def test_start_game_without_color_is_forbidden():
    """El host sin color asignado no puede iniciar (no hay humano con color)."""
    srv = Server()
    a = FakeConn("c1")
    srv.register_connection(a)
    srv.handle_message(a, {"type": "join", "username": "Alice"})
    a.sent.clear()
    srv.handle_message(a, {"type": "start_game"})
    errors = [m for m in a.sent if m["type"] == "error"]
    assert any(m["code"] == "FORBIDDEN" for m in errors)


def test_single_human_with_color_can_start():
    """1 humano con color + 2 bots: el host puede iniciar (partida de 3)."""
    srv, a = _start_game_1h(clear=False)
    assert srv.phase is ServerPhase.IN_GAME
    assert any(m["type"] == "game_started" for m in a.sent)


def test_start_game_by_host_transitions_to_in_game():
    srv, a, b = _start_game_2h(clear=False)
    assert srv.phase is ServerPhase.IN_GAME
    assert any(m["type"] == "game_started" for m in a.sent)
    assert any(m["type"] == "game_started" for m in b.sent)
    assert any(m["type"] == "state_update" for m in a.sent)


def test_server_binds_and_accepts_connection():
    srv = Server(host="127.0.0.1", port=0)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    srv.wait_ready(timeout=1.0)
    assert srv.port > 0
    sock = socket.create_connection(("127.0.0.1", srv.port), timeout=1.0)
    sock.close()
    time.sleep(0.1)
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


# ---------------------------------------------------------------------------
# Mecánica de juego (2 humanos + 2 bots)
# ---------------------------------------------------------------------------

def test_roll_initial_broadcasts():
    srv, a, b = _start_game_2h()
    srv.handle_message(a, {"type": "roll_initial"})
    assert any(m["type"] == "initial_roll" for m in a.sent)
    assert any(m["type"] == "initial_roll" for m in b.sent)
    assert any(m["type"] == "state_update" for m in a.sent)


def test_roll_dice_not_my_turn_is_rejected():
    srv, a, b = _start_game_2h()
    _play_to_active(srv, a, b)
    cur = _current_human(srv, (a, b))
    assert cur is not None, "el turno debería caer en un humano tras los bots"
    other = b if cur is a else a
    other.sent.clear()
    srv.handle_message(other, {"type": "roll_dice"})  # no es su turno
    assert any(m["type"] == "error" for m in other.sent)


def test_unknown_conn_sending_game_command_without_join_is_rejected():
    srv, a, b = _start_game_2h()
    ghost = FakeConn("ghost")
    srv.register_connection(ghost)
    srv.handle_message(ghost, {"type": "roll_dice"})
    assert any(m["type"] == "error" for m in ghost.sent)


def test_message_in_closed_phase_rejected():
    srv, a, b = _start_game_2h()
    srv.phase = ServerPhase.CLOSED  # Simulate game ended
    a.sent.clear()
    srv.handle_message(a, {"type": "roll_dice"})
    errors = [m for m in a.sent if m["type"] == "error"]
    assert any(m["code"] == "GAME_ENDED" for m in errors)


def test_unhandled_command_in_game_phase():
    """'join' está prohibido en fase IN_GAME."""
    srv, a, b = _start_game_2h()
    a.sent.clear()
    srv.handle_message(a, {"type": "join", "username": "Charlie"})
    errors = [m for m in a.sent if m["type"] == "error"]
    assert any(m["code"] == "FORBIDDEN" for m in errors)


def test_roll_dice_broadcasts_dice_result_and_state():
    srv, a, b = _start_game_2h()
    _play_to_active(srv, a, b)
    cur = _current_human(srv, (a, b))
    assert cur is not None
    a.sent.clear(); b.sent.clear()
    srv.handle_message(cur, {"type": "roll_dice"})
    assert any(m["type"] == "dice_result" for m in a.sent)
    assert any(m["type"] == "dice_result" for m in b.sent)
    assert any(m["type"] == "state_update" for m in a.sent)


def test_crown_piece_dispatch_path_reachable():
    srv, a, b = _start_game_2h()
    _play_to_active(srv, a, b)
    cur = _current_human(srv, (a, b))
    assert cur is not None
    cur.sent.clear()
    # No suele haber pieza coronable: basta con que el dispatch responda algo
    # (state_update o error) sin romper el servidor.
    srv.handle_message(cur, {"type": "crown_piece", "piece_index": 0})
    assert cur.sent


# ---------------------------------------------------------------------------
# Desconexiones
# ---------------------------------------------------------------------------

def test_disconnect_during_setup_auto_rolls_initial_so_setup_unblocks():
    """1 humano tira inicial y el otro se desconecta antes de tirar: el server
    tira por él para que el SETUP se resuelva y el juego avance."""
    srv, a, b = _start_game_2h()
    srv.handle_message(a, {"type": "roll_initial"})
    assert srv.session.game.phase.value == "setup", "Bob aún no tiró"
    a.sent.clear()
    srv._on_disconnect(b)
    # El juego continúa (1 humano + 2 bots) y el SETUP queda resuelto.
    assert srv.session is not None
    assert srv.session.game.phase.value == "rolling"
    assert len(srv.session.game.turn_order) == 4
    assert any(m["type"] == "state_update" for m in a.sent)


def test_disconnect_of_current_player_advances_turn_and_broadcasts():
    """Se desconecta el humano que tiene el turno: el cursor avanza a un jugador
    conectado y se rebroadcastea el estado."""
    srv, a, b = _start_game_2h()
    _play_to_active(srv, a, b)
    cur = _current_human(srv, (a, b))
    assert cur is not None
    other = b if cur is a else a
    other.sent.clear()
    srv._on_disconnect(cur)
    # El juego sigue (queda 1 humano + 2 bots) y el turno ya no es del que salió.
    assert srv.session is not None
    assert srv.session.current_turn_conn_id() != cur.conn_id
    assert any(m["type"] == "state_update" for m in other.sent)


def test_last_human_disconnect_resets_server_to_lobby():
    """Cuando el único humano de una partida se desconecta, el server vuelve a
    LOBBY (no quedan humanos; los bots no juegan solos sin nadie)."""
    srv, a = _start_game_1h()
    srv._on_disconnect(a)
    assert srv.phase is ServerPhase.LOBBY
    assert srv.session is None
    assert srv._connections == {}
    # Un cliente nuevo puede unirse y ser host en un lobby limpio.
    charlie = FakeConn("c3")
    srv.register_connection(charlie)
    srv.handle_message(charlie, {"type": "join", "username": "Charlie"})
    assert any(m["type"] == "welcome" and m["is_host"] for m in charlie.sent)


# ---------------------------------------------------------------------------
# Validación de mensajes
# ---------------------------------------------------------------------------

def test_invalid_color_in_select_color():
    srv = Server()
    a = FakeConn("c1")
    srv.register_connection(a)
    srv.handle_message(a, {"type": "join", "username": "Alice"})
    a.sent.clear()
    srv.handle_message(a, {"type": "select_color", "color": "neon_purple"})
    errors = [m for m in a.sent if m["type"] == "error"]
    assert any(m["code"] == "BAD_MESSAGE" for m in errors)


def test_leave_in_lobby():
    """Un humano sale del lobby; el otro ve la lista actualizada (1 humano + 2 bots)."""
    srv = Server()
    a, b = FakeConn("c1"), FakeConn("c2")
    srv.register_connection(a); srv.register_connection(b)
    srv.handle_message(a, {"type": "join", "username": "Alice"})
    srv.handle_message(b, {"type": "join", "username": "Bob"})
    a.sent.clear(); b.sent.clear()
    srv.handle_message(a, {"type": "leave"})
    assert "c1" not in srv._connections
    updates = [m for m in b.sent if m["type"] == "lobby_update"]
    assert updates
    humans = [p for p in updates[-1]["players"] if not p["is_bot"]]
    assert [p["username"] for p in humans] == ["Bob"]


def test_bad_protocol_message():
    srv = Server()
    a = FakeConn("c1")
    srv.register_connection(a)
    srv.handle_message(a, {"username": "Alice"})  # missing "type"
    errors = [m for m in a.sent if m["type"] == "error"]
    assert any(m["code"] == "BAD_MESSAGE" for m in errors)


def test_join_sends_welcome_to_first_player():
    srv = Server()
    a = FakeConn("c1")
    srv.register_connection(a)
    srv.handle_message(a, {"type": "join", "username": "First"})
    welcome = next(m for m in a.sent if m["type"] == "welcome")
    assert welcome["is_host"] is True
    assert welcome["username"] == "First"
