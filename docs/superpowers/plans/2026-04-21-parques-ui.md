# Parqués UI (Quasar + Android) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **IMPORTANT — User owns git.** The user manages all git operations. Subagents must not run `git add`, `git commit`, `git branch`, `git checkout`, `git push`, or any mutating git command. Where this plan says "Commit", replace with "Report the diff to the controller". Only read-only git commands (`git status`, `git diff`, `git log`) are allowed.

**Goal:** Implementar el cliente gráfico Quasar + Vue 3 + TypeScript estricto + Pinia + Capacitor Android, consumiendo el servidor del módulo #2 vía un WebSocket bridge añadido al mismo proceso Python. Al final, dos clientes (browser o APK Android) pueden jugar una partida completa de Parqués.

**Architecture:** El servidor existente acepta un listener WebSocket adicional (asyncio en un thread dedicado, `server/ws_bridge.py`); el cliente Quasar se conecta por WS y consume el mismo protocolo NDJSON. Tipos compartidos como discriminated unions con enums en `client/src/types/`. 3 stores Pinia (connection, lobby, game), 4 pantallas (connect, lobby, game, end), tablero SVG con 96 casillas y animación CSS de movimiento. APK Android via Capacitor desde el inicio.

**Tech Stack:** Python 3.11 + `websockets>=13` (nuevo). Node/TS: Quasar v2 + Vue 3 + `<script setup lang="ts">` + Pinia + Vue Router + Vitest + Capacitor + Android SDK.

**Spec:** `docs/superpowers/specs/2026-04-21-parques-ui-design.md`

**Convenciones (persistentes, en memoria del proyecto):**
- **Sin magic strings:** todo string simbólico va en enum o `as const`. ESLint lo obliga.
- **TypeScript estricto** (`strict: true`, `noImplicitAny`). `any` solo con comentario justificativo.
- **Identificadores y nombres de archivos en inglés**, docs en español.
- **Snake_case en DTOs** (coincide con el wire del servidor Python).

---

## File Structure

### Cambios en Python (`server/`)

| Archivo | Cambio |
|---|---|
| `server/ws_bridge.py` | **Nuevo.** `WebSocketConnection` adapter + `start_ws_listener(server, host, port)`. |
| `server/__main__.py` | **Modificar.** Nuevos flags `--port-ws`, `--no-ws`; arranca el bridge tras bind del TCP. |
| `pyproject.toml` | **Modificar.** Añadir `websockets>=13` como optional dep `ws`. |
| `tests_server/test_ws_bridge.py` | **Nuevo.** E2E: un cliente TCP + un cliente WS juegan el handshake del lobby. |

### Cliente TypeScript (`client/`)

```
client/
├── src/
│   ├── boot/pinia.ts
│   ├── components/
│   │   ├── BoardCanvas.vue
│   │   ├── DiceRoller.vue
│   │   ├── PlayerList.vue
│   │   ├── PieceToken.vue
│   │   └── TurnBanner.vue
│   ├── composables/
│   │   ├── useServerProtocol.ts
│   │   └── useBoardGeometry.ts
│   ├── css/app.scss
│   ├── layouts/MainLayout.vue
│   ├── pages/
│   │   ├── ConnectPage.vue
│   │   ├── LobbyPage.vue
│   │   ├── GamePage.vue
│   │   └── EndPage.vue
│   ├── router/
│   │   ├── index.ts
│   │   └── routes.ts
│   ├── stores/
│   │   ├── connection.ts
│   │   ├── lobby.ts
│   │   └── game.ts
│   ├── test-utils/
│   │   ├── factories.ts
│   │   └── mockWebSocket.ts
│   └── types/
│       ├── domain.ts
│       └── protocol.ts
├── src-capacitor/android/         # generado por Capacitor
├── public/
├── index.html
├── quasar.config.ts
├── tsconfig.json                  # strict: true
├── package.json
├── .eslintrc.cjs
└── vitest.config.ts
```

**Responsabilidades (una por archivo):**

| Archivo | Responsabilidad |
|---|---|
| `src/types/domain.ts` | Enums y DTOs del dominio (Color, PieceState, GamePhase, MoveAction, PieceDto, GameStateDto, ...). Sin lógica. |
| `src/types/protocol.ts` | Enums del protocolo + discriminated unions (ClientCommand, ServerEvent). Sin lógica. |
| `src/stores/connection.ts` | WebSocket instance + credenciales + status enum. |
| `src/stores/lobby.ts` | Estado del lobby (players, availableColors, isHost, myColor). |
| `src/stores/game.ts` | Snapshot del Game + availableMoves + winner. |
| `src/composables/useServerProtocol.ts` | Convenience API para declarar handlers tipados por evento. |
| `src/composables/useBoardGeometry.ts` | Funciones puras: position → (x, y) en el viewBox SVG. |
| `src/components/BoardCanvas.vue` | SVG con circuito + cárceles + rectas finales + meta. Orquesta las fichas. |
| `src/components/PieceToken.vue` | Un `<circle>` para una ficha con glow si es selectable. |
| `src/components/DiceRoller.vue` | Muestra 2 dados con animación de roll. |
| `src/components/PlayerList.vue` | Lista de jugadores con avatar + nombre + progreso. |
| `src/components/TurnBanner.vue` | Banner superior con texto "Tu turno" / "Turno de X". |
| `src/router/routes.ts` | Enum `Route` + lista de rutas + `meta.requiresConnection`. |
| `src/router/index.ts` | Crea el router + registra guards. |
| `src/layouts/MainLayout.vue` | `q-layout` con header, page container, drawer/bottom sheet según breakpoint. |
| `src/pages/*.vue` | Una página por ruta; orquesta stores + composables + componentes. |

---

## Task 1: WS bridge — dependencia y scaffold

**Files:**
- Modify: `pyproject.toml`
- Create: `server/ws_bridge.py` (stub)
- Create: `tests_server/test_ws_bridge.py` (stub)

- [ ] **Step 1: Añadir `websockets` a `pyproject.toml`**

Cambiar `[project.optional-dependencies]`:

```toml
[project.optional-dependencies]
dev = ["pytest>=8.0"]
ws  = ["websockets>=13"]
```

- [ ] **Step 2: Reinstalar con el extra ws**

```bash
.venv/bin/pip install -e '.[dev,ws]' -q
```

Verify: `.venv/bin/python -c "import websockets; print(websockets.__version__)"` imprime >=13.

- [ ] **Step 3: Crear `server/ws_bridge.py` con docstring + imports**

```python
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
```

- [ ] **Step 4: Crear `tests_server/test_ws_bridge.py` con stub**

```python
"""E2E tests for the WebSocket bridge."""
import pytest
```

- [ ] **Step 5: Verify no regression**

```bash
.venv/bin/pytest -q
```

Expected: `133 passed` (still).

- [ ] **Step 6: Report diff (user commits)**

---

## Task 2: `WebSocketConnection` adapter

**Files:**
- Modify: `server/ws_bridge.py`
- Modify: `tests_server/test_ws_bridge.py`

**Contrato:** `WebSocketConnection` debe exponer la misma interfaz pública que `server.connection.ClientConnection` (el `Server` ya la usa sin distinguir tipo):

- `conn_id: str` attribute.
- `readline() -> bytes` — bloqueante en el thread del `_run_client_loop`; pops de una `queue.Queue` alimentada por la corrutina asyncio que lee frames WS.
- `send(data: bytes) -> None` — atómico; envía frame WS de texto; threadsafe usando `run_coroutine_threadsafe`.
- `close() -> None`.

- [ ] **Step 1: Tests (sin sockets reales, mockear el WS)**

Añadir a `tests_server/test_ws_bridge.py`:

```python
import asyncio
import threading
import pytest


def test_websocket_connection_exposes_readline_and_send():
    # Dada una clase ficticia que simula un WS de websockets,
    # WebSocketConnection debe exponer readline()/send()/close() como ClientConnection.
    from server.ws_bridge import WebSocketConnection
    # El test real usa un MockWS inline; verify that send pushes a text frame
    # and readline pops from the adapter's queue.
    pass  # implementado en el Step 3
```

Por ahora el test es stub (tendremos uno real en Task 5 con E2E real).

- [ ] **Step 2: Implementar `WebSocketConnection`**

Añadir a `server/ws_bridge.py`:

```python
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
```

- [ ] **Step 3: Unit test interno (sin websockets real)**

Sustituir el stub por:

```python
def test_websocket_connection_readline_and_send(event_loop_in_thread):
    """Spawn an asyncio loop in a thread; verify adapter roundtrip."""
    from server.ws_bridge import WebSocketConnection

    class MockWS:
        def __init__(self) -> None:
            self.sent: list[str] = []

        async def send(self, msg: str) -> None:
            self.sent.append(msg)

        async def close(self) -> None:
            pass

    loop, stop_loop = event_loop_in_thread
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

    stop_loop()
```

Añadir fixture al mismo archivo:

```python
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
```

- [ ] **Step 4: Run test**

```bash
.venv/bin/pytest tests_server/test_ws_bridge.py -v
```

Expected: 1 passed.

Full suite: `134 passed`.

- [ ] **Step 5: Report diff**

---

## Task 3: `start_ws_listener` (asyncio en thread)

**Files:**
- Modify: `server/ws_bridge.py`
- Modify: `tests_server/test_ws_bridge.py`

**Contrato:** `start_ws_listener(server: Server, host: str, port: int) -> threading.Thread`:

1. Crea un event loop asyncio en un thread daemon.
2. Llama `websockets.serve(handler, host, port)` donde `handler` (corrutina):
   - Mint a `conn_id` via `server._mint_conn_id()`.
   - Crea `WebSocketConnection(ws, loop, conn_id=conn_id)`.
   - Llama `server.register_connection(conn)`.
   - Dispara `server._run_client_loop(conn)` en un executor (thread separado) → no bloquea el event loop.
   - En paralelo, un `async for frame in ws: conn.enqueue_frame(frame)` alimenta el queue.
   - Al cerrar el WS (natural o por error): `conn.mark_closed()` para que `readline()` en el client loop retorne `b""` y termine.

- [ ] **Step 1: Tests E2E mínimos (server + browser-like WS client)**

Añadir a `tests_server/test_ws_bridge.py`:

```python
import asyncio
import json

import pytest


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
    ws_thread = start_ws_listener(srv, "127.0.0.1", 0)
    # The WS thread exposes its bound port via an event on Server.
    # Implementation detail: we'll add srv.ws_port attribute set by start_ws_listener.
    # For now, poll until it's set or give up.
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
```

Nota: esto requiere instalar `pytest-asyncio`. Añadir a `[project.optional-dependencies]`:

```toml
dev = ["pytest>=8.0", "pytest-asyncio>=0.23"]
```

Y `pyproject.toml` → `[tool.pytest.ini_options]`:

```toml
asyncio_mode = "auto"
```

- [ ] **Step 2: Fail**

```bash
.venv/bin/pip install -e '.[dev,ws]' -q
.venv/bin/pytest tests_server/test_ws_bridge.py -v
```

Expected: test fails (no `start_ws_listener`).

