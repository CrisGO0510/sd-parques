# Parqués UI (Quasar + Android) — Spec de Diseño

**Fecha:** 2026-04-21
**Autor:** CrisGO
**Estado:** Propuesto
**Módulo:** #3 de la ruta incremental (ver `## Contexto`)

## Resumen

Cliente gráfico del juego Parqués implementado con Quasar v2 + Vue 3 + TypeScript estricto + Pinia, consumiendo el servidor del módulo #2 por WebSocket. Se empaqueta con Capacitor para generar un APK Android nativo desde el primer día. El servidor existente recibe un bridge WebSocket (`server/ws_bridge.py`) para aceptar conexiones del navegador/app sin perder el TCP crudo del módulo #2. Mobile-first adaptive: el layout prioriza el viewport de teléfono y se expande a paneles laterales en desktop. No tiene persistencia en BD, autenticación, estadísticas, Berkeley ni recomendador — cada uno es un módulo aparte.

Convenciones del proyecto: **identificadores, comentarios y mensajes de protocolo en inglés**, **documentación en español**. Para el cliente: **TypeScript estricto** (`strict: true`, sin `any` sin justificación), **no magic strings** (todo símbolo va en enum o `as const`).

## Contexto

Proyecto final de Sistemas Distribuidos (UTP, semestre 2026-1). Este es el módulo #3. La hoja de ruta se actualiza al absorber la bonificación del APK Android en este módulo — de 10 módulos iniciales queda en 9:

1. ✅ **Reglas del juego en Python puro** — `core/` (spec: `docs/superpowers/specs/2026-04-19-parques-core-design.md`).
2. ✅ **Servidor TCP + threads** — `server/` (spec: `docs/superpowers/specs/2026-04-20-parques-server-design.md`).
3. **UI Quasar mobile + APK Android** ← este spec.
4. Persistencia (BD local SQLite).
5. Autenticación.
6. Estadísticas y ranking.
7. Sincronización de relojes (Berkeley).
8. Recomendador.
9. Despliegue en nube (bonificación del enunciado).

Decisiones previas que enmarcan este módulo:

- **Bridge WebSocket al servidor TCP existente** (opción A del brainstorming) — un solo proceso `python -m server` acepta TCP crudo (por compatibilidad con clientes Python) y WebSocket (para el navegador/Android). Ambas conexiones comparten el `Server` singleton y el lock global.
- **Capacitor + Android desde el inicio.** APK nativo es output de build estándar, no bono opcional al final.
- **TypeScript estricto + enums.** Reglas persistentes guardadas en memoria del proyecto.

Fuente de verdad del protocolo: `server/protocol.py` del módulo #2. El cliente refleja exactamente esos enums y shapes en `src/types/`.
Fuente de verdad del dominio: `core/entities.py` del módulo #1 (Color, PieceState, GamePhase, MoveAction). El cliente define enums espejo.
Fuente de verdad de requisitos del curso: `proyecto_final_distribuidos_2026-1.pdf` — el enunciado explícitamente acepta "clientes web" y considera el APK Android como bonificación (nota 5.0).

## Alcance

**Incluye:**

- Cliente Quasar v2 + Vue 3 + TypeScript estricto + Pinia + Capacitor + Android.
- 4 rutas Vue Router: `/connect`, `/lobby`, `/game`, `/end`.
- Componentes: `BoardCanvas` (SVG), `DiceRoller`, `PlayerList`, `PieceToken`, `TurnBanner`.
- Composables: `useServerProtocol`, `useBoardGeometry`.
- 3 stores Pinia: `connection`, `lobby`, `game`.
- Tablero SVG cruciforme fiel a la figura del enunciado.
- `server/ws_bridge.py` — bridge WebSocket añadido al servidor del módulo #2.
- Tests con Vitest sobre stores, composables y componentes con lógica.
- APK Android via Capacitor, configurado para conectar a la LAN.

**No incluye** (va en módulos posteriores, explícitamente fuera de alcance):

