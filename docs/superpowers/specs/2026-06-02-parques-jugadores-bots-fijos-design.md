# Diseño — Modelo de jugadores: 2 humanos + 2 bots fijos

**Fecha:** 2026-06-02
**Sub-proyecto:** A (de 3: A jugadores/bots · B recomendaciones · C app móvil)
**Estado:** aprobado para implementación

## Contexto y motivación

Hoy el lobby admite hasta 4 jugadores y hasta 3 bots que el *host* agrega/quita
manualmente con los comandos `add_bot` / `remove_bot`. El requerimiento del curso
cambia este modelo: la partida debe ser de **2 jugadores humanos como máximo** y
los puestos restantes los ocupan **bots fijos por defecto**, sin posibilidad de
agregarlos o quitarlos manualmente.

## Requerimientos

1. **Máximo 2 jugadores humanos** por partida.
2. **2 bots fijos** siempre presentes, con nombres **Camila** y **Bryan**.
3. **Eliminar** los comandos `add_bot` y `remove_bot` (servidor, protocolo y cliente).
4. Los bots existen en el lobby **desde el inicio** (no se inyectan al arrancar).
5. El **host (1 humano)** puede iniciar la partida aunque no llegue el segundo humano.

## Decisiones de diseño

- **Asignación de colores (intercalada):**
  - Camila = `GREEN`
  - Bryan = `YELLOW`
  - Humanos eligen entre `RED` y `BLUE`.
  - Orden de turnos resultante: `RED` (humano) → `GREEN` (Camila) → `BLUE` (humano) → `YELLOW` (Bryan).
- **Composición de partida:** siempre 2 bots + 1 ó 2 humanos ⇒ 3 ó 4 jugadores
  (el `core` ya soporta 2–4 jugadores).
- **Inicio:** basta **1 humano con color asignado** para que el host pueda iniciar.
  Si solo hay 1 humano, su color humano libre (RED o BLUE) queda sin usar y la
  partida corre con 3 jugadores.
- **Dónde viven los bots (Opción 1):** el `Lobby` se construye ya con los 2 bots
  sembrados. Es la única fuente de verdad; los bots nunca se quitan manualmente.
- **Cierre del lobby:** cuando se va el **último humano** del lobby, el lobby se
  **reinicia limpio**: se descarta el `Lobby` actual y se recrea uno nuevo y vacío
  (con los 2 bots fijos sembrados de nuevo), listo para nuevos jugadores sin
  reiniciar el servidor. Coherente con el `_reset_to_lobby()` existente. (No se
  pasa a fase `CLOSED`.)

## Cambios por capa

### `server/lobby.py`

- Constantes:
  - `MAX_PLAYERS = 4` (sin cambio).
  - **Nueva** `MAX_HUMANS = 2`.
  - **Nueva** `FIXED_BOTS: dict[Color, str] = {Color.GREEN: "Camila", Color.YELLOW: "Bryan"}`.
  - **Eliminar** `MAX_BOTS` y `_BOT_NAME_BY_COLOR`.
- `Lobby.__init__` / `default_factory`: **siembra** los 2 bots como `LobbyPlayer`
  con `conn_id = f"{BOT_CONN_PREFIX}{color.value}"` (`bot:green`, `bot:yellow`),
  `is_bot=True`, `is_host=False` y su `color` ya asignado.
- **Eliminar** métodos `add_bot`, `remove_bot`, `clear_bots`.
- `join()`:
  - Rechaza con `LobbyFull("máximo 2 jugadores")` cuando ya hay 2 humanos
    (contar solo `not p.is_bot`).
  - Mantiene la invariante "host siempre humano" y el rechazo por nombre duplicado.
- `can_start()`:
  - Al menos **1 humano** presente.
  - **Todos** los humanos tienen color asignado (los bots ya lo tienen por construcción).
  - (Ya no se exige rango 2–4 sobre el total porque los 2 bots siempre están.)
- `available_colors()`: sin cambios de lógica — devolverá `RED`/`BLUE` mientras
  los humanos no los tomen, porque `GREEN`/`YELLOW` están ocupados por los bots.