- [ ] **Step 3: Implementar `start_ws_listener`**

Añadir a `server/ws_bridge.py`:

```python
import websockets
from server.server import Server


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
```

- [ ] **Step 4: Pass**

```bash
.venv/bin/pytest tests_server/test_ws_bridge.py -v
```

Expected: 2 passed. Full suite: `135 passed`.

- [ ] **Step 5: Report diff**

---

## Task 4: Integrar el bridge en `__main__.py`

**Files:**
- Modify: `server/__main__.py`

- [ ] **Step 1: Actualizar CLI con nuevos flags**

Reemplazar el contenido de `server/__main__.py`:

```python
"""Entry point: `python -m server`."""
from __future__ import annotations

import argparse
import logging
import sys

from server.server import Server


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port-tcp", type=int, default=5000, dest="port_tcp")
    parser.add_argument("--port-ws",  type=int, default=5001, dest="port_ws",
                        help="WebSocket listener port (0 disables)")
    parser.add_argument("--no-ws",    action="store_true",
                        help="Disable the WebSocket listener entirely")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s",
    )

    server = Server(host=args.host, port=args.port_tcp)

    # Start WS listener if requested (must be before serve_forever which blocks).
    if not args.no_ws and args.port_ws:
        import threading

        from server.ws_bridge import start_ws_listener

        # serve_forever blocks — we start TCP in a thread, then WS in another,
        # then main just waits for Ctrl+C.
        tcp_thread = threading.Thread(
            target=server.serve_forever, daemon=True, name="tcp-listener",
        )
        tcp_thread.start()
        server.wait_ready(timeout=2.0)

        start_ws_listener(server, args.host, args.port_ws)

        try:
            tcp_thread.join()
        except KeyboardInterrupt:
            logging.info("shutdown requested")
            server.shutdown()
        return 0

    # No WS: use the existing flow.
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("shutdown requested")
        server.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Smoke manual**

```bash
timeout 1 .venv/bin/python -m server --port-tcp 0 --port-ws 0 --log-level DEBUG 2>&1 | head -5 || true
```

Expected: deberías ver dos líneas `listening on 0.0.0.0:<port>` — una del TCP y otra del WS listener.

- [ ] **Step 3: Verify no regression**

```bash
.venv/bin/pytest -q
```

Expected: `135 passed`.

- [ ] **Step 4: Report diff**

---

## Task 5: Test E2E mixto (TCP + WS conviven)

**Files:**
- Modify: `tests_server/test_ws_bridge.py`

- [ ] **Step 1: Test**

```python
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
    def tcp_join() -> list[str]:
        sock = socket.create_connection(("127.0.0.1", srv.port), timeout=2.0)
        sock.sendall(b'{"type":"join","username":"TcpAlice"}\n')
        buf = b""
        received = []
        sock.settimeout(1.0)
        while len(received) < 2:
            chunk = sock.recv(4096)
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                if line:
                    received.append(line.decode("utf-8"))
        sock.close()
        return received

    tcp_msgs_future = asyncio.get_event_loop().run_in_executor(None, tcp_join)

    # Give the TCP side a moment to register.
    await asyncio.sleep(0.2)

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

    # Collect TCP messages.
    tcp_msgs = await tcp_msgs_future
    assert any("TcpAlice" in m for m in tcp_msgs)

    srv.shutdown()
```

- [ ] **Step 2: Pass**

```bash
.venv/bin/pytest tests_server/test_ws_bridge.py -v
```

Expected: 3 passed.

Full suite: `136 passed` total.

- [ ] **Step 3: Report diff**

---

## Task 6: Scaffold del cliente Quasar

**Files:**
- Create: todo el proyecto `client/` via `quasar create`

- [ ] **Step 1: Generar el proyecto con create-quasar**

```bash
cd /home/cris/Documents/sistemas-distribuidos/sd-parques
npx -y create-quasar client --branch next
```

Responder al wizard:
- Project name: `parques-client` (o dejar default)
- Meta info del package: valores razonables
- Target browsers: default (modern)
- **CSS preprocessor: `Sass with indented syntax`** (o simple SCSS)
- **Add Quasar UI package? Yes**
- **TypeScript? YES** ← clave
- **Router mode: Vue Router 4**
- Add Pinia for state management? Yes
- **State management: Pinia**
- Add Prettier for code formatting? **No** (usamos solo ESLint)
- Lint feature? **ESLint with `@typescript-eslint`**
- Install dependencies? Yes, with npm

Esto crea `client/` con toda la estructura estándar.

- [ ] **Step 2: Verify que el smoke corre**

```bash
cd client
npm run dev
# Esperar a que diga "App running on http://localhost:9000"
# Abrir el browser, verificar que se ve la welcome page
# Ctrl+C
```

- [ ] **Step 3: Report diff** (el `client/` completo es untracked)

---

## Task 7: TypeScript strict, ESLint, Vitest config

**Files:**
- Modify: `client/tsconfig.json`
- Modify: `client/.eslintrc.cjs`
- Create: `client/vitest.config.ts`
- Modify: `client/package.json` (scripts + devDeps)

- [ ] **Step 1: `tsconfig.json` estricto**

Reemplazar `client/tsconfig.json`:

```json
{
  "extends": "@quasar/app-vite/tsconfig-preset",
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "strictBindCallApply": true,
    "noImplicitThis": true,
    "alwaysStrict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "src/*": ["src/*"],
      "app/*": ["*"],
      "components/*": ["src/components/*"],
      "layouts/*": ["src/layouts/*"],
      "pages/*": ["src/pages/*"],
      "stores/*": ["src/stores/*"],
      "boot/*": ["src/boot/*"]
    }
  }
}
```

- [ ] **Step 2: ESLint estricto anti-any y anti magic strings**

Reemplazar `client/.eslintrc.cjs`:

```js
/* eslint-env node */
module.exports = {
  root: true,
  parser: 'vue-eslint-parser',
  parserOptions: {
    parser: '@typescript-eslint/parser',
    ecmaVersion: 'latest',
    sourceType: 'module',
  },
  env: { browser: true, node: true },
  extends: [
    'plugin:@typescript-eslint/recommended',
    'plugin:vue/vue3-recommended',
  ],
  plugins: ['@typescript-eslint', 'vue'],
  rules: {
    '@typescript-eslint/no-explicit-any': 'error',
    '@typescript-eslint/explicit-function-return-type': ['warn', {
      allowExpressions: true,
      allowTypedFunctionExpressions: true,
    }],
    '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
    'vue/multi-word-component-names': 'off',
    'no-console': ['warn', { allow: ['warn', 'error'] }],
  },
};
```

- [ ] **Step 3: Vitest config**

Crear `client/vitest.config.ts`:

```ts
import { defineConfig } from 'vitest/config';
import vue from '@vitejs/plugin-vue';
import { fileURLToPath } from 'node:url';

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      src: fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    environment: 'happy-dom',
    globals: true,
    coverage: {
      provider: 'v8',
      include: ['src/stores/**', 'src/composables/**'],
      reporter: ['text', 'html'],
    },
  },
});
```

Instalar dependencias:

```bash
cd client
npm install -D vitest @vue/test-utils happy-dom @vitest/coverage-v8
```

- [ ] **Step 4: Scripts en `package.json`**

Añadir a `client/package.json` → `"scripts"`:

```json
{
  "scripts": {
    "dev":            "quasar dev",
    "build":          "quasar build",
    "build:android":  "quasar build -m capacitor -T android",
    "test":           "vitest run",
    "test:watch":     "vitest",
    "test:coverage":  "vitest run --coverage",
    "lint":           "eslint . --ext .ts,.vue",
    "typecheck":      "vue-tsc --noEmit"
  }
}
```

Instalar `vue-tsc`:

```bash
npm install -D vue-tsc
```

- [ ] **Step 5: Verify**

```bash
cd client
npm run lint           # should pass
npm run typecheck      # should pass
npm run test           # 0 tests — but vitest should run clean
```

Expected: los tres pasan sin errores.

- [ ] **Step 6: Report diff**

---

## Task 8: `types/domain.ts` + `types/protocol.ts`

**Files:**
- Create: `client/src/types/domain.ts`
- Create: `client/src/types/protocol.ts`

- [ ] **Step 1: `src/types/domain.ts` — enums y DTOs del dominio**

```ts
// Los valores string deben coincidir EXACTAMENTE con core/entities.py
export enum Color {
  RED    = 'red',
  BLUE   = 'blue',
  GREEN  = 'green',
  YELLOW = 'yellow',
}

export enum PieceState {
  IN_JAIL          = 'in_jail',
  ON_BOARD         = 'on_board',
  IN_HOME_STRETCH  = 'in_home_stretch',
  CROWNED          = 'crowned',
}

export enum GamePhase {
  SETUP    = 'setup',
  ROLLING  = 'rolling',
  MOVING   = 'moving',
  CROWNING = 'crowning',
  FINISHED = 'finished',
}

export enum MoveAction {
  EXIT_JAIL           = 'exit_jail',
  ADVANCE             = 'advance',
  CAPTURE             = 'capture',
  ENTER_HOME_STRETCH  = 'enter_home_stretch',
  REACH_GOAL          = 'reach_goal',
}

export interface PieceDto {
  index: number;
  state: PieceState;
  circuit_position: number | null;
  home_stretch_position: number | null;
}

export interface PlayerDto {
  name: string;
  color: Color;
  pieces: PieceDto[];
}

export interface GameStateDto {
  players: PlayerDto[];
  phase: GamePhase;
  turn_order: number[];
  current_turn_index: number;
  pending_dice: number[];
  initial_rolls: Record<string, number>;
  initial_rolls_remaining: number;
  consecutive_pairs: number;
  winner: number | null;
}

export interface MoveDto {
  piece_index: number;
  dice_value: number;
  action: MoveAction;
}

export interface MoveResultDto {
  action: MoveAction;
  reached_goal: boolean;
  captured: PieceDto | null;
}

export interface LobbyPlayerDto {
  username: string;
  color: Color | null;
}
```

- [ ] **Step 2: `src/types/protocol.ts` — enums + discriminated unions**

```ts
import type {
  Color,
  GameStateDto,
  LobbyPlayerDto,
  MoveDto,
  MoveResultDto,
} from './domain';

export enum ClientCommandType {
  JOIN          = 'join',
  SELECT_COLOR  = 'select_color',
  START_GAME    = 'start_game',
  ROLL_INITIAL  = 'roll_initial',
  ROLL_DICE     = 'roll_dice',
  MOVE_PIECE    = 'move_piece',
  SKIP_TURN     = 'skip_turn',
  CROWN_PIECE   = 'crown_piece',
  LEAVE         = 'leave',
}

export enum ServerEventType {
  WELCOME          = 'welcome',
  LOBBY_UPDATE     = 'lobby_update',
  GAME_STARTED     = 'game_started',
  STATE_UPDATE     = 'state_update',
  INITIAL_ROLL     = 'initial_roll',
  DICE_RESULT      = 'dice_result',
  AVAILABLE_MOVES  = 'available_moves',
  MOVE_APPLIED     = 'move_applied',
  GAME_OVER        = 'game_over',
  ERROR            = 'error',
}

