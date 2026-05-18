"""Shared fixtures for server tests."""
from __future__ import annotations

import json
import queue
import socket
import threading
import time

import pytest

from server.server import Server


def inline_bot_delay(_delay_seconds, cb):
    """Run a scheduled bot callback synchronously, no thread, no real delay.
    Makes integration tests with bots deterministic."""
    cb()
    return None  # No timer object; BotRunner._cancel_one tolerates None.


@pytest.fixture
def server_factory():
    """Spawn a Server in a daemon thread; cleanup on fixture teardown."""
    servers: list[Server] = []

    def _make(rng=None, bot_delay_fn=None) -> tuple[str, int]:
        srv = Server(
            host="127.0.0.1",
            port=0,
            rng=rng,
            bot_delay_fn=bot_delay_fn,
        )
        thread = threading.Thread(target=srv.serve_forever, daemon=True)
        thread.start()
        srv.wait_ready(timeout=2.0)
        servers.append(srv)
        return "127.0.0.1", srv.port

    yield _make

    for srv in servers:
        srv.shutdown()


class SocketClient:
    """A synchronous test client that reads/writes NDJSON over a TCP socket.

    Named `SocketClient` (not `TestClient`) so pytest does not try to collect
    it as a test class.
    """

    __test__ = False  # belt-and-suspenders against pytest collection

    def __init__(self, host: str, port: int):
        self.sock = socket.create_connection((host, port), timeout=2.0)
        self.sock.settimeout(2.0)
        self._recv_queue: queue.Queue[dict] = queue.Queue()
        self._alive = True
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()

    def _reader(self) -> None:
        buf = b""
        while self._alive:
            try:
                chunk = self.sock.recv(4096)
            except (socket.timeout, OSError):
                break
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                if line.strip():
                    try:
                        self._recv_queue.put(json.loads(line))
                    except json.JSONDecodeError:
                        pass

    def send(self, msg: dict) -> None:
        line = (json.dumps(msg) + "\n").encode("utf-8")
        self.sock.sendall(line)

    def recv(self, timeout: float = 1.0) -> dict:
        return self._recv_queue.get(timeout=timeout)

    def drain(self, expected_count: int | None = None, timeout: float = 1.0) -> list[dict]:
        """Collect currently-available (or up to N expected) messages."""
        msgs = []
        start = time.monotonic()
        while True:
            try:
                msgs.append(self._recv_queue.get(timeout=0.1))
            except queue.Empty:
                if expected_count is None:
                    return msgs
                if len(msgs) >= expected_count:
                    return msgs
                if time.monotonic() - start > timeout:
                    return msgs

    def close(self) -> None:
        self._alive = False
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.sock.close()


@pytest.fixture
def client_factory():
    """Factory that creates SocketClient instances; cleanup on fixture teardown."""
    clients: list[SocketClient] = []

    def _make(host: str, port: int) -> SocketClient:
        c = SocketClient(host, port)
        clients.append(c)
        return c

    yield _make

    for c in clients:
        c.close()
