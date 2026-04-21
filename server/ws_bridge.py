"""WebSocket bridge: exposes the parques Server over WS for browser/mobile clients.

Runs an asyncio event loop in a dedicated thread with websockets.serve().
Each WS connection is wrapped in a WebSocketConnection adapter that exposes
the same interface as server.connection.ClientConnection, so the existing
Server._run_client_loop can handle both transport types identically.
"""
from __future__ import annotations

import asyncio
import logging
import queue
import threading

from server.server import Server

logger = logging.getLogger(__name__)


class WebSocketConnection:
    """Adapter that exposes ClientConnection's interface over a websockets connection.

    readline() / send() / close() are designed to be called from the synchronous
    _run_client_loop thread. The asyncio side (the websockets handler) pumps
    incoming frames into self._incoming via enqueue_frame(), and send() uses
    run_coroutine_threadsafe to schedule the outgoing write on the asyncio loop.
    """

    _EOF = None  # sentinel pushed into _incoming when the WS closes

    def __init__(
        self,
        ws,  # websockets.ServerConnection — typed as Any to avoid tight coupling
        loop: asyncio.AbstractEventLoop,
        *,
        conn_id: str,
    ) -> None:
        self.ws = ws
        self._loop = loop
        self.conn_id = conn_id
        self._incoming: queue.Queue = queue.Queue()

    # ---- pump side (asyncio thread) ----

    def enqueue_frame(self, frame: str) -> None:
        """Called from the asyncio handler when a WS text frame arrives."""
        self._incoming.put(frame.encode("utf-8"))

    def mark_closed(self) -> None:
        """Called from the asyncio handler when the WS closes."""
        self._incoming.put(self._EOF)

    # ---- sync side (client loop thread) ----

    def readline(self) -> bytes:
        """Block until the next frame or EOF. Returns bytes ending in '\\n'
        to match the ClientConnection contract. Returns b'' on EOF.
        """
        frame = self._incoming.get()
        if frame is self._EOF:
            return b""
        # Ensure newline for decode() compatibility (decode strips it again).
        if not frame.endswith(b"\n"):
            frame = frame + b"\n"
        return frame

    def send(self, data: bytes) -> None:
        """Send data as a WS text frame. Strips trailing newline."""
        text = data.rstrip(b"\n").decode("utf-8")
        # Schedule the send on the asyncio loop and wait for completion.
        future = asyncio.run_coroutine_threadsafe(self.ws.send(text), self._loop)
        future.result(timeout=5.0)

    def close(self) -> None:
        """Close the WS connection. Safe to call multiple times."""
        try:
            future = asyncio.run_coroutine_threadsafe(self.ws.close(), self._loop)
            future.result(timeout=2.0)
        except Exception:  # noqa: BLE001 — ya está cerrándose
            pass


import websockets  # noqa: E402


def start_ws_listener(
    server: Server,
    host: str,
    port: int,
) -> threading.Thread:
    """Spin up an asyncio loop in a thread and run websockets.serve().

    Sets server.ws_port to the bound port once listening. Returns the thread.
    """
    ready = threading.Event()

    async def _handler(ws) -> None:  # ws: websockets.ServerConnection
        # Prefer get_running_loop() inside coroutines (get_event_loop()
        # emits DeprecationWarning on 3.12+ when a loop is running).
        loop = asyncio.get_running_loop()
        conn_id = server._mint_conn_id()
        conn = WebSocketConnection(ws, loop, conn_id=conn_id)
        server.register_connection(conn)

        # Dispatch the sync client loop on a thread.
        loop_task = loop.run_in_executor(None, server._run_client_loop, conn)

        # Pump incoming frames into the adapter queue.
        try:
            async for frame in ws:
                if isinstance(frame, bytes):
                    frame = frame.decode("utf-8")
                conn.enqueue_frame(frame)
        except websockets.ConnectionClosed:
            pass
        finally:
            conn.mark_closed()

        await loop_task  # wait for the client loop thread to finish

    def _run() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def _main() -> None:
            async with websockets.serve(_handler, host, port) as srv_obj:
                # Grab the bound port if we passed 0.
                bound_port = srv_obj.sockets[0].getsockname()[1]
                server.ws_port = bound_port
                ready.set()
                logger.info("WS listener on %s:%d", host, bound_port)
                await asyncio.Future()  # run forever

        try:
            loop.run_until_complete(_main())
        except Exception as e:  # noqa: BLE001
            logger.exception("WS listener crashed: %s", e)
        finally:
            loop.close()

    thread = threading.Thread(target=_run, daemon=True, name="ws-listener")
    thread.start()
    ready.wait(timeout=2.0)
    return thread