export enum ErrorCode {
  BAD_MESSAGE       = 'BAD_MESSAGE',
  NOT_AUTHENTICATED = 'NOT_AUTHENTICATED',
  DUPLICATE_PLAYER  = 'DUPLICATE_PLAYER',
  WRONG_PHASE       = 'WRONG_PHASE',
  INVALID_MOVE      = 'INVALID_MOVE',
  FORBIDDEN         = 'FORBIDDEN',
  GAME_ENDED        = 'GAME_ENDED',
}

import type { MoveAction } from './domain';

export type ClientCommand =
  | { type: ClientCommandType.JOIN;         username: string }
  | { type: ClientCommandType.SELECT_COLOR; color: Color }
  | { type: ClientCommandType.START_GAME }
  | { type: ClientCommandType.ROLL_INITIAL }
  | { type: ClientCommandType.ROLL_DICE }
  | { type: ClientCommandType.MOVE_PIECE;   piece_index: number; dice_value: number; action: MoveAction }
  | { type: ClientCommandType.SKIP_TURN }
  | { type: ClientCommandType.CROWN_PIECE;  piece_index: number }
  | { type: ClientCommandType.LEAVE };

export type ServerEvent =
  | { type: ServerEventType.WELCOME;          username: string; is_host: boolean }
  | { type: ServerEventType.LOBBY_UPDATE;     players: LobbyPlayerDto[]; available_colors: Color[] }
  | { type: ServerEventType.GAME_STARTED }
  | { type: ServerEventType.STATE_UPDATE;     state: GameStateDto }
  | { type: ServerEventType.INITIAL_ROLL;     player_index: number; username: string; total: number }
  | { type: ServerEventType.DICE_RESULT;      player_index: number; d1: number; d2: number; is_pair: boolean }
  | { type: ServerEventType.AVAILABLE_MOVES;  moves: MoveDto[] }
  | { type: ServerEventType.MOVE_APPLIED;     move: MoveDto; result: MoveResultDto }
  | { type: ServerEventType.GAME_OVER;        winner_index: number | null; winner_username: string | null }
  | { type: ServerEventType.ERROR;            code: ErrorCode; message: string };

export function assertNever(x: never): never {
  throw new Error(`unexpected value in exhaustive switch: ${JSON.stringify(x)}`);
}
```

- [ ] **Step 3: Verify**

```bash
cd client
npm run typecheck
```

Expected: pasa sin errores.

- [ ] **Step 4: Report diff**

---

## Task 9: `connectionStore`

**Files:**
- Create: `client/src/stores/connection.ts`
- Create: `client/src/stores/connection.test.ts`

- [ ] **Step 1: Tests (mock de WebSocket global)**

Crear `client/src/test-utils/mockWebSocket.ts`:

```ts
export enum MockWSState {
  CONNECTING = 0,
  OPEN       = 1,
  CLOSING    = 2,
  CLOSED     = 3,
}

export class MockWebSocket {
  readyState: MockWSState = MockWSState.CONNECTING;
  onopen:    (() => void) | null = null;
  onclose:   (() => void) | null = null;
  onerror:   ((e: unknown) => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  sent: string[] = [];

  constructor(public url: string) { /* defer open */ }

  // Test helpers — NOT part of the real WebSocket API
  simulateOpen(): void {
    this.readyState = MockWSState.OPEN;
    this.onopen?.();
  }

  simulateMessage(data: string): void {
    this.onmessage?.({ data });
  }

  simulateClose(): void {
    this.readyState = MockWSState.CLOSED;
    this.onclose?.();
  }

  send(data: string): void {
    this.sent.push(data);
  }

  close(): void {
    this.readyState = MockWSState.CLOSED;
    this.onclose?.();
  }
}

export function installMockWebSocket(): { restore: () => void; instances: MockWebSocket[] } {
  const originalWS = globalThis.WebSocket;
  const instances: MockWebSocket[] = [];
  class TrackedMock extends MockWebSocket {
    constructor(url: string) {
      super(url);
      instances.push(this);
    }
  }
  (globalThis as unknown as { WebSocket: typeof WebSocket }).WebSocket = TrackedMock as unknown as typeof WebSocket;
  return {
    restore: () => { (globalThis as unknown as { WebSocket: typeof WebSocket }).WebSocket = originalWS; },
    instances,
  };
}
```

Crear `client/src/stores/connection.test.ts`:

```ts
import { setActivePinia, createPinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { ConnectionStatus, useConnectionStore } from './connection';
import { ClientCommandType, ServerEventType } from 'src/types/protocol';
import { installMockWebSocket, MockWebSocket } from 'src/test-utils/mockWebSocket';

describe('connectionStore', () => {
  let mock: { restore: () => void; instances: MockWebSocket[] };

  beforeEach(() => {
    setActivePinia(createPinia());
    mock = installMockWebSocket();
  });

  afterEach(() => mock.restore());

  it('starts disconnected', () => {
    const store = useConnectionStore();
    expect(store.status).toBe(ConnectionStatus.DISCONNECTED);
  });

  it('connect() sets status to CONNECTED after onopen', async () => {
    const store = useConnectionStore();
    const promise = store.connect('localhost', 5001, 'Alice');
    const ws = mock.instances[0]!;
    ws.simulateOpen();
    await promise;
    expect(store.status).toBe(ConnectionStatus.CONNECTED);
    expect(store.host).toBe('localhost');
    expect(store.port).toBe(5001);
    expect(store.username).toBe('Alice');
  });

  it('send() writes serialized JSON to the socket', async () => {
    const store = useConnectionStore();
    const promise = store.connect('localhost', 5001, 'Alice');
    mock.instances[0]!.simulateOpen();
    await promise;
    store.send({ type: ClientCommandType.JOIN, username: 'Alice' });
    expect(mock.instances[0]!.sent).toEqual(['{"type":"join","username":"Alice"}']);
  });

  it('onEvent() fires for incoming messages', async () => {
    const store = useConnectionStore();
    const promise = store.connect('localhost', 5001, 'Alice');
    mock.instances[0]!.simulateOpen();
    await promise;

    let received: unknown = null;
    store.onEvent((e) => { received = e; });
    mock.instances[0]!.simulateMessage('{"type":"welcome","username":"Alice","is_host":true}');
    expect(received).toEqual({
      type: ServerEventType.WELCOME,
      username: 'Alice',
      is_host: true,
    });
  });

  it('disconnect() transitions back to DISCONNECTED', async () => {
    const store = useConnectionStore();
    const promise = store.connect('localhost', 5001, 'Alice');
    mock.instances[0]!.simulateOpen();
    await promise;
    store.disconnect();
    expect(store.status).toBe(ConnectionStatus.DISCONNECTED);
  });
});
```

- [ ] **Step 2: Fail**

```bash
cd client
npm test
```

Expected: fail (no existe `./connection`).

- [ ] **Step 3: Implementar `src/stores/connection.ts`**

```ts
import { defineStore } from 'pinia';
import { ref } from 'vue';
import type { ClientCommand, ServerEvent } from 'src/types/protocol';

export enum ConnectionStatus {
  DISCONNECTED = 'disconnected',
  CONNECTING   = 'connecting',
  CONNECTED    = 'connected',
  ERROR        = 'error',
}

type EventHandler = (e: ServerEvent) => void;

export const useConnectionStore = defineStore('connection', () => {
  const status        = ref<ConnectionStatus>(ConnectionStatus.DISCONNECTED);
  const host          = ref<string>('localhost');
  const port          = ref<number>(5001);
  const username      = ref<string>('');
  const errorMessage  = ref<string | null>(null);

  // Not reactive on purpose — Vue doesn't need to observe these.
  let socket: WebSocket | null = null;
  const handlers: EventHandler[] = [];

  function connect(h: string, p: number, u: string): Promise<void> {
    host.value = h;
    port.value = p;
    username.value = u;
    status.value = ConnectionStatus.CONNECTING;
    errorMessage.value = null;

    return new Promise((resolve, reject) => {
      const ws = new WebSocket(`ws://${h}:${p}`);
      socket = ws;
      ws.onopen = () => {
        status.value = ConnectionStatus.CONNECTED;
        resolve();
      };
      ws.onerror = () => {
        status.value = ConnectionStatus.ERROR;
        errorMessage.value = 'connection error';
        reject(new Error('connection error'));
      };
      ws.onclose = () => {
        status.value = ConnectionStatus.DISCONNECTED;
      };
      ws.onmessage = (evt: MessageEvent<string>) => {
        const parsed = JSON.parse(evt.data) as ServerEvent;
        for (const h of handlers) h(parsed);
      };
    });
  }

  function send(cmd: ClientCommand): void {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      throw new Error('socket not open');
    }
    socket.send(JSON.stringify(cmd));
  }

  function onEvent(handler: EventHandler): () => void {
    handlers.push(handler);
    return () => {
      const i = handlers.indexOf(handler);
      if (i >= 0) handlers.splice(i, 1);
    };
  }

  function disconnect(): void {
    if (socket) {
      socket.close();
      socket = null;
    }
    handlers.length = 0;
    status.value = ConnectionStatus.DISCONNECTED;
  }

  return { status, host, port, username, errorMessage,
           connect, send, onEvent, disconnect };
});
```

- [ ] **Step 4: Pass**

```bash
cd client
npm test
```

Expected: 5 passed.

- [ ] **Step 5: Report diff**

---

## Task 10: `lobbyStore`

**Files:**
- Create: `client/src/stores/lobby.ts`, `client/src/stores/lobby.test.ts`

- [ ] **Step 1: Tests**

```ts
// client/src/stores/lobby.test.ts
import { setActivePinia, createPinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useLobbyStore } from './lobby';
import { Color } from 'src/types/domain';

describe('lobbyStore', () => {
  beforeEach(() => setActivePinia(createPinia()));

  it('starts empty', () => {
    const s = useLobbyStore();
    expect(s.players).toEqual([]);
    expect(s.isHost).toBe(false);
    expect(s.myColor).toBeNull();
  });

  it('canStart requires 2+ players all with color', () => {
    const s = useLobbyStore();
    expect(s.canStart).toBe(false);
    s.updateFromLobbyUpdate(
      [{ username: 'A', color: Color.RED }],
      [Color.BLUE, Color.GREEN, Color.YELLOW],
    );
    expect(s.canStart).toBe(false);  // only 1 player
    s.updateFromLobbyUpdate(
      [{ username: 'A', color: Color.RED }, { username: 'B', color: null }],
      [Color.BLUE, Color.GREEN, Color.YELLOW],
    );
    expect(s.canStart).toBe(false);  // B has no color
    s.updateFromLobbyUpdate(
      [{ username: 'A', color: Color.RED }, { username: 'B', color: Color.BLUE }],
      [Color.GREEN, Color.YELLOW],
    );
    expect(s.canStart).toBe(true);
  });

  it('reset clears state', () => {
    const s = useLobbyStore();
    s.isHost = true;
    s.myColor = Color.RED;
    s.reset();
    expect(s.isHost).toBe(false);
    expect(s.myColor).toBeNull();
  });
});
```

- [ ] **Step 2: Fail**

- [ ] **Step 3: Implementar `src/stores/lobby.ts`**

```ts
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { Color, LobbyPlayerDto } from 'src/types/domain';

export const useLobbyStore = defineStore('lobby', () => {
  const players         = ref<LobbyPlayerDto[]>([]);
  const availableColors = ref<Color[]>([]);
  const isHost          = ref<boolean>(false);
  const myColor         = ref<Color | null>(null);

  const canStart = computed<boolean>(() =>
    players.value.length >= 2 && players.value.every(p => p.color !== null)
  );

  function updateFromLobbyUpdate(
    newPlayers: LobbyPlayerDto[],
    newAvailable: Color[],
  ): void {
    players.value = newPlayers;
    availableColors.value = newAvailable;
  }

  function reset(): void {
    players.value = [];
    availableColors.value = [];
    isHost.value = false;
    myColor.value = null;
  }

  return { players, availableColors, isHost, myColor, canStart,
           updateFromLobbyUpdate, reset };
});
```

- [ ] **Step 4: Pass** (3 passed in lobby.test.ts; total agregado). 

- [ ] **Step 5: Report diff**

---

## Task 11: `gameStore`

**Files:**
- Create: `client/src/stores/game.ts`, `client/src/stores/game.test.ts`
- Create: `client/src/test-utils/factories.ts`

- [ ] **Step 1: Factory de DTOs en `factories.ts`**

```ts
// client/src/test-utils/factories.ts
import {
  Color, GamePhase, PieceState,
  GameStateDto, PieceDto, PlayerDto,
} from 'src/types/domain';

export function makePiece(overrides: Partial<PieceDto> = {}): PieceDto {
  return {
    index: 0,
    state: PieceState.IN_JAIL,
    circuit_position: null,
    home_stretch_position: null,
    ...overrides,
  };
}

export function makePlayer(overrides: Partial<PlayerDto> = {}): PlayerDto {
  return {
    name: 'Alice',
    color: Color.RED,
    pieces: [makePiece({ index: 0 }), makePiece({ index: 1 }), makePiece({ index: 2 }), makePiece({ index: 3 })],
    ...overrides,
  };
}

export function makeGameState(overrides: Partial<GameStateDto> = {}): GameStateDto {
  return {
    players: [
      makePlayer({ name: 'Alice', color: Color.RED }),
      makePlayer({ name: 'Bob', color: Color.BLUE }),
    ],
    phase: GamePhase.SETUP,
    turn_order: [],
    current_turn_index: 0,
    pending_dice: [],
    initial_rolls: {},
    initial_rolls_remaining: 0,
    consecutive_pairs: 0,
    winner: null,
    ...overrides,
  };
}
```

- [ ] **Step 2: Tests del gameStore**

```ts
// client/src/stores/game.test.ts
import { setActivePinia, createPinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useGameStore } from './game';
import { Color, GamePhase } from 'src/types/domain';
import { makeGameState } from 'src/test-utils/factories';

describe('gameStore', () => {
  beforeEach(() => setActivePinia(createPinia()));

  it('starts with no state', () => {
    const s = useGameStore();
    expect(s.state).toBeNull();
    expect(s.isMyTurn).toBe(false);
    expect(s.phase).toBeNull();
  });

  it('isMyTurn is true when turn_order[current_turn_index] is my color', () => {
    const s = useGameStore();
    s.myColor = Color.RED;
    // Alice (RED) is players[0], Bob (BLUE) is players[1]. turn_order: [0, 1].
    s.updateFromStateUpdate(makeGameState({
      phase: GamePhase.ROLLING,
      turn_order: [0, 1],
      current_turn_index: 0,
    }));
    expect(s.isMyTurn).toBe(true);
    s.updateFromStateUpdate(makeGameState({
      phase: GamePhase.ROLLING,
      turn_order: [0, 1],
      current_turn_index: 1,
    }));
    expect(s.isMyTurn).toBe(false);
  });

  it('phase reflects state.phase', () => {
    const s = useGameStore();
    s.updateFromStateUpdate(makeGameState({ phase: GamePhase.MOVING, pending_dice: [3, 5] }));
    expect(s.phase).toBe(GamePhase.MOVING);
    expect(s.dice).toEqual([3, 5]);
  });

  it('setWinner updates winnerUsername', () => {
    const s = useGameStore();
    s.setWinner('Alice');
    expect(s.winnerUsername).toBe('Alice');
  });

  it('reset clears everything', () => {
    const s = useGameStore();
    s.myColor = Color.RED;
    s.setWinner('Alice');
    s.updateFromStateUpdate(makeGameState());
    s.reset();
    expect(s.state).toBeNull();
    expect(s.myColor).toBeNull();
    expect(s.winnerUsername).toBeNull();
  });
});
```

- [ ] **Step 3: Fail**

- [ ] **Step 4: Implementar `src/stores/game.ts`**

```ts
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { Color, GamePhase, GameStateDto, MoveDto } from 'src/types/domain';

export const useGameStore = defineStore('game', () => {
  const state           = ref<GameStateDto | null>(null);
  const availableMoves  = ref<MoveDto[]>([]);
  const myColor         = ref<Color | null>(null);
  const winnerUsername  = ref<string | null>(null);

  const currentTurnColor = computed<Color | null>(() => {
    const st = state.value;
    if (!st || st.turn_order.length === 0) return null;
    const playerIdx = st.turn_order[st.current_turn_index];
    return playerIdx !== undefined ? st.players[playerIdx]?.color ?? null : null;
  });

  const isMyTurn = computed<boolean>(() =>
    myColor.value !== null && currentTurnColor.value === myColor.value
  );

  const phase = computed<GamePhase | null>(() => state.value?.phase ?? null);

  const dice = computed<[number, number] | null>(() => {
    const pd = state.value?.pending_dice;
    if (!pd || pd.length !== 2) return null;
    return [pd[0]!, pd[1]!];
  });

  function updateFromStateUpdate(newState: GameStateDto): void {
    state.value = newState;
  }

  function setAvailableMoves(moves: MoveDto[]): void {
    availableMoves.value = moves;
  }

  function setWinner(u: string | null): void {
    winnerUsername.value = u;
  }

  function reset(): void {
    state.value = null;
    availableMoves.value = [];
    myColor.value = null;
    winnerUsername.value = null;
  }

  return { state, availableMoves, myColor, winnerUsername,
           currentTurnColor, isMyTurn, phase, dice,
           updateFromStateUpdate, setAvailableMoves, setWinner, reset };
});
```

- [ ] **Step 5: Pass**

- [ ] **Step 6: Report diff**

---

## Task 12: `useServerProtocol` composable

**Files:**
- Create: `client/src/composables/useServerProtocol.ts`
- Create: `client/src/composables/useServerProtocol.test.ts`

- [ ] **Step 1: Tests**

```ts
// client/src/composables/useServerProtocol.test.ts
import { createApp } from 'vue';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useServerProtocol } from './useServerProtocol';
import { ServerEventType, ClientCommandType } from 'src/types/protocol';
import { useConnectionStore } from 'src/stores/connection';
import { installMockWebSocket, MockWebSocket } from 'src/test-utils/mockWebSocket';

describe('useServerProtocol', () => {
  let mock: { restore: () => void; instances: MockWebSocket[] };

  beforeEach(() => {
    setActivePinia(createPinia());
    mock = installMockWebSocket();
  });
  afterEach(() => mock.restore());

  it('fires the registered handler when a typed event arrives', async () => {
    const store = useConnectionStore();
    const p = store.connect('localhost', 5001, 'A');
    mock.instances[0]!.simulateOpen();
    await p;

    // Tiny Vue app so onUnmounted lifecycle works.
    const app = createApp({
      setup() {
        const welcomeSpy = vi.fn();
        const { send } = useServerProtocol({
          [ServerEventType.WELCOME]: welcomeSpy,
        });
        // Trigger and assert.
        mock.instances[0]!.simulateMessage('{"type":"welcome","username":"A","is_host":true}');
        expect(welcomeSpy).toHaveBeenCalledWith({
          type: ServerEventType.WELCOME,
          username: 'A',
          is_host: true,
        });
        // Send too — it should go via the store.
        send({ type: ClientCommandType.ROLL_DICE });
        expect(mock.instances[0]!.sent).toContain('{"type":"roll_dice"}');
        return () => null;
      },
    });
    app.use(createPinia());
    const el = document.createElement('div');
    app.mount(el);
    app.unmount();
  });
});
```

- [ ] **Step 2: Fail**

- [ ] **Step 3: Implementar `src/composables/useServerProtocol.ts`**

```ts
import { onUnmounted } from 'vue';
import { useConnectionStore } from 'src/stores/connection';
import type { ClientCommand, ServerEvent } from 'src/types/protocol';
import { ServerEventType } from 'src/types/protocol';

type EventHandlers = {
  [K in ServerEventType]?: (event: Extract<ServerEvent, { type: K }>) => void;
};

export interface ServerProtocolHandle {
  send: (cmd: ClientCommand) => void;
}

export function useServerProtocol(handlers: EventHandlers): ServerProtocolHandle {
  const conn = useConnectionStore();

  const unsubscribe = conn.onEvent((event: ServerEvent) => {
    const handler = handlers[event.type];
    if (handler) {
      // The handler for a specific K is guaranteed by the EventHandlers shape.
      (handler as (e: ServerEvent) => void)(event);
    }
  });

  onUnmounted(unsubscribe);

  return { send: conn.send };
}
```

- [ ] **Step 4: Pass**

- [ ] **Step 5: Report diff**

---

## Task 13: `useBoardGeometry` composable

**Files:**
- Create: `client/src/composables/useBoardGeometry.ts`
- Create: `client/src/composables/useBoardGeometry.test.ts`

El layout cruciforme se define con **constantes** en el archivo. Meta: para cualquier `circuit_position: 0..95`, retornar `{ x, y }` dentro del viewBox 600×600.

- [ ] **Step 1: Implementar `useBoardGeometry.ts` con layout simple**

```ts
import { Color } from 'src/types/domain';

export interface Point { x: number; y: number }

// Layout constants — viewBox 600×600.
export const BOARD_SIZE     = 600;
export const CELL_SIZE      = 30;
export const JAIL_SIZE      = 150;
export const HOME_STRETCH_SIZE = 8;
export const GOAL_RADIUS    = 50;
export const GOAL_CENTER: Point = { x: BOARD_SIZE / 2, y: BOARD_SIZE / 2 };

// Arm index → starting offset and direction. Arm 0 = top, then clockwise.
// Each arm has 24 cells: 8 down outer lane, 8 across bottom, 8 up inner lane.
const ARMS = [
  { name: 'N', color: Color.RED    },
  { name: 'E', color: Color.BLUE   },
  { name: 'S', color: Color.GREEN  },
  { name: 'W', color: Color.YELLOW },
];

