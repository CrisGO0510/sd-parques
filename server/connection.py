"""ClientConnection: per-socket wrapper with line-buffered read."""
from __future__ import annotations

import socket
import threading


class ClientConnection:
    """Wraps a connected TCP socket.

    Provides readline() (blocks until a newline-terminated line or EOF is received)
    and send() (atomic sendall).
    """

    def __init__(self, sock: socket.socket, *, conn_id: str):
        self.sock = sock
        self.conn_id = conn_id
        self._buffer = b""
        self._send_lock = threading.Lock()

    def readline(self) -> bytes:
        """Return the next line (including \\n) or b"" on EOF.

        Raises whatever socket.recv raises on errors.
        """
        while b"\n" not in self._buffer:
            chunk = self.sock.recv(4096)
            if not chunk:
                # Clean EOF: return anything leftover in the buffer without a newline
                # as empty (we don't deliver incomplete lines — that'd be protocol bug).
                self._buffer = b""
                return b""
            self._buffer += chunk
        line, self._buffer = self._buffer.split(b"\n", 1)
        return line + b"\n"

    def send(self, data: bytes) -> None:
        """Atomically send all bytes. Thread-safe for concurrent emits."""
        with self._send_lock:
            self.sock.sendall(data)

    def close(self) -> None:
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.sock.close()
