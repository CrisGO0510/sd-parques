"""E2E tests for the WebSocket bridge."""
import asyncio
import socket
import threading

import pytest


@pytest.fixture
def event_loop_in_thread():
    """Start an asyncio loop in a daemon thread; yield (loop, stop_fn)."""
    loop = asyncio.new_event_loop()
    t = threading.Thread(target=loop.run_forever, daemon=True)
    t.start()

    def stop() -> None:
        loop.call_soon_threadsafe(loop.stop)
        t.join(timeout=1.0)

    try:
        yield loop, stop
    finally:
        if loop.is_running():
            stop()
        loop.close()


def test_websocket_connection_readline_and_send(event_loop_in_thread):
    """Adapter roundtrip: enqueue_frame → readline; send → MockWS captures."""
    from server.ws_bridge import WebSocketConnection

    class MockWS:
        def __init__(self) -> None:
            self.sent: list[str] = []

        async def send(self, msg: str) -> None:
            self.sent.append(msg)

        async def close(self) -> None:
            pass

    loop, _ = event_loop_in_thread
    ws = MockWS()
    conn = WebSocketConnection(ws, loop, conn_id="c1")

    # enqueue_frame pushes into the queue; readline returns it (with newline).
    conn.enqueue_frame('{"type":"join","username":"A"}')
    assert conn.readline() == b'{"type":"join","username":"A"}\n'

    # send schedules on the loop and writes to the mock.
    conn.send(b'{"type":"welcome"}\n')
    assert ws.sent == ['{"type":"welcome"}']

    # mark_closed followed by readline returns b''.
    conn.mark_closed()
    assert conn.readline() == b""


import json


@pytest.mark.asyncio
async def test_ws_client_can_join_lobby():
    """Start a Server with WS listener; a WS client joins and receives welcome."""
    import websockets

    from server.server import Server
    from server.ws_bridge import start_ws_listener

    srv = Server(host="127.0.0.1", port=0)  # TCP bound but we won't use it
    tcp_thread = threading.Thread(target=srv.serve_forever, daemon=True)
    tcp_thread.start()
    srv.wait_ready(timeout=2.0)

    # Start WS listener on its own port.
    start_ws_listener(srv, "127.0.0.1", 0)
    for _ in range(50):
        port = getattr(srv, "ws_port", None)
        if port:
            break
        await asyncio.sleep(0.02)
    assert port is not None, "ws_port never set"

    async with websockets.connect(f"ws://127.0.0.1:{port}") as ws:
        await ws.send(json.dumps({"type": "join", "username": "Alice"}))
        raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
        msg = json.loads(raw)
        assert msg["type"] == "welcome"
        assert msg["is_host"] is True

    srv.shutdown()

@pytest.mark.asyncio
async def test_ws_listener_responds_to_http_probe():
    """HTTP probes should get a clean 200 instead of a handshake error."""
    from server.server import Server
    from server.ws_bridge import start_ws_listener

    srv = Server(host="127.0.0.1", port=0)
    tcp_thread = threading.Thread(target=srv.serve_forever, daemon=True)
    tcp_thread.start()
    srv.wait_ready(timeout=2.0)

    start_ws_listener(srv, "127.0.0.1", 0)
    for _ in range(50):
        ws_port = getattr(srv, "ws_port", None)
        if ws_port:
            break
        await asyncio.sleep(0.02)
    assert ws_port is not None

    sock = socket.create_connection(("127.0.0.1", ws_port), timeout=2.0)
    try:
        sock.sendall(b"GET / HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")
        response = sock.recv(4096).decode("utf-8", errors="replace")
    finally:
        sock.close()
        srv.shutdown()

    assert "200 OK" in response
    assert "ok" in response.lower()

@pytest.mark.asyncio
async def test_tcp_and_ws_clients_share_lobby():
    """A TCP client and a WS client join; both see each other in lobby_update."""
    import socket
    import websockets

    from server.server import Server
    from server.ws_bridge import start_ws_listener

    srv = Server(host="127.0.0.1", port=0)
    tcp_thread = threading.Thread(target=srv.serve_forever, daemon=True)
    tcp_thread.start()
    srv.wait_ready(timeout=2.0)

    start_ws_listener(srv, "127.0.0.1", 0)
    for _ in range(50):
        ws_port = getattr(srv, "ws_port", None)
        if ws_port:
            break
        await asyncio.sleep(0.02)
    assert ws_port is not None

    # TCP client joins (sync, so run on a thread to not block the asyncio loop).
    # tcp_joined: set once TcpAlice has received her welcome (she's in the lobby).
    # tcp_done:   set by the test to let TcpAlice's thread know it may close.
    tcp_joined = threading.Event()
    tcp_done = threading.Event()

    def tcp_join() -> list[str]:
        sock = socket.create_connection(("127.0.0.1", srv.port), timeout=2.0)
        sock.sendall(b'{"type":"join","username":"TcpAlice"}\n')
        buf = b""
        received = []
        sock.settimeout(0.2)  # short timeout so we can check tcp_done frequently
        # Read until the test signals done.
        while not tcp_done.is_set():
            try:
                chunk = sock.recv(4096)
            except socket.timeout:
                continue  # check tcp_done again
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                if line:
                    received.append(line.decode("utf-8"))
                    if not tcp_joined.is_set():
                        tcp_joined.set()  # TcpAlice is now in the lobby
        sock.close()
        return received

    tcp_msgs_future = asyncio.get_running_loop().run_in_executor(None, tcp_join)

    # Wait until TcpAlice's welcome has been received (she's registered in lobby).
    await asyncio.get_running_loop().run_in_executor(
        None, lambda: tcp_joined.wait(timeout=2.0)
    )
    assert tcp_joined.is_set(), "TCP client never received welcome"

    # WS client joins.
    async with websockets.connect(f"ws://127.0.0.1:{ws_port}") as ws:
        await ws.send(json.dumps({"type": "join", "username": "WsBob"}))
        ws_welcome = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
        assert ws_welcome["type"] == "welcome"
        assert ws_welcome["is_host"] is False  # TcpAlice is host

        # Expect lobby_update containing both.
        lobby_msg = None
        for _ in range(5):
            raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
            parsed = json.loads(raw)
            if parsed["type"] == "lobby_update":
                lobby_msg = parsed
                break
        assert lobby_msg is not None
        usernames = {p["username"] for p in lobby_msg["players"]}
        assert "TcpAlice" in usernames and "WsBob" in usernames

    # Signal TcpAlice's thread to close and collect its messages.
    tcp_done.set()
    tcp_msgs = await tcp_msgs_future
    assert any("TcpAlice" in m for m in tcp_msgs)

    srv.shutdown()