export function circuitCellCenter(position: number): Point {
  if (position < 0 || position >= 96) {
    throw new Error(`position out of range: ${position}`);
  }
  const arm      = Math.floor(position / 24);  // 0..3
  const cellInArm = position % 24;             // 0..23
  return armCellCenter(arm, cellInArm);
}

function armCellCenter(arm: number, cellInArm: number): Point {
  // The L-shape of each arm: 8 cells going "away" (outer lane),
  // 8 cells going "across" (bottom), 8 cells going "back" (inner lane).
  const cx = BOARD_SIZE / 2;
  const cy = BOARD_SIZE / 2;

  // Raw L-shape coordinates relative to arm 0 (top, pointing down toward center).
  let rx: number;
  let ry: number;
  if (cellInArm < 8) {
    // Outer lane going down.
    rx = -CELL_SIZE * 1.5;
    ry = -(BOARD_SIZE / 2) + JAIL_SIZE + 10 + CELL_SIZE * (cellInArm + 0.5);
  } else if (cellInArm < 16) {
    // Across the bottom of the arm, left to right.
    rx = -CELL_SIZE * 1.5 + CELL_SIZE * ((cellInArm - 8) + 0.5);
    ry = -(BOARD_SIZE / 2) + JAIL_SIZE + 10 + CELL_SIZE * 8;
  } else {
    // Inner lane going up.
    rx = CELL_SIZE * 1.5;
    ry = -(BOARD_SIZE / 2) + JAIL_SIZE + 10 + CELL_SIZE * ((23 - cellInArm) + 0.5);
  }

  // Rotate by 90° × arm around the center.
  const theta = (Math.PI / 2) * arm;
  const x = cx + rx * Math.cos(theta) - ry * Math.sin(theta);
  const y = cy + rx * Math.sin(theta) + ry * Math.cos(theta);
  return { x, y };
}

export function homeStretchCellCenter(color: Color, index: number): Point {
  if (index < 0 || index >= HOME_STRETCH_SIZE) {
    throw new Error(`home_stretch index out of range: ${index}`);
  }
  const arm = ARMS.findIndex(a => a.color === color);
  if (arm < 0) throw new Error(`unknown color: ${color}`);

  // Home stretch cells go from the arm's inner entry toward the center.
  const cx = BOARD_SIZE / 2;
  const cy = BOARD_SIZE / 2;
  // index 0 is just after the circuit entry; index 7 is adjacent to the goal.
  const distanceFromCenter = (HOME_STRETCH_SIZE - 1 - index) * CELL_SIZE + GOAL_RADIUS + CELL_SIZE / 2;
  const theta = (Math.PI / 2) * arm;
  const rx = 0;
  const ry = -distanceFromCenter;
  const x = cx + rx * Math.cos(theta) - ry * Math.sin(theta);
  const y = cy + rx * Math.sin(theta) + ry * Math.cos(theta);
  return { x, y };
}

export function jailSlotCenter(color: Color, slot: number): Point {
  if (slot < 0 || slot >= 4) throw new Error(`slot out of range: ${slot}`);
  const arm = ARMS.findIndex(a => a.color === color);
  if (arm < 0) throw new Error(`unknown color: ${color}`);

  // Jail corners: N=top-left, E=top-right, S=bottom-right, W=bottom-left.
  const corners: Array<{ x: number; y: number }> = [
    { x: 10,                       y: 10                       },
    { x: BOARD_SIZE - JAIL_SIZE - 10, y: 10                       },
    { x: BOARD_SIZE - JAIL_SIZE - 10, y: BOARD_SIZE - JAIL_SIZE - 10 },
    { x: 10,                       y: BOARD_SIZE - JAIL_SIZE - 10 },
  ];
  const corner = corners[arm]!;
  // 2×2 grid of slots inside the jail.
  const slotX = slot % 2;
  const slotY = Math.floor(slot / 2);
  const inset = JAIL_SIZE / 4;
  return {
    x: corner.x + inset + slotX * (JAIL_SIZE / 2),
    y: corner.y + inset + slotY * (JAIL_SIZE / 2),
  };
}

export function goalCenter(): Point {
  return GOAL_CENTER;
}
```

- [ ] **Step 2: Tests**

```ts
// client/src/composables/useBoardGeometry.test.ts
import { describe, expect, it } from 'vitest';
import { Color } from 'src/types/domain';
import {
  BOARD_SIZE,
  circuitCellCenter,
  goalCenter,
  homeStretchCellCenter,
  jailSlotCenter,
} from './useBoardGeometry';

describe('useBoardGeometry', () => {
  it('goal center is at (300, 300)', () => {
    expect(goalCenter()).toEqual({ x: 300, y: 300 });
  });

  it('circuit cells are all within the viewBox', () => {
    for (let p = 0; p < 96; p++) {
      const { x, y } = circuitCellCenter(p);
      expect(x).toBeGreaterThanOrEqual(0);
      expect(x).toBeLessThanOrEqual(BOARD_SIZE);
      expect(y).toBeGreaterThanOrEqual(0);
      expect(y).toBeLessThanOrEqual(BOARD_SIZE);
    }
  });

  it('circuitCellCenter throws for out-of-range', () => {
    expect(() => circuitCellCenter(-1)).toThrow();
    expect(() => circuitCellCenter(96)).toThrow();
  });

  it('home stretch cells for each color stay inside the viewBox', () => {
    for (const color of [Color.RED, Color.BLUE, Color.GREEN, Color.YELLOW]) {
      for (let i = 0; i < 8; i++) {
        const { x, y } = homeStretchCellCenter(color, i);
        expect(x).toBeGreaterThanOrEqual(0);
        expect(x).toBeLessThanOrEqual(BOARD_SIZE);
        expect(y).toBeGreaterThanOrEqual(0);
        expect(y).toBeLessThanOrEqual(BOARD_SIZE);
      }
    }
  });

  it('jail slots distribute into 4 corners', () => {
    const red   = jailSlotCenter(Color.RED, 0);
    const blue  = jailSlotCenter(Color.BLUE, 0);
    const green = jailSlotCenter(Color.GREEN, 0);
    const yellow = jailSlotCenter(Color.YELLOW, 0);
    // Red top-left should have small x and y.
    expect(red.x).toBeLessThan(BOARD_SIZE / 2);
    expect(red.y).toBeLessThan(BOARD_SIZE / 2);
    // Blue top-right.
    expect(blue.x).toBeGreaterThan(BOARD_SIZE / 2);
    expect(blue.y).toBeLessThan(BOARD_SIZE / 2);
    // Green bottom-right.
    expect(green.x).toBeGreaterThan(BOARD_SIZE / 2);
    expect(green.y).toBeGreaterThan(BOARD_SIZE / 2);
    // Yellow bottom-left.
    expect(yellow.x).toBeLessThan(BOARD_SIZE / 2);
    expect(yellow.y).toBeGreaterThan(BOARD_SIZE / 2);
  });
});
```

- [ ] **Step 3: Pass**

- [ ] **Step 4: Report diff**

---

## Task 14: Router con `Route` enum y guards

**Files:**
- Create: `client/src/router/routes.ts`
- Modify: `client/src/router/index.ts`

- [ ] **Step 1: `src/router/routes.ts`**

```ts
import type { RouteRecordRaw } from 'vue-router';

export enum Route {
  CONNECT = '/connect',
  LOBBY   = '/lobby',
  GAME    = '/game',
  END     = '/end',
}

const routes: RouteRecordRaw[] = [
  { path: '/',           redirect: Route.CONNECT },
  { path: Route.CONNECT, component: () => import('pages/ConnectPage.vue') },
  { path: Route.LOBBY,   component: () => import('pages/LobbyPage.vue'),
    meta: { requiresConnection: true } },
  { path: Route.GAME,    component: () => import('pages/GamePage.vue'),
    meta: { requiresConnection: true } },
  { path: Route.END,     component: () => import('pages/EndPage.vue'),
    meta: { requiresConnection: true } },
  { path: '/:catchAll(.*)*', redirect: Route.CONNECT },
];

export default routes;
```

- [ ] **Step 2: `src/router/index.ts`**

```ts
import { defineRouter } from '#q-app/wrappers';
import {
  createMemoryHistory, createRouter, createWebHashHistory, createWebHistory,
} from 'vue-router';
import routes from './routes';
import { Route } from './routes';
import { ConnectionStatus, useConnectionStore } from 'src/stores/connection';

export default defineRouter(function (/* { store, ssrContext } */) {
  const createHistory = process.env.SERVER
    ? createMemoryHistory
    : (process.env.VUE_ROUTER_MODE === 'history' ? createWebHistory : createWebHashHistory);
  const Router = createRouter({
    scrollBehavior: () => ({ left: 0, top: 0 }),
    routes,
    history: createHistory(process.env.VUE_ROUTER_BASE),
  });

  Router.beforeEach((to) => {
    if (to.meta['requiresConnection']) {
      const conn = useConnectionStore();
      if (conn.status !== ConnectionStatus.CONNECTED) {
        return Route.CONNECT;
      }
    }
    return true;
  });

  return Router;
});
```

- [ ] **Step 3: Verify**

```bash
cd client
npm run typecheck
npm run lint
npm test
```

Expected: todos los tests del stores+composables pasan; sin errores TS/ESLint.

- [ ] **Step 4: Report diff**

---

## Task 15: `MainLayout` + app skeleton

**Files:**
- Modify: `client/src/layouts/MainLayout.vue`
- Create: `client/src/css/app.scss` (si no existe)

- [ ] **Step 1: `MainLayout.vue`**

```vue
<template>
  <q-layout view="hHh lpR fFf">
    <q-header elevated class="bg-primary">
      <q-toolbar>
        <q-toolbar-title>Parqués</q-toolbar-title>
        <q-space />
        <q-icon v-if="conn.status === ConnectionStatus.CONNECTED" name="wifi" />
        <q-icon v-else name="wifi_off" />
      </q-toolbar>
    </q-header>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { ConnectionStatus, useConnectionStore } from 'src/stores/connection';

const conn = useConnectionStore();
</script>
```

- [ ] **Step 2: CSS básico en `src/css/app.scss`**

```scss
// Game-specific colors.
:root {
  --parques-red:    #e74c3c;
  --parques-blue:   #3498db;
  --parques-green:  #27ae60;
  --parques-yellow: #f1c40f;
  --parques-safe:   #c8e6c9;
}

.piece-circle {
  transition: cx 0.3s ease, cy 0.3s ease;
  stroke: #333;
  stroke-width: 2;
}

.piece-circle.selectable {
  filter: drop-shadow(0 0 6px gold);
  cursor: pointer;
}
```

- [ ] **Step 3: Verify dev still runs**

```bash
cd client
npm run dev &
DEV_PID=$!
# Poll until the dev server responds or give up after 20s.
for _ in $(seq 1 40); do
  if curl -s -o /dev/null -w "%{http_code}" http://localhost:9000 | grep -q "^2"; then
    echo "dev server ready"
    break
  fi
  sleep 0.5
