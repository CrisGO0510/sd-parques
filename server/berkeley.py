"""Algoritmo de Berkeley para sincronización de relojes.

El servidor actúa como maestro:
1. Manda time_request a todos los clientes con su timestamp actual.
2. Los clientes responden con su timestamp local (time_response).
3. El servidor calcula el promedio de diferencias y manda time_adjust
   a cada cliente con el ajuste en milisegundos que debe aplicar.
"""
from __future__ import annotations

import logging
import time
import threading
from typing import Any, Callable

logger = logging.getLogger(__name__)


class BerkeleySync:
    def __init__(
        self,
        get_connections: Callable[[], dict[str, Any]],
        send_fn: Callable[[Any, bytes], None],
        encode_fn: Callable[[dict], bytes],
        timeout: float = 3.0,
    ) -> None:
        self._get_connections = get_connections
        self._send = send_fn
        self._encode = encode_fn
        self._timeout = timeout
        self._pending: dict[str, float] = {}   # conn_id → tiempo de envío
        self._responses: dict[str, int] = {}   # conn_id → timestamp cliente (ms)
        self._lock = threading.Lock()
        self._done = threading.Event()

    def run(self) -> None:
        """Ejecuta una ronda de sincronización Berkeley."""
        connections = self._get_connections()
        if not connections:
            return

        server_time_ms = int(time.time() * 1000)
        conn_ids = list(connections.keys())

        with self._lock:
            self._pending = {cid: time.monotonic() for cid in conn_ids}
            self._responses = {}
            self._done.clear()

        # Pedir timestamp a todos los clientes
        for conn_id, conn in connections.items():
            try:
                self._send(conn, self._encode({
                    "type": "time_request",
                    "server_time": server_time_ms,
                }))
            except Exception as e:
                logger.warning("berkeley: error sending time_request to %s: %s", conn_id, e)
                with self._lock:
                    self._pending.pop(conn_id, None)

        # Esperar respuestas con timeout
        self._done.wait(timeout=self._timeout)

        with self._lock:
            responses = dict(self._responses)

        if not responses:
            logger.warning("berkeley: no responses received")
            return

        # Calcular diferencias respecto al servidor
        diffs = []
        for conn_id, client_time_ms in responses.items():
            diff = server_time_ms - client_time_ms
            diffs.append(diff)

        avg_diff = sum(diffs) // len(diffs)
        logger.info("berkeley: %d responses, avg_diff=%dms", len(responses), avg_diff)

        # Mandar ajuste individual a cada cliente
        connections = self._get_connections()
        for conn_id, client_time_ms in responses.items():
            conn = connections.get(conn_id)
            if conn is None:
                continue
            # Ajuste = lo que debe sumar el cliente para acercarse al promedio
            adjust_ms = avg_diff - (server_time_ms - client_time_ms)
            try:
                self._send(conn, self._encode({
                    "type": "time_adjust",
                    "adjust_ms": adjust_ms,
                }))
                logger.debug("berkeley: conn=%s adjust=%dms", conn_id, adjust_ms)
            except Exception as e:
                logger.warning("berkeley: error sending time_adjust to %s: %s", conn_id, e)

    def handle_response(self, conn_id: str, client_time_ms: int) -> None:
        """Llamar cuando llega un time_response de un cliente."""
        with self._lock:
            if conn_id not in self._pending:
                return
            self._responses[conn_id] = client_time_ms
            self._pending.pop(conn_id)
            if not self._pending:
                self._done.set()