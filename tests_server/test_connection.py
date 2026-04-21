import socket
import threading

import pytest

from server.connection import ClientConnection


def _pair():
    """Create a connected socket pair (server_side, client_side) via a listener."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    host, port = listener.getsockname()
    client = socket.create_connection((host, port))
    server_side, _ = listener.accept()
    listener.close()
    return server_side, client


def test_readline_returns_complete_message():
    server_side, client = _pair()
    try:
        conn = ClientConnection(server_side, conn_id="c1")
        client.sendall(b'{"type":"ping"}\n')
        line = conn.readline()
        assert line == b'{"type":"ping"}\n'
    finally:
        server_side.close()
        client.close()


def test_readline_handles_partial_then_complete():
    server_side, client = _pair()
    try:
        conn = ClientConnection(server_side, conn_id="c1")
        client.sendall(b'{"type":')
        client.sendall(b'"ping"}\n')
        line = conn.readline()
        assert line == b'{"type":"ping"}\n'
    finally:
        server_side.close()
        client.close()


def test_readline_handles_two_messages_in_one_chunk():
    server_side, client = _pair()
    try:
        conn = ClientConnection(server_side, conn_id="c1")
        client.sendall(b'{"type":"a"}\n{"type":"b"}\n')
        first = conn.readline()
        second = conn.readline()
        assert first == b'{"type":"a"}\n'
        assert second == b'{"type":"b"}\n'
    finally:
        server_side.close()
        client.close()


def test_readline_returns_empty_on_clean_close():
    server_side, client = _pair()
    try:
        conn = ClientConnection(server_side, conn_id="c1")
        client.close()
        line = conn.readline()
        assert line == b""
    finally:
        server_side.close()


def test_send_writes_full_message():
    server_side, client = _pair()
    try:
        conn = ClientConnection(server_side, conn_id="c1")
        conn.send(b'{"type":"welcome"}\n')
        received = client.recv(1024)
        assert received == b'{"type":"welcome"}\n'
    finally:
        server_side.close()
        client.close()