done
curl -s http://localhost:9000 | head -5
kill "$DEV_PID" 2>/dev/null || true
wait "$DEV_PID" 2>/dev/null || true
```

Expected: HTML inicial sin errores.

- [ ] **Step 4: Report diff**

---

## Task 16: `ConnectPage`

**Files:**
- Create: `client/src/pages/ConnectPage.vue`

- [ ] **Step 1: `ConnectPage.vue`**

```vue
<template>
  <q-page class="q-pa-md flex flex-center">
    <q-card style="min-width: 320px; max-width: 400px; width: 100%">
      <q-card-section>
        <div class="text-h5">Conectar al servidor</div>
      </q-card-section>
      <q-card-section>
        <q-input v-model="host" label="Host" :rules="[v => !!v || 'Requerido']" />
        <q-input v-model.number="port" label="Puerto" type="number"
                 :rules="[v => v >= 1 && v <= 65535 || 'Puerto inválido']" />
        <q-input v-model="username" label="Nombre de usuario"
                 :rules="[v => v.length >= 3 && v.length <= 20 || '3-20 caracteres']" />
      </q-card-section>
      <q-card-actions align="center">
        <q-btn color="primary" label="Conectar" :loading="connecting" @click="onConnect" />
      </q-card-actions>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { useConnectionStore, ConnectionStatus } from 'src/stores/connection';
import { useLobbyStore } from 'src/stores/lobby';
import { useServerProtocol } from 'src/composables/useServerProtocol';
import { ClientCommandType, ServerEventType, ErrorCode } from 'src/types/protocol';
import { Route } from 'src/router/routes';

const $q       = useQuasar();
const router   = useRouter();
const conn     = useConnectionStore();
const lobby    = useLobbyStore();

const host     = ref<string>(localStorage.getItem('parques.host')     || 'localhost');
const port     = ref<number>(Number(localStorage.getItem('parques.port')) || 5001);
const username = ref<string>(localStorage.getItem('parques.username') || '');
const connecting = ref<boolean>(false);

const { send } = useServerProtocol({
  [ServerEventType.WELCOME]: (e) => {
    lobby.isHost = e.is_host;
    router.push(Route.LOBBY);
  },
  [ServerEventType.ERROR]: (e) => {
    $q.notify({ color: 'negative', message: e.message, icon: 'error' });
    connecting.value = false;
  },
});

async function onConnect(): Promise<void> {
  connecting.value = true;
  try {
    await conn.connect(host.value, port.value, username.value);
    localStorage.setItem('parques.host',     host.value);
    localStorage.setItem('parques.port',     String(port.value));
    localStorage.setItem('parques.username', username.value);
    send({ type: ClientCommandType.JOIN, username: username.value });
  } catch (err: unknown) {
    connecting.value = false;
    $q.notify({ color: 'negative', message: 'No se pudo conectar', icon: 'error' });
  }
}
</script>
```

- [ ] **Step 2: Verify builds**

```bash
cd client
npm run typecheck
npm run lint
```

- [ ] **Step 3: Manual smoke**

```bash
# Terminal 1
.venv/bin/python -m server --port-tcp 5000 --port-ws 5001
# Terminal 2
cd client && npm run dev
# Browser http://localhost:9000 → /connect, click Conectar, verificar que redirige a /lobby (aunque esa página aún esté vacía).
```

- [ ] **Step 4: Report diff**

---

## Task 17: `LobbyPage`

**Files:**
- Create: `client/src/pages/LobbyPage.vue`

- [ ] **Step 1: `LobbyPage.vue`**

```vue
<template>
  <q-page class="q-pa-md">
    <div class="text-h5 q-mb-md">Sala de espera</div>

    <q-card class="q-mb-md">
      <q-list>
        <q-item v-for="p in lobby.players" :key="p.username">
          <q-item-section avatar>
            <q-avatar :style="avatarStyle(p.color)" text-color="white">
              {{ p.username.charAt(0).toUpperCase() }}
            </q-avatar>
          </q-item-section>
          <q-item-section>
            <q-item-label>{{ p.username }}</q-item-label>
            <q-item-label caption>{{ p.color ?? 'sin color' }}</q-item-label>
          </q-item-section>
        </q-item>
      </q-list>
    </q-card>

    <div class="q-mb-md">
      <div class="text-subtitle1 q-mb-sm">Elige tu color</div>
      <div class="row q-gutter-sm">
        <q-btn v-for="c in lobby.availableColors" :key="c"
               :label="c" :style="colorBtnStyle(c)"
               @click="onSelectColor(c)" />
      </div>
    </div>

    <div v-if="lobby.isHost">
      <q-btn color="positive" size="lg" :disable="!lobby.canStart" @click="onStart">
        Iniciar partida
      </q-btn>
    </div>
    <div v-else class="text-caption">Esperando al host…</div>
  </q-page>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { useLobbyStore } from 'src/stores/lobby';
import { useGameStore } from 'src/stores/game';
import { useServerProtocol } from 'src/composables/useServerProtocol';
import { ClientCommandType, ServerEventType } from 'src/types/protocol';
import { Color } from 'src/types/domain';
import { Route } from 'src/router/routes';

const $q     = useQuasar();
const router = useRouter();
const lobby  = useLobbyStore();
const game   = useGameStore();

const { send } = useServerProtocol({
  [ServerEventType.LOBBY_UPDATE]: (e) => {
    lobby.updateFromLobbyUpdate(e.players, e.available_colors);
  },
  [ServerEventType.GAME_STARTED]: () => {
    game.myColor = lobby.myColor;
    router.push(Route.GAME);
  },
  [ServerEventType.ERROR]: (e) => {
    $q.notify({ color: 'negative', message: e.message });
  },
});

const COLOR_HEX: Record<Color, string> = {
  [Color.RED]:    '#e74c3c',
  [Color.BLUE]:   '#3498db',
  [Color.GREEN]:  '#27ae60',
  [Color.YELLOW]: '#f1c40f',
};

function avatarStyle(color: Color | null): Record<string, string> {
  return { backgroundColor: color ? COLOR_HEX[color] : '#999' };
}

function colorBtnStyle(color: Color): Record<string, string> {
  return { backgroundColor: COLOR_HEX[color], color: 'white' };
}

function onSelectColor(c: Color): void {
  lobby.myColor = c;
  send({ type: ClientCommandType.SELECT_COLOR, color: c });
}

function onStart(): void {
  send({ type: ClientCommandType.START_GAME });
}
</script>
```

- [ ] **Step 2: Smoke manual**

Arrancar server y dos tabs del browser. Ambas hacen join, eligen color, host arranca, ambas saltan a /game.

- [ ] **Step 3: Report diff**

---

## Task 18: `BoardCanvas.vue` (tablero SVG estático)

**Files:**
- Create: `client/src/components/BoardCanvas.vue`

- [ ] **Step 1: Implementar el SVG del tablero sin piezas**

```vue
<template>
  <svg :viewBox="`0 0 ${BOARD_SIZE} ${BOARD_SIZE}`" class="board-svg">
    <!-- Fondo -->
    <rect :width="BOARD_SIZE" :height="BOARD_SIZE" fill="#f5e6c8" rx="8" />

    <!-- Cárceles -->
    <g v-for="(color, i) in JAIL_COLORS" :key="'jail-'+i">
      <rect :x="jailCorner(i).x" :y="jailCorner(i).y"
            :width="JAIL_SIZE" :height="JAIL_SIZE"
            :fill="COLOR_HEX[color]" fill-opacity="0.3" stroke="#666" rx="4" />
      <text :x="jailCorner(i).x + JAIL_SIZE/2" :y="jailCorner(i).y + 20"
            text-anchor="middle" font-size="12" fill="#333">CÁRCEL</text>
    </g>

    <!-- Circuit cells -->
    <rect v-for="pos in CIRCUIT_POSITIONS" :key="'cell-'+pos"
          :x="circuitCellCenter(pos).x - CELL_SIZE/2"
          :y="circuitCellCenter(pos).y - CELL_SIZE/2"
          :width="CELL_SIZE" :height="CELL_SIZE"
          :fill="cellFill(pos)" stroke="#999" stroke-width="0.5" rx="2" />

    <!-- Home stretches -->
    <g v-for="color in [Color.RED, Color.BLUE, Color.GREEN, Color.YELLOW]" :key="'hs-'+color">
      <rect v-for="i in HOME_STRETCH_INDICES" :key="'hs-'+color+'-'+i"
            :x="homeStretchCellCenter(color, i).x - CELL_SIZE/2"
            :y="homeStretchCellCenter(color, i).y - CELL_SIZE/2"
            :width="CELL_SIZE" :height="CELL_SIZE"
            :fill="COLOR_HEX[color]" fill-opacity="0.4"
            stroke="#999" stroke-width="0.5" rx="2" />
    </g>

    <!-- Goal -->
    <circle :cx="BOARD_SIZE/2" :cy="BOARD_SIZE/2" :r="GOAL_RADIUS"
            fill="#87CEEB" stroke="#666" stroke-width="1.5" />
    <text :x="BOARD_SIZE/2" :y="BOARD_SIZE/2" text-anchor="middle"
          dominant-baseline="middle" font-size="14" fill="#333" font-weight="bold">META</text>

    <!-- Pieces rendered via <PieceToken> → Task 19 -->
    <slot name="pieces" />
  </svg>
</template>

<script setup lang="ts">
import { Color } from 'src/types/domain';
import {
  BOARD_SIZE, CELL_SIZE, JAIL_SIZE, GOAL_RADIUS,
  circuitCellCenter, homeStretchCellCenter,
} from 'src/composables/useBoardGeometry';

const COLOR_HEX: Record<Color, string> = {
  [Color.RED]:    '#e74c3c',
  [Color.BLUE]:   '#3498db',
  [Color.GREEN]:  '#27ae60',
  [Color.YELLOW]: '#f1c40f',
};

// Arm 0 = N/RED, 1 = E/BLUE, 2 = S/GREEN, 3 = W/YELLOW.
const JAIL_COLORS = [Color.RED, Color.BLUE, Color.GREEN, Color.YELLOW];
const CIRCUIT_POSITIONS: number[] = Array.from({ length: 96 }, (_, i) => i);
const HOME_STRETCH_INDICES: number[] = Array.from({ length: 8 }, (_, i) => i);

// Constants for exits and safes — MUST STAY IN SYNC with core/board.py.
// If the Python motor ever changes EXITS or SAFES, update these two sets.
const EXITS_POSITIONS = new Set<number>([0, 24, 48, 72]);
const SAFE_POSITIONS  = new Set<number>([0, 6, 18, 24, 30, 42, 48, 54, 66, 72, 78, 90]);

function cellFill(pos: number): string {
  if (EXITS_POSITIONS.has(pos)) return '#ffeb3b';
  if (SAFE_POSITIONS.has(pos))   return '#c8e6c9';
  return '#fff';
}

function jailCorner(arm: number): { x: number; y: number } {
  const corners = [
    { x: 10,                   y: 10                   },
    { x: BOARD_SIZE - JAIL_SIZE - 10, y: 10                   },
    { x: BOARD_SIZE - JAIL_SIZE - 10, y: BOARD_SIZE - JAIL_SIZE - 10 },
    { x: 10,                   y: BOARD_SIZE - JAIL_SIZE - 10 },
  ];
  return corners[arm]!;
}
</script>