- Autenticación / login / tokens (módulo #5).
- Persistencia del estado en base de datos (módulo #4).
- Estadísticas entre partidas, ranking global (módulo #6).
- Sincronización de relojes Berkeley (módulo #7).
- Recomendador de jugadas (módulo #8) — hay un botón "Pedir recomendación" en la UI que queda deshabilitado con tooltip "Disponible en módulo #8".
- Despliegue en nube con TLS (módulo #9).
- E2E tests con Playwright/Cypress.
- Reconexión automática con token de sesión (el módulo #2 explícitamente no la tiene).
- Validación runtime de payloads del servidor (se confía en el server; si manda basura, la UI truena).

## Decisiones de diseño tomadas en brainstorming

| Tema | Decisión | Razón |
|---|---|---|
| Bridge navegador↔servidor | **Listener WebSocket en el mismo proceso Python** | Un solo servicio, integración trivial con el `Server` existente |
| Modo de partida | **Host inicia con `start_game`** (heredado del módulo #2) | Ya decidido |
| Rutas del cliente | **4 rutas Vue Router** | Navegación explícita y guards simples |
| Render del tablero | **SVG** (no Canvas, no HTML) | Vue + SVG declarativo, interactividad por elemento, animación con CSS transform |
| Layout visual | **Cruciforme fiel al enunciado** | Lo que espera el profesor ver |
| Persistencia cliente | **localStorage de host/port/username**, sin auto-reconexión | UX simple, sin complicar el módulo #2 |
| Lenguaje | **TypeScript estricto** (`strict: true`, `noImplicitAny`, `any` solo con justificación) | Regla persistente del usuario |
| Magic strings | **Enums siempre** para tipos, códigos, estados, rutas | Regla persistente del usuario |
| Mobile-first | **Sí** — Capacitor/Android desde el inicio, no bono final | Viewport de teléfono prioritario, desktop adaptive |
| Testing | **Vitest sobre stores y composables** (≥70%), componentes con lógica; páginas manuales | YAGNI en UI; E2E con browser fuera de alcance |
| Validación runtime del protocolo | **Sin validación** — confiar en el servidor | Tests E2E del módulo #2 ya garantizan shape correcta |

## Estructura del proyecto

```
sd-parques/
├── core/                             # motor (intacto)
├── server/                           # TCP server existente
│   ├── ...                           # todo lo del módulo #2
│   └── ws_bridge.py                  # NUEVO — listener WebSocket
├── client/                           # NUEVO — Quasar + Vue 3 + TS
│   ├── src/
│   │   ├── boot/
│   │   │   └── pinia.ts
│   │   ├── components/
│   │   │   ├── BoardCanvas.vue
│   │   │   ├── DiceRoller.vue
│   │   │   ├── PlayerList.vue
│   │   │   ├── PieceToken.vue
│   │   │   └── TurnBanner.vue
│   │   ├── composables/
│   │   │   ├── useServerProtocol.ts
│   │   │   └── useBoardGeometry.ts
│   │   ├── css/
│   │   │   └── app.scss
│   │   ├── layouts/
│   │   │   └── MainLayout.vue
│   │   ├── pages/
│   │   │   ├── ConnectPage.vue
│   │   │   ├── LobbyPage.vue
│   │   │   ├── GamePage.vue
│   │   │   └── EndPage.vue
│   │   ├── router/
│   │   │   ├── index.ts
│   │   │   └── routes.ts
│   │   ├── stores/
│   │   │   ├── connection.ts
│   │   │   ├── lobby.ts
│   │   │   └── game.ts
│   │   ├── test-utils/
│   │   │   ├── factories.ts
│   │   │   └── mockWebSocket.ts
│   │   └── types/
│   │       ├── protocol.ts           # ClientCommand/ServerEvent + enums
│   │       └── domain.ts             # Color, PieceState, GamePhase, MoveAction, DTOs
│   ├── src-capacitor/                # generado por quasar mode add capacitor
│   │   └── android/                  # generado por npx cap add android
│   ├── public/
│   ├── index.html
│   ├── quasar.config.ts
│   ├── tsconfig.json                 # strict: true
│   ├── package.json
│   ├── .eslintrc.cjs
│   └── vitest.config.ts
├── tests/                            # tests del motor
├── tests_server/                     # tests del server + test nuevo del WS bridge
└── pyproject.toml                    # + `websockets` como optional dep "ws"
```

**Decisiones de layout:**

1. **`client/` paralelo a `server/`.** Dos subproyectos, no monorepo con tooling. Cada uno se instala y corre aparte.
2. **`src/types/`** como único punto de verdad de tipos del wire. Nada inline en componentes.
3. **Componentes chicos y focalizados.** `PieceToken` renderiza una ficha; `BoardCanvas` orquesta el tablero; `TurnBanner` aparte para reutilizar.
4. **Composables** para lógica reutilizable (`useServerProtocol`, `useBoardGeometry`).
5. **3 stores Pinia por dominio de estado**: connection, lobby, game — no un mega-store monolítico.

**Dependencias externas añadidas:**

- Python: `websockets>=13` como extra `ws` en `pyproject.toml`. `pip install -e '.[dev,ws]'`.
- Node: las que trae `create-quasar` con template TS (Vitest, ESLint, TypeScript). Sin axios, sin `socket.io-client`, sin librerías de animación extra.

## Bridge WebSocket (`server/ws_bridge.py`)

### Objetivo

El mismo proceso `python -m server` debe aceptar **dos** tipos de conexión compartiendo estado y lock global:

1. **TCP crudo** (módulo #2) — clientes Python como los tests.
2. **WebSocket** (nuevo) — navegador y Android via Capacitor.

### Arquitectura

- **Thread principal / TCP loop** — `accept()` de sockets crudos. Sin cambios respecto al módulo #2.
- **Thread WS listener** — `websockets.serve()` dentro de un `asyncio.new_event_loop()` corriendo en un thread dedicado. Al arrancar el server, se lanza con `start_ws_listener(server, host, port_ws)`.
- **Adapter `WebSocketConnection`** — expone la misma interfaz pública que `server.connection.ClientConnection`:
  - `conn_id: str`
  - `readline() -> bytes` (bloqueante; espera el próximo frame WS y lo convierte a bytes con `\n`).
  - `send(data: bytes) -> None` (envía frame WS de texto con el JSON, sin el `\n`).
  - `close() -> None`.

Esto permite que el `Server._run_client_loop` del módulo #2 trabaje sin distinguir el tipo de transporte — solo usa la interfaz de `ClientConnection`.

### Integración asyncio ↔ threads

`_run_client_loop` es síncrono y bloqueante (usa `readline` bloqueante). Para que conviva con el event loop asyncio que maneja WebSocket:

- El handler asyncio (`async def handler(ws)`) recibe el WS.
- Crea un `WebSocketConnection(ws, conn_id=...)`.
- Spawnea `_run_client_loop` en un thread aparte con `loop.run_in_executor(None, server._run_client_loop, conn)`.
- Paralelamente, una corrutina asyncio lee frames de `ws` y los encola en `WebSocketConnection._incoming` (una `queue.Queue` threadsafe). `readline()` del adapter pops de esa queue.
- El `send` del adapter usa `asyncio.run_coroutine_threadsafe(ws.send(text), loop)` para volver al event loop.

### CLI extendido

```
python -m server [--host HOST] [--port-tcp PORT] [--port-ws PORT] [--no-ws] [--log-level LEVEL]
```

- `--port-tcp` default `5000`.
- `--port-ws` default `5001`.
- `--no-ws` desactiva el bridge (útil para tests que solo necesitan TCP).

### Tests del bridge

- `tests_server/test_ws_bridge.py` — un test E2E mínimo:
  1. Arranca el server con TCP + WS en puertos dinámicos (0).
  2. Abre un cliente TCP (socket crudo) + un cliente WS (usando la librería `websockets` en modo cliente, también async; el test usa `asyncio.run` local).
  3. Ambos hacen `join` con usernames distintos y reciben `welcome` + `lobby_update`.
  4. Cuando uno dispara `start_game`, ambos reciben `game_started`.

Esto demuestra que TCP y WS conviven, comparten el singleton y los eventos se broadcasean a ambos.

## Types compartidos (`src/types/`)

### `src/types/domain.ts` — enums espejo del motor y DTOs

Contiene **enums** para `Color`, `PieceState`, `GamePhase`, `MoveAction` con los mismos valores string que los enums Python del motor. Y **interfaces** para los DTOs que serializan las entidades Python: `PieceDto`, `PlayerDto`, `GameStateDto`, `MoveDto`, `MoveResultDto`, `LobbyPlayerDto`.

Notas clave:

- `initial_rolls: Record<string, number>` — los keys de JSON son strings aunque Python tenga `dict[int, int]`. El cliente los parsea con `Number(key)` al consumirlos.
- **Nomenclatura snake_case en DTOs.** Todos los campos de DTOs conservan el snake_case con que viajan por el wire (`piece_index`, `available_colors`, `winner_username`, etc.). El cliente **no** los re-casea a camelCase — mantener coherencia con el servidor Python y evitar mapping layer innecesario.
- `winner: number | null` (índice del jugador ganador, no el username).
- Los enums usan string values (`RED = 'red'`), no números, para que `JSON.stringify(myColor)` dé el string esperado.

### `src/types/protocol.ts` — enums + discriminated unions

Enums:

- `ClientCommandType` (9 valores: JOIN, SELECT_COLOR, START_GAME, ROLL_INITIAL, ROLL_DICE, MOVE_PIECE, SKIP_TURN, CROWN_PIECE, LEAVE).
- `ServerEventType` (10 valores: WELCOME, LOBBY_UPDATE, GAME_STARTED, STATE_UPDATE, INITIAL_ROLL, DICE_RESULT, AVAILABLE_MOVES, MOVE_APPLIED, GAME_OVER, ERROR).
- `ErrorCode` (7 valores: BAD_MESSAGE, NOT_AUTHENTICATED, DUPLICATE_PLAYER, WRONG_PHASE, INVALID_MOVE, FORBIDDEN, GAME_ENDED).

Discriminated unions:

- `ClientCommand` — uno por cada `ClientCommandType`, con sus campos tipados.
- `ServerEvent` — uno por cada `ServerEventType`, con sus payloads tipados (referenciando DTOs de `domain.ts`).

Esto permite type narrowing exhaustivo en `switch (event.type)` y `exhaustiveness checking` con una función `assertNever(event: never): never`.

### Reglas de uso

- **Nunca** comparar un campo `type` con un literal string (`event.type === 'welcome'` ❌). Siempre con el enum (`event.type === ServerEventType.WELCOME` ✓).
- ESLint con `no-restricted-syntax` o similar valida esto en CI local (`npm run lint`).

## Stores Pinia y composables

### `stores/connection.ts`

Encapsula el WebSocket + credenciales de conexión.

**Estado:**
- `status: ConnectionStatus` (DISCONNECTED, CONNECTING, CONNECTED, ERROR).
- `host: string`, `port: number`, `username: string`, `errorMessage: string | null`.

**Métodos:**
- `connect(host, port, username) → Promise<void>` — crea WebSocket, setea status, espera `onopen`; persiste credenciales en localStorage tras conexión exitosa.
- `send(cmd: ClientCommand) → void` — serializa con JSON y manda por el WS.
- `onEvent(handler: (e: ServerEvent) => void) → () => void` — registra un handler; retorna un unsubscribe.
- `disconnect() → void` — cierra el WS, resetea status.

El `WebSocket` instance vive **fuera** del estado reactivo (ref) porque no es serializable y no debe observarse.

### `stores/lobby.ts`

Estado del lobby pre-partida.

**Estado:**
- `players: LobbyPlayerDto[]`, `availableColors: Color[]`, `isHost: boolean`, `myColor: Color | null`.

**Getters:**
- `canStart: boolean` — `players.length ≥ 2 && todos tienen color`.

**Métodos:**
- `reset() → void`.
- `updateFromLobbyUpdate(players, availableColors) → void`.

### `stores/game.ts`

Estado durante la partida.

**Estado:**
- `state: GameStateDto | null`, `availableMoves: MoveDto[]`, `myColor: Color | null`, `winnerUsername: string | null`.

**Getters:**
- `currentTurnColor: Color | null`.
- `isMyTurn: boolean`.
- `phase: GamePhase | null`.
- `dice: [number, number] | null`.

**Métodos:**
- `reset() → void`.
- `updateFromStateUpdate(state) → void`.
- `setAvailableMoves(moves) → void`.
- `setWinner(username) → void`.

### `composables/useServerProtocol.ts`

Convenience wrapper sobre `connectionStore` que permite a componentes declarar handlers tipados por evento:

```ts
const { send } = useServerProtocol({
  [ServerEventType.LOBBY_UPDATE]: (e) => lobbyStore.updateFromLobbyUpdate(e.players, e.available_colors),
  [ServerEventType.GAME_STARTED]: () => router.push(Route.GAME),
});
```

El handler de cada evento recibe un objeto tipado con **solo** los campos de ese evento (via `Extract<ServerEvent, { type: K }>`). `onUnmounted` automáticamente hace unsubscribe.

### `composables/useBoardGeometry.ts`

Funciones **puras** que mapean datos del dominio a coordenadas SVG:

- `circuitCellCenter(position: number) → Point`.
- `homeStretchCellCenter(color: Color, index: number) → Point`.
- `jailSlotCenter(color: Color, slot: number) → Point`.
- `goalCenter() → Point`.

Usa constantes de layout (tamaño del tablero, offset por brazo, etc.) definidas en el mismo archivo. Testeable sin montar componente.

## Pantallas y navegación

### Enum de rutas

```ts
export enum Route {
  CONNECT = '/connect',
  LOBBY   = '/lobby',
  GAME    = '/game',
  END     = '/end',
}
```

Redirect `/ → /connect`, catchAll `/:catchAll(.*)* → /connect`.

### Router guard

`router.beforeEach` inspecciona `meta.requiresConnection`:

- Si la ruta requiere conexión y `connectionStore.status !== CONNECTED` → redirige a `Route.CONNECT`.
- Esto cubre refreshes del browser en `/lobby`, `/game`, `/end`.

### `ConnectPage.vue`

Formulario de conexión: host, port, username. Defaults desde localStorage. Validación inline (host/IP válida, port 1-65535, username 3-20 alfanuméricos+espacios).

**Flujo:**
1. Click "Conectar" → `connectionStore.connect(host, port, username)`.
2. Si success → `send({ type: JOIN, username })` → al recibir `WELCOME` guarda `is_host` en `lobbyStore.isHost` → `router.push(LOBBY)`.
3. Si falla → `q-notify` con el error.
4. LocalStorage se actualiza tras éxito.

**Responsive:**
- Mobile: formulario ocupa viewport, botón grande fijo abajo.
- Desktop: card centrado de 400px.

### `LobbyPage.vue`

- Lista de jugadores (avatar del color + nombre).
- Picker de colores disponibles (los taken se ven pero deshabilitados).
- Botón "Iniciar partida" visible solo al host, habilitado cuando `canStart`.
- Para no-host: texto "Esperando al host...".

**Eventos:** `LOBBY_UPDATE` → actualizar store; `GAME_STARTED` → `push(GAME)`; `ERROR` → `q-notify`.

**Comandos:** `SELECT_COLOR`, `START_GAME` (solo host), `LEAVE` implícito por close.

### `GamePage.vue`

**Layout adaptivo (breakpoint `md`):**

Desktop:
```
┌──────────────────────────────────────────────┐
│ Header: "Tu turno" / "Turno de X"  [🟢]       │
├─────────────────────────────┬────────────────┤
│                             │ PlayerList     │
│       <BoardCanvas />       ├────────────────┤
│                             │ DiceRoller     │
│                             ├────────────────┤
│                             │ [Lanzar]       │
│                             │ [Pasar turno]  │
│                             │ [IA (pronto)]  │
└─────────────────────────────┴────────────────┘
```

Mobile:
```
┌───────────────────────┐
│ "Turno de Alice"  🟢  │
├───────────────────────┤
│                       │
│   <BoardCanvas />     │
│   (90% viewport)      │
│                       │
├───────────────────────┤
│ Bottom sheet:         │
│   PlayerList          │
│   DiceRoller          │
│   [Lanzar] [Pasar]    │
└───────────────────────┘
```

**Flujo de usuario (en tu turno):**

1. Fase `SETUP` → botón "Dado inicial" → `ROLL_INITIAL`.
2. Fase `ROLLING` → botón "Lanzar" → `ROLL_DICE`.
3. Fase `MOVING` + `availableMoves > 0` → fichas válidas con glow dorado. Click en ficha:
   - Si **una** sola Move posible con esa ficha → envía `MOVE_PIECE` directamente.
   - Si **múltiples** (distintos dados pendientes) → `q-dialog` rápido "¿Usar el 3 o el 5?".
4. Fase `MOVING` + `availableMoves == 0` → botón "Pasar turno" activo → `SKIP_TURN`.
5. Fase `CROWNING` → modal "Triple par. Elige ficha a coronar" con botones de cada ficha no-coronada del jugador → `CROWN_PIECE`.
6. Evento `GAME_OVER` → `push(END)`.

**Cuando NO es tu turno:** todos los controles deshabilitados. Board se actualiza en tiempo real por `STATE_UPDATE`.

### `EndPage.vue`

Muestra el ganador en grande + botón "Volver al menú" que hace `disconnect()` y `router.push(CONNECT)`.

### Manejo de pérdida de conexión

Si el WS se cae en medio de una partida:

- `connectionStore.status = ERROR`.
- Modal no cerrable "Conexión perdida" con un solo botón → vuelve a `/connect` y resetea los stores.

## Tablero SVG

### ViewBox y zonas

- ViewBox: `0 0 600 600` (cuadrado; se re-escala al viewport del cliente).
- **Meta:** `<circle>` en (300, 300), radio 50.
- **Cárceles:** 4 rectángulos 150×150 en las esquinas con el color del jugador en 30% de opacidad. Slots fijos 2×2 para las 4 fichas del color.
- **Rectas finales:** 4 columnas de 8 `<rect>` del color del jugador, desde el borde del cuadrante interior hasta tocar la meta.
- **Circuito principal:** 96 `<rect>` distribuidos en 4 brazos de 24 casillas cada uno.

### Asignación de brazos a colores

- Brazo 0 (N): RED exit en pos 0.
- Brazo 1 (E): BLUE exit en pos 24.
- Brazo 2 (S): GREEN exit en pos 48.
- Brazo 3 (W): YELLOW exit en pos 72.

Las entradas a recta final (pos 71, 95, 23, 47 del `board.py`) son la última celda del carril interior, justo antes de desviarse a las 8 celdas de la recta final del color correspondiente.

### Mapping `circuit_position → (x, y)`

`useBoardGeometry.ts::circuitCellCenter(position)` implementa el mapeo con:

1. `arm = Math.floor(position / 24)` (0..3).
2. `cell = position % 24` (0..23).
3. Dentro del brazo, las 24 celdas se distribuyen en una "L" que bordea la cárcel: 8 bajando el carril exterior, 8 cruzando el fondo, 8 subiendo el carril interior.
4. La función aplica offset + rotación según `arm`.

Los números exactos (tamaño de celda, offsets) se calibran durante implementación. No hay matemática conceptualmente difícil, solo constantes.

### Casillas de seguro

Los 12 seguros (incluyen los 4 exits) se distinguen visualmente:

- Seguros "neutros" (8 casillas no-exit): fondo verde claro + icono de escudo SVG pequeño.
- Exits (4 casillas): fondo del color del jugador al 100% opaco + icono de escudo más grande.

### Fichas

Cada ficha es un `<circle>` del color del jugador, radio 18:

- `IN_JAIL` → posicionada en uno de los 4 slots de la cárcel según `piece.index`.
- `ON_BOARD` → centrada en `circuitCellCenter(circuit_position)`.
- `IN_HOME_STRETCH` → centrada en `homeStretchCellCenter(color, home_stretch_position)`.
- `CROWNED` → **no se dibuja** en el tablero. El `PlayerList` muestra el contador de fichas coronadas por jugador.

### Interactividad

Cada `<circle>` tiene un `:class="{ selectable: isSelectable(piece) }"` y un `@click="onPieceClick(piece)"`:

- `isSelectable(piece)` = `gameStore.isMyTurn && gameStore.availableMoves.some(m => m.piece_index === piece.index)`.
- CSS: `.selectable { filter: drop-shadow(0 0 6px gold); cursor: pointer; }`.
- En mobile, el radio `18` garantiza touch target cómodo (área total ~36×36px); se puede subir a `22` si hace falta en dispositivos densos.

### Animación de movimiento

`style="transition: cx 0.3s ease, cy 0.3s ease;"` sobre cada círculo. Cuando un `STATE_UPDATE` cambia `piece.circuit_position` o `piece.home_stretch_position`, Vue re-renderiza con nuevas `cx/cy` y la transición CSS anima el recorrido.

Captura: la ficha rival cambia de `ON_BOARD` a `IN_JAIL` con `circuit_position = null`. El render la reposiciona al slot de cárcel. La transición la anima desde la casilla hasta la cárcel.

## Testing

### Stack

- Vitest (incluido con Quasar v2).
- `@vue/test-utils` para componentes.
- `happy-dom` como DOM simulado.
- Todos los tests en `.test.ts`.
- `vitest.config.ts` scopea la cobertura explícitamente: `coverage.include: ['src/stores/**', 'src/composables/**']` para medir solo lo que tiene meta ≥70%. Otros archivos no cuentan.

### Alcance

| Nivel | ¿Testea? | Meta |
|---|---|---|
| Stores Pinia (connection, lobby, game) | ✅ | ≥70% |
| Composables (useServerProtocol, useBoardGeometry) | ✅ | ≥70% |
| Componentes con lógica (PieceToken, DiceRoller) | ✅ | Casos clave |
| Páginas completas (Connect/Lobby/Game/End) | ❌ | Validación manual con `quasar dev` |
| E2E con browser | ❌ | Fuera de alcance |

### Fixtures compartidos

- `src/test-utils/factories.ts` — builders con defaults + overrides parciales (`makePlayer`, `makePiece`, `makeFakeState`).
- `src/test-utils/mockWebSocket.ts` — stub que implementa la interfaz mínima de `WebSocket` y permite al test disparar `onmessage` manualmente.

### Scripts en `client/package.json`

```json
{
  "scripts": {
    "dev":           "quasar dev",
    "build":         "quasar build",
    "build:android": "quasar build -m capacitor -T android",
    "test":          "vitest run",
    "test:watch":    "vitest",
    "test:coverage": "vitest run --coverage",
    "lint":          "eslint . --ext .ts,.vue",
    "typecheck":     "tsc --noEmit"
  }
}
```

### ESLint clave

`@typescript-eslint/no-explicit-any: 'error'`. Opcionalmente `no-restricted-syntax` que detecta literales que deberían ser enums (ej. `"join"`, `"welcome"` sueltos).

## Dev workflow y build

### Desarrollo local (2 terminales)

```bash
# Terminal 1 (repo root)
.venv/bin/python -m server --log-level INFO
# → TCP listening on 0.0.0.0:5000
# → WS  listening on 0.0.0.0:5001

# Terminal 2 (client/)
cd client
npm run dev
# → http://localhost:9000
```

Browser abre `/connect`, ingresa `localhost:5001`, juega. Una segunda pestaña del browser es el segundo jugador.

### Build web

```bash
cd client && npm run build
# → client/dist/spa/
```

SPA estática, lista para módulo #9 (deploy).

### Build Android

Primera vez:
```bash
cd client
quasar mode add capacitor
cd src-capacitor && npx cap add android
```

Ciclo normal:
```bash
cd client
npm run build:android
cd src-capacitor && npx cap open android
```

El dispositivo Android debe estar conectado por USB con debugging activo, o se instala el APK generado manualmente.

**Red:** desde Android, el host del servidor es la IP LAN del PC (ej. `192.168.1.42`), no `localhost`. El form de `/connect` lo acepta.

### Permissions Android

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
```

### Cleartext WebSocket (dev)

Android 9+ bloquea WS sin TLS por default. En dev se permite cleartext via `network_security_config.xml`:

```xml
<network-security-config>
  <base-config cleartextTrafficPermitted="true" />
</network-security-config>
```

Referenciado desde `AndroidManifest.xml` con `android:networkSecurityConfig="@xml/network_security_config"`. **Solo en dev.** En producción (módulo #9) el servidor estará detrás de HTTPS/WSS.

### `.gitignore` del cliente

```
node_modules/
dist/
src-capacitor/android/app/build/
src-capacitor/android/.gradle/
src-capacitor/android/local.properties
*.log
.quasar/
```

## Criterios de módulo #3 terminado

- `.venv/bin/pytest` verde (motor + server + WS bridge test).
- `cd client && npm test` pasa con ≥70% cobertura en `src/stores/` y `src/composables/`.
- `cd client && npm run typecheck` pasa limpio (sin warnings TS).
- `cd client && npm run lint` pasa; ningún `any` explícito sin comentario justificativo.
- `cd client && npm run dev` arranca; dos pestañas de browser pueden completar una partida.
- `cd client && npm run build:android` produce un APK; el APK instalado en un teléfono conectado a la LAN del PC puede completar una partida contra el servidor.

## Limitaciones conocidas

(Para documentar en el futuro `README.md` del proyecto, junto con las del módulo #2.)

- **Sin TLS.** Las conexiones WS van en cleartext; aceptable solo en LAN. Producción requiere un reverse proxy con HTTPS/WSS (módulo #9).
- **Sin reconexión.** Si el usuario cierra la pestaña / el dispositivo pierde red, la partida se pierde (el servidor ya así lo decidió en el módulo #2). No hay recovery por token.
- **Sin validación runtime de payloads.** Si el servidor envía algo mal-formado, la UI truena. Los tests del servidor cubren este contrato.
- **Sin offline / PWA.** La app requiere conexión al servidor siempre.
- **Sin i18n.** UI en español hardcodeado.
- **Sin accessibility (a11y) auditada.** Aria-labels, contrast ratios, keyboard navigation no son prioridad en este alcance.
- **Sin soporte de browsers antiguos.** Target: Chrome/Firefox/Safari/Edge modernos (≤2 años).
- **APK no firmado para Play Store.** El APK es debug-signable para instalación directa; publicar requiere keystore + alineación de gradle fuera de alcance.

## Asunciones pendientes de validación

1. **El profesor acepta "WebSocket" como sockets para el módulo #3.** El módulo #2 usa TCP crudo fiel al enunciado; este módulo añade WebSocket porque el navegador no puede TCP. Si el profesor aclara que solo TCP cuenta, la capa WS queda como "extra" y podemos enfatizar el TCP del módulo #2 en la demo.
2. **Layout exacto del tablero (asunción #1 del módulo #1) sigue aplicando.** Si el profesor define posiciones concretas de seguros/entradas distintas a las de `board.py`, se ajusta en el motor y la UI lo hereda sin cambios (el mapping visual depende de `useBoardGeometry`, que es puro).
3. **Los nombres de ruta (`/connect`, `/lobby`, `/game`, `/end`) son aceptables.** Alternativa: `/`, `/sala`, `/partida`, `/fin` en español. No hay preferencia explícita del usuario hasta ahora.
4. **Mobile-first aplica tanto a web como a Android.** La decisión del usuario fue "priorizar mobile"; en web el UI se re-ajusta a desktop con breakpoint `md`.

## Siguientes pasos

1. Revisión de este spec por un subagente reviewer (iterar hasta aprobación).
2. Revisión por el usuario.
3. Escritura del plan de implementación en `docs/superpowers/plans/2026-04-21-parques-ui.md` vía `superpowers:writing-plans`.
4. Ejecución del plan con TDD (test → fail → implement → pass), en el estilo de los módulos #1 y #2.
5. Al cerrar el módulo (tests verdes, APK Android funcional, partida E2E entre navegador y APK), iniciar brainstorming del módulo #4 (persistencia SQLite).