- `leave()`: sin cambios de firma; quita al jugador y reasigna host a otro humano
  si lo había. La decisión de "reiniciar el lobby cuando no quedan humanos" vive en
  el `Server` (ver abajo), no en el `Lobby`.

### `server/server.py`

- `_dispatch_lobby`: **eliminar** las ramas `elif t == "add_bot"` y
  `elif t == "remove_bot"`.
- Rama `start_game`: ajustar el mensaje de error de `can_start` a algo como
  `"se necesita al menos 1 jugador con color asignado"`.
- **Cierre del lobby (último humano):** centralizar en un helper
  `_reset_lobby_if_no_humans()` (requiere `self.lock`): si `self.phase is LOBBY`
  y no queda ningún humano en `self.lobby.players()`, reemplazar
  `self.lobby = Lobby()` (se re-siembra con los 2 bots) y loguear el reinicio.
  Llamarlo tras `lobby.leave(...)` en:
  - `_on_disconnect` (rama `LOBBY`) — **reemplaza** el bloque actual de
    `clear_bots()` (`server.py:160-164`).
  - la rama `elif t == "leave"` de `_dispatch_lobby`.
- El resto (`_lobby_update`, `_start_game`, broadcast) no cambia: los bots ya
  vienen en `self.lobby.players()`.

### `server/protocol.py`

- Quitar `"add_bot"` y `"remove_bot"` de `COMMAND_SCHEMAS`.

### Cliente (`client/`)

- `src/types/protocol.ts`: eliminar los tipos de mensaje `add_bot` y `remove_bot`.
- `src/composables/useServerProtocol.ts`: eliminar las funciones `send*` para
  agregar/quitar bot.
- `src/pages/LobbyPage.vue`: eliminar los controles de agregar/quitar bot; los bots
  llegan automáticamente vía `lobby_update`. La selección de color debe ofrecer solo
  los colores disponibles (`RED`/`BLUE`).
- `src/stores/lobby.ts`: ajustar si expone acciones de add/remove bot.

## Manejo de errores

| Situación | Código | Mensaje |
|---|---|---|
| 3.er humano intenta unirse | `LOBBY_FULL` | "máximo 2 jugadores" |
| `start_game` sin humano con color | `FORBIDDEN` | "se necesita al menos 1 jugador con color asignado" |
| `start_game` por no-host | `FORBIDDEN` | "solo el host puede iniciar la partida" (sin cambio) |
| Comando `add_bot`/`remove_bot` entrante | `BAD_MESSAGE` (`unknown type`) | rechazado por `validate_command` |

## Estrategia de pruebas (TDD — tests primero)

Backend (reescribir/ajustar al nuevo modelo):

- `tests_server/test_lobby_bots.py`: los 2 bots existen al crear el `Lobby`;
  ya no hay `add_bot`/`remove_bot`/`clear_bots`.
- `tests_server/test_lobby.py`: `join` rechaza al 3.er humano; `can_start` con
  1 humano + 2 bots; `available_colors` = `RED`/`BLUE`.
- `tests_server/test_protocol_bots.py` (o `test_protocol.py`): `add_bot`/`remove_bot`
  ya no son tipos válidos.
- `tests_server/test_server_bots.py`: `start_game` con 1 humano funciona; las ramas
  de add/remove bot devuelven error de tipo desconocido.
- `tests_server/test_session_bots.py`: una sesión iniciada contiene a Camila (GREEN)
  y Bryan (YELLOW) como entradas `is_bot=True`.
- `tests_server/test_server_bots.py` (o `test_server.py`): al irse el último humano
  del lobby (vía `leave` y vía desconexión), el lobby se reinicia limpio — vuelve a
  tener exactamente los 2 bots, sin humanos ni host; el servidor sigue en fase
  `LOBBY` (no `CLOSED`).

Cliente:

- `src/stores/lobby.test.ts`: el store refleja 2 bots fijos; sin acciones de
  add/remove bot.

Criterio de aceptación: `python -m pytest tests/ tests_server/` y
`cd client && npm run typecheck && npm test` pasan sin fallos.

## Fuera de alcance (otros sub-proyectos)

- **B — Recomendaciones:** mejora del `recommender` / sugerencias (a definir con
  detalle más adelante).
- **C — App móvil:** build Capacitor/Android.