<style scoped>
.board-svg {
  width: 100%;
  max-width: 600px;
  height: auto;
  display: block;
  margin: 0 auto;
}
</style>
```

- [ ] **Step 2: Smoke visual**

Temporalmente, modificar `GamePage.vue` stub (si existe) o crear un test page con `<BoardCanvas />`. Verificar visualmente en `npm run dev` que el tablero dibuja el circuito + cárceles + rectas finales + meta.

- [ ] **Step 3: Report diff**

---

## Task 19: `PieceToken.vue` + render de piezas en el tablero

**Files:**
- Create: `client/src/components/PieceToken.vue`

- [ ] **Step 1: `PieceToken.vue`**

```vue
<template>
  <circle
    v-if="position"
    :cx="position.x" :cy="position.y" :r="18"
    :fill="fill"
    class="piece-circle"
    :class="{ selectable }"
    @click="$emit('click')"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { PieceDto } from 'src/types/domain';
import { Color, PieceState } from 'src/types/domain';
import {
  circuitCellCenter,
  homeStretchCellCenter,
  jailSlotCenter,
} from 'src/composables/useBoardGeometry';

const props = defineProps<{
  piece: PieceDto;
  color: Color;
  selectable: boolean;
}>();

defineEmits<{ (e: 'click'): void }>();

const COLOR_HEX: Record<Color, string> = {
  [Color.RED]:    '#e74c3c',
  [Color.BLUE]:   '#3498db',
  [Color.GREEN]:  '#27ae60',
  [Color.YELLOW]: '#f1c40f',
};

const fill = computed(() => COLOR_HEX[props.color]);

const position = computed<{ x: number; y: number } | null>(() => {
  switch (props.piece.state) {
    case PieceState.IN_JAIL:
      return jailSlotCenter(props.color, props.piece.index);
    case PieceState.ON_BOARD:
      if (props.piece.circuit_position === null) return null;
      return circuitCellCenter(props.piece.circuit_position);
    case PieceState.IN_HOME_STRETCH:
      if (props.piece.home_stretch_position === null) return null;
      return homeStretchCellCenter(props.color, props.piece.home_stretch_position);
    case PieceState.CROWNED:
      return null;  // not rendered on the board
  }
});
</script>
```

- [ ] **Step 2: Test mínimo de `PieceToken`**

```ts
// client/src/components/PieceToken.test.ts
import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import PieceToken from './PieceToken.vue';
import { Color, PieceState } from 'src/types/domain';
import { makePiece } from 'src/test-utils/factories';

describe('PieceToken', () => {
  it('renders a circle when the piece is ON_BOARD', () => {
    const wrapper = mount(PieceToken, {
      props: {
        piece: makePiece({ state: PieceState.ON_BOARD, circuit_position: 10 }),
        color: Color.RED,
        selectable: false,
      },
    });
    expect(wrapper.find('circle').exists()).toBe(true);
  });

  it('does not render for CROWNED pieces', () => {
    const wrapper = mount(PieceToken, {
      props: {
        piece: makePiece({ state: PieceState.CROWNED }),
        color: Color.RED,
        selectable: false,
      },
    });
    expect(wrapper.find('circle').exists()).toBe(false);
  });

  it('adds selectable class when selectable', () => {
    const wrapper = mount(PieceToken, {
      props: {
        piece: makePiece({ state: PieceState.ON_BOARD, circuit_position: 10 }),
        color: Color.RED,
        selectable: true,
      },
    });
    expect(wrapper.classes()).toContain('selectable');
  });
});
```

- [ ] **Step 3: Pass**

- [ ] **Step 4: Report diff**

---

## Task 20: `DiceRoller`, `PlayerList`, `TurnBanner`

**Files:**
- Create: `client/src/components/DiceRoller.vue`
- Create: `client/src/components/PlayerList.vue`
- Create: `client/src/components/TurnBanner.vue`

Componentes presentacionales — lógica mínima, props explícitas.

- [ ] **Step 1: `DiceRoller.vue`**

```vue
<template>
  <div class="row items-center q-gutter-md">
    <div class="die">{{ d1 ?? '·' }}</div>
    <div class="die">{{ d2 ?? '·' }}</div>
    <q-btn v-if="canRoll" color="primary" size="lg" label="Lanzar" @click="$emit('roll')" />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  d1: number | null;
  d2: number | null;
  canRoll: boolean;
}>();
defineEmits<{ (e: 'roll'): void }>();
</script>

<style scoped>
.die {
  width: 64px; height: 64px;
  border: 2px solid #333; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 32px; font-weight: bold;
  background: white;
}
</style>
```

- [ ] **Step 2: `PlayerList.vue`**

```vue
<template>
  <q-list>
    <q-item v-for="(p, idx) in players" :key="p.name"
            :class="{ 'bg-primary text-white': idx === currentTurnIndex }">
      <q-item-section avatar>
        <q-avatar :style="avatarStyle(p.color)" text-color="white">
          {{ p.name.charAt(0).toUpperCase() }}
        </q-avatar>
      </q-item-section>
      <q-item-section>
        <q-item-label>{{ p.name }}</q-item-label>
        <q-item-label caption>{{ crownedCount(p) }} / 4 coronadas</q-item-label>
      </q-item-section>
    </q-item>
  </q-list>
</template>

<script setup lang="ts">
import { Color, PieceState } from 'src/types/domain';
import type { PlayerDto } from 'src/types/domain';

defineProps<{
  players: PlayerDto[];
  currentTurnIndex: number;
}>();

const COLOR_HEX: Record<Color, string> = {
  [Color.RED]:    '#e74c3c',
  [Color.BLUE]:   '#3498db',
  [Color.GREEN]:  '#27ae60',
  [Color.YELLOW]: '#f1c40f',
};

function avatarStyle(color: Color): Record<string, string> {
  return { backgroundColor: COLOR_HEX[color] };
}

function crownedCount(p: PlayerDto): number {
  return p.pieces.filter(x => x.state === PieceState.CROWNED).length;
}
</script>
```

- [ ] **Step 3: `TurnBanner.vue`**

```vue
<template>
  <div class="turn-banner" :class="{ 'my-turn': isMyTurn }">
    {{ text }}
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  isMyTurn: boolean;
  currentPlayerName: string | null;
}>();

const text = computed<string>(() => {
  if (props.isMyTurn) return 'Tu turno';
  if (props.currentPlayerName) return `Turno de ${props.currentPlayerName}`;
  return 'Esperando…';
});
</script>

<style scoped>
.turn-banner {
  padding: 16px;
  text-align: center;
  font-size: 20px;
  background: #eee;
}
.turn-banner.my-turn {
  background: #4caf50;
  color: white;
  font-weight: bold;
}
</style>
```

- [ ] **Step 4: Pass (npm test aún verde)**

- [ ] **Step 5: Report diff**

---

## Task 21: `GamePage` — integración completa

**Files:**
- Create: `client/src/pages/GamePage.vue`

Este es el componente más complejo del cliente. Integra `BoardCanvas`, `PieceToken`, `DiceRoller`, `PlayerList`, `TurnBanner` con los 3 stores.

- [ ] **Step 1: `GamePage.vue`**

```vue
<template>
  <q-page class="q-pa-sm">
    <TurnBanner :is-my-turn="game.isMyTurn" :current-player-name="currentPlayerName" />

    <div class="row q-mt-md">
      <!-- Tablero -->
      <div class="col-12 col-md-8">
        <BoardCanvas>
          <template #pieces>
            <PieceToken v-for="(piece, idx) in allPieces" :key="idx"
                        :piece="piece.dto" :color="piece.color"
                        :selectable="isSelectable(piece)"
                        @click="onPieceClick(piece)" />
          </template>
        </BoardCanvas>
      </div>

      <!-- Panel lateral (desktop) / Bottom sheet (mobile) -->
      <div class="col-12 col-md-4 q-pl-md">
        <PlayerList v-if="game.state"
                    :players="game.state.players"
                    :current-turn-index="currentTurnIndex" />
        <q-separator spaced />
        <DiceRoller :d1="game.dice?.[0] ?? null" :d2="game.dice?.[1] ?? null"
                    :can-roll="canRoll" @roll="onRoll" />
        <q-btn v-if="canSkip" class="q-mt-md full-width" label="Pasar turno" @click="onSkip" />
        <q-btn disable class="q-mt-md full-width" label="Recomendación (pronto)" />
      </div>
    </div>

    <!-- Dialog: Crowning (triple pair) -->
    <q-dialog :model-value="game.phase === GamePhase.CROWNING && game.isMyTurn" persistent>
      <q-card>
        <q-card-section class="text-center">
          <div class="text-h6">¡Triple par!</div>
          <div>Elige la ficha que quieres coronar</div>
        </q-card-section>
        <q-card-actions align="center">
          <q-btn v-for="p in crownablePieces" :key="p.index"
                 color="primary" :label="`Ficha ${p.index + 1}`"
                 @click="onCrownPiece(p.index)" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Dialog: Choose die when piece has multiple options -->
    <q-dialog :model-value="dieChoice !== null" persistent>
      <q-card v-if="dieChoice">
        <q-card-section>¿Usar el {{ dieChoice.options[0] }} o el {{ dieChoice.options[1] }}?</q-card-section>
        <q-card-actions align="center">
          <q-btn v-for="die in dieChoice.options" :key="die"
                 color="primary" :label="String(die)" @click="onDieChosen(die)" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useQuasar } from 'quasar';

import BoardCanvas from 'components/BoardCanvas.vue';
import PieceToken from 'components/PieceToken.vue';
import DiceRoller from 'components/DiceRoller.vue';
import PlayerList from 'components/PlayerList.vue';
import TurnBanner from 'components/TurnBanner.vue';

import { useGameStore } from 'src/stores/game';
import { useLobbyStore } from 'src/stores/lobby';
import { useServerProtocol } from 'src/composables/useServerProtocol';
import { ClientCommandType, ServerEventType } from 'src/types/protocol';
import { Color, GamePhase, PieceState } from 'src/types/domain';
import type { PieceDto, MoveDto } from 'src/types/domain';
import { Route } from 'src/router/routes';

const $q     = useQuasar();
const router = useRouter();
const game   = useGameStore();
const lobby  = useLobbyStore();

interface PieceOwned { dto: PieceDto; color: Color; playerIndex: number }

const { send } = useServerProtocol({
  [ServerEventType.STATE_UPDATE]:    (e) => game.updateFromStateUpdate(e.state),
  [ServerEventType.AVAILABLE_MOVES]: (e) => game.setAvailableMoves(e.moves),
  [ServerEventType.GAME_OVER]:       (e) => {
    game.setWinner(e.winner_username);
    router.push(Route.END);
  },
  [ServerEventType.ERROR]: (e) => $q.notify({ color: 'negative', message: e.message }),
});

const allPieces = computed<PieceOwned[]>(() => {
  if (!game.state) return [];
  const out: PieceOwned[] = [];
  for (let pIdx = 0; pIdx < game.state.players.length; pIdx++) {
    const player = game.state.players[pIdx]!;
    for (const piece of player.pieces) {
      out.push({ dto: piece, color: player.color, playerIndex: pIdx });
    }
  }
  return out;
});

const currentTurnIndex = computed<number>(() => {
  const st = game.state;
  if (!st || st.turn_order.length === 0) return -1;
  return st.turn_order[st.current_turn_index] ?? -1;
});

const currentPlayerName = computed<string | null>(() => {
  const idx = currentTurnIndex.value;
  return idx >= 0 ? game.state?.players[idx]?.name ?? null : null;
});

function isSelectable(p: PieceOwned): boolean {
  if (!game.isMyTurn) return false;
  if (p.color !== game.myColor) return false;
  return game.availableMoves.some(m => m.piece_index === p.dto.index);
}

const canRoll = computed<boolean>(() =>
  game.isMyTurn && (game.phase === GamePhase.ROLLING || game.phase === GamePhase.SETUP)
);

const canSkip = computed<boolean>(() =>
  game.isMyTurn && game.phase === GamePhase.MOVING && game.availableMoves.length === 0
);

function onRoll(): void {
  if (game.phase === GamePhase.SETUP) {
    // Need our player index.
    const myIdx = game.state?.players.findIndex(p => p.color === game.myColor) ?? -1;
    if (myIdx < 0) return;
    send({ type: ClientCommandType.ROLL_INITIAL });
  } else {
    send({ type: ClientCommandType.ROLL_DICE });
  }
}

function onSkip(): void {
  send({ type: ClientCommandType.SKIP_TURN });
}

const crownablePieces = computed<PieceDto[]>(() => {
  if (!game.state || game.myColor === null) return [];
  const me = game.state.players.find(p => p.color === game.myColor);
  return me ? me.pieces.filter(pc => pc.state !== PieceState.CROWNED) : [];
});

function onCrownPiece(piece_index: number): void {
  send({ type: ClientCommandType.CROWN_PIECE, piece_index });
}

// Die-choice handling: if a piece has multiple moves with different dice, ask.
interface DieChoice { pieceIndex: number; options: number[] }
const dieChoice = ref<DieChoice | null>(null);

function onPieceClick(p: PieceOwned): void {
  const matches = game.availableMoves.filter(m => m.piece_index === p.dto.index);
  if (matches.length === 1) {
    applyMove(matches[0]!);
  } else if (matches.length > 1) {
    dieChoice.value = {
      pieceIndex: p.dto.index,
      options: [...new Set(matches.map(m => m.dice_value))],
    };
  }
}

function onDieChosen(die: number): void {
  if (!dieChoice.value) return;
  const move = game.availableMoves.find(m =>
    m.piece_index === dieChoice.value!.pieceIndex && m.dice_value === die
  );
  dieChoice.value = null;
  if (move) applyMove(move);
}

function applyMove(move: MoveDto): void {
  send({
    type: ClientCommandType.MOVE_PIECE,
    piece_index: move.piece_index,
    dice_value: move.dice_value,
    action: move.action,
  });
}
</script>
```

- [ ] **Step 2: Smoke manual con 2 pestañas**

Iniciar server, dos tabs: `/connect` → join → select_color → start_game (host) → ambas ven el tablero → pueden lanzar dados y mover fichas → el juego progresa. Verificar animación suave al mover. Verificar captura, recta final, coronar.

- [ ] **Step 3: Report diff**

---

## Task 22: `EndPage`

**Files:**
- Create: `client/src/pages/EndPage.vue`

- [ ] **Step 1:**

```vue
<template>
  <q-page class="flex flex-center">
    <q-card style="min-width: 300px">
      <q-card-section class="text-center">
        <div class="text-h4">¡Fin del juego!</div>
        <div class="text-h6 q-mt-md">
          Ganador: {{ game.winnerUsername ?? 'empate' }}
        </div>
      </q-card-section>
      <q-card-actions align="center">
        <q-btn color="primary" label="Volver al menú" @click="onBack" />
      </q-card-actions>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';
import { useConnectionStore } from 'src/stores/connection';
import { useGameStore } from 'src/stores/game';
import { useLobbyStore } from 'src/stores/lobby';
import { Route } from 'src/router/routes';

const router = useRouter();
const conn   = useConnectionStore();
const game   = useGameStore();
const lobby  = useLobbyStore();

function onBack(): void {
  conn.disconnect();
  game.reset();
  lobby.reset();
  router.push(Route.CONNECT);
}
</script>
```

- [ ] **Step 2: Manual verify**

Completar una partida hasta game_over y confirmar que se navega a `/end` mostrando ganador.

- [ ] **Step 3: Report diff**

---

## Task 23: Capacitor + Android setup

**Files:**
- Generado: `client/src-capacitor/`, `client/src-capacitor/android/`
- Modificar: `client/src-capacitor/android/app/src/main/res/xml/network_security_config.xml`

- [ ] **Step 1: Añadir Capacitor mode**

```bash
cd client
quasar mode add capacitor
# Responder al wizard: appId com.parques.game, appName "Parqués"
```

- [ ] **Step 2: Añadir Android platform**

```bash
cd client/src-capacitor
npx cap add android
```

- [ ] **Step 3: Configurar cleartext WS para dev LAN**

Crear `client/src-capacitor/android/app/src/main/res/xml/network_security_config.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
  <base-config cleartextTrafficPermitted="true">
    <trust-anchors>
      <certificates src="system" />
    </trust-anchors>
  </base-config>
</network-security-config>
```

Editar `client/src-capacitor/android/app/src/main/AndroidManifest.xml`, añadir al `<application>`:

```xml
android:networkSecurityConfig="@xml/network_security_config"
android:usesCleartextTraffic="true"
```

- [ ] **Step 4: Build APK debug**

```bash
cd client
npm run build:android
# Esto ejecuta: quasar build -m capacitor -T android
```

Expected: APK generado en `client/src-capacitor/android/app/build/outputs/apk/debug/app-debug.apk`.

- [ ] **Step 5: Test manual del APK (opcional, requiere Android device)**

Si hay un dispositivo disponible:
```bash
adb install client/src-capacitor/android/app/build/outputs/apk/debug/app-debug.apk
```

En el dispositivo, abrir "Parqués", ingresar la IP LAN del PC (ej. 192.168.1.42) y el puerto 5001 → conectar → jugar.

Si no hay dispositivo disponible, este step se marca DONE_WITH_CONCERNS y se valida después manualmente.

- [ ] **Step 6: Report diff**

---

## Task 24: Smoke integración — 2 clientes completan una partida

- [ ] **Step 1: Arrancar stack**

Terminal 1: `.venv/bin/python -m server`
Terminal 2: `cd client && npm run dev`

- [ ] **Step 2: Flujo completo con 2 pestañas browser**

1. Tab 1 → `/connect` → localhost/5001/"Alice" → Conectar.
2. Tab 2 → `/connect` → localhost/5001/"Bob" → Conectar.
3. Tab 1 (host) y Tab 2: select_color rojo y azul.
4. Tab 1: click "Iniciar partida". Ambos ven el tablero.
5. Ambos lanzan dados iniciales → quien gane tira y mueve.
6. Completar varias jugadas: exit jail con pares, captura, home stretch, reach goal.
7. Simular triple par y coronación.
8. Continuar hasta `game_over`.
9. Ambos ven `/end` con el ganador.

Si algún paso rompe, crear una task de fix específica con el síntoma y proceder.

- [ ] **Step 3: Report diff (si hubo fixes)**

---

## Task 25: Cobertura + lint + typecheck final

- [ ] **Step 1: Vitest coverage**

```bash
cd client && npm run test:coverage
```

Expected: cobertura ≥70% en `src/stores/**` y `src/composables/**`.

Si alguna métrica falla, añadir 1-2 tests enfocados en el archivo bajo el target.

- [ ] **Step 2: Typecheck limpio**

```bash
cd client && npm run typecheck
```

Expected: 0 errores.

- [ ] **Step 3: Lint limpio**

```bash
cd client && npm run lint
```

Expected: 0 errores. Si hay warnings por `any` no justificado → arreglarlos.

- [ ] **Step 4: Pytest full suite verde**

```bash
cd /home/cris/Documents/sistemas-distribuidos/sd-parques
.venv/bin/pytest -q
```

Expected: `136 passed` (motor + server + WS bridge tests).

- [ ] **Step 5: Report diff final**

---

## Resumen de tareas

| # | Tarea | Archivos clave |
|---|---|---|
| 1 | WS bridge: dep + scaffold | `pyproject.toml`, `server/ws_bridge.py` |
| 2 | WS bridge: WebSocketConnection adapter | `server/ws_bridge.py` |
| 3 | WS bridge: start_ws_listener | `server/ws_bridge.py` |
| 4 | WS bridge: integrar en `__main__` | `server/__main__.py` |
| 5 | WS bridge: E2E test TCP + WS | `tests_server/test_ws_bridge.py` |
| 6 | Scaffold cliente Quasar TS | `client/` |
| 7 | tsconfig + ESLint + Vitest config | `client/tsconfig.json`, `.eslintrc.cjs`, `vitest.config.ts`, `package.json` |
| 8 | types/domain + types/protocol | `client/src/types/*.ts` |
| 9 | connectionStore + tests | `client/src/stores/connection.*` |
| 10 | lobbyStore + tests | `client/src/stores/lobby.*` |
| 11 | gameStore + factories + tests | `client/src/stores/game.*`, `src/test-utils/factories.ts` |
| 12 | useServerProtocol + tests | `client/src/composables/useServerProtocol.*` |
| 13 | useBoardGeometry + tests | `client/src/composables/useBoardGeometry.*` |
| 14 | Router + Route enum + guards | `client/src/router/*` |
| 15 | MainLayout + app.scss | `client/src/layouts/MainLayout.vue`, `src/css/app.scss` |
| 16 | ConnectPage | `client/src/pages/ConnectPage.vue` |
| 17 | LobbyPage | `client/src/pages/LobbyPage.vue` |
| 18 | BoardCanvas (SVG estático) | `client/src/components/BoardCanvas.vue` |
| 19 | PieceToken + tests | `client/src/components/PieceToken.*` |
| 20 | DiceRoller + PlayerList + TurnBanner | `client/src/components/*.vue` |
| 21 | GamePage (integración) | `client/src/pages/GamePage.vue` |
| 22 | EndPage | `client/src/pages/EndPage.vue` |
| 23 | Capacitor + Android setup + APK build | `client/src-capacitor/` |
| 24 | Smoke manual: 2 clientes una partida | — |
| 25 | Cobertura + typecheck + lint | — |

**Criterios de módulo #3 terminado:**
- `.venv/bin/pytest` verde (motor + server + WS bridge).
- `cd client && npm test` verde con cobertura ≥70% en `stores/` y `composables/`.
- `cd client && npm run typecheck` limpio.
- `cd client && npm run lint` limpio; sin `any` sin justificar.
- Dos pestañas del browser pueden completar una partida.
- APK Android construido; idealmente probado en un dispositivo LAN.
