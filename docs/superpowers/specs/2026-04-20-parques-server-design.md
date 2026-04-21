# Parqués Server — Spec de Diseño

**Fecha:** 2026-04-20
**Autor:** CrisGO
**Estado:** Propuesto
**Módulo:** #2 de la ruta incremental (ver `## Contexto`)

## Resumen

Servidor TCP en Python que expone el motor del módulo #1 a múltiples clientes a través de sockets y threading explícitos. Implementa el ciclo de vida de una partida de Parqués entre 2-4 jugadores en red: lobby de espera, inicio de partida por el host, turnos coordinados con un lock global, manejo de desconexiones con salto de turno, y cierre al terminar. No tiene interfaz gráfica (eso es el módulo #3); la única forma de probarlo en este módulo es mediante tests automatizados.

Convenciones del proyecto: **identificadores, comentarios y mensajes de protocolo en inglés**, **documentación en español**.

## Contexto

Proyecto final de Sistemas Distribuidos (UTP, semestre 2026-1). El proyecto se construye en 10 módulos incrementales; este es el #2.

Hoja de ruta actualizada:

1. ✅ **Reglas del juego en Python puro** — `core/` (spec: `docs/superpowers/specs/2026-04-19-parques-core-design.md`).
2. **Servidor + cliente de sockets** ← este spec.
3. UI gráfica (Quasar, contra el servidor).
4. Persistencia (BD local).
5. Autenticación.
6. Estadísticas y ranking.
7. Sincronización de relojes (Berkeley).
8. Recomendador.
9. Despliegue en nube (bonificación del enunciado).
10. APK Android (bonificación).

Decisiones previas que enmarcan este módulo:

-                              All parsers are up-to-date!
 **Sockets TCP crudos** (`socket` + `threading` de la stdlib). El enunciado pide literalmente *"Hilos y Sockets"*; interpretamos que la forma más fiel es `socket.AF_INET`/`SOCK_STREAM` manejado a mano, no capas sobre WebSockets o frameworks HTTP.
- **Cliente web vendrá en el módulo #3.** El navegador no puede hablar TCP crudo; ese problema se resolverá más tarde (posible proxy WebSocket↔TCP, o listener WebSocket extra en el mismo servidor). Para este módulo, el servidor es puramente TCP; los clientes de prueba son sockets Python.

Fuente de verdad para reglas: `core/` (ya implementado, 67 tests, 98% cobertura).
Fuente de verdad para requerimientos del curso: `proyecto_final_distribuidos_2026-1.pdf`.

## Alcance

**Incluye:**

- Servidor TCP con accept loop y un hilo por cliente (pattern clásico de threading).
- Protocolo JSON por líneas (NDJSON) con un set cerrado de comandos y eventos.
- `Lobby` donde los jugadores se registran con username, eligen color, y el host ordena arrancar.
- `GameSession` que envuelve `core.Game`, mapea colores ↔ conexiones y gestiona desconectados.
- `Server` que orquesta todo con un `threading.Lock` global.
- Entry point `python -m server`.
- Suite de tests en `tests_server/` (protocolo, lobby, session, integración end-to-end).

**No incluye** (va en módulos posteriores, explícitamente fuera de alcance):

- WebSocket / HTTP / cualquier protocolo que no sea TCP crudo (módulo #3 resuelve el puente al navegador).
- Interfaz gráfica (módulo #3).
- Cliente CLI interactivo — los tests automatizados son la única verificación funcional.
- Persistencia en BD (módulo #4).
- Autenticación, JWT, hashing (módulo #5).
- Estadísticas entre partidas (módulo #6).
- Sincronización Berkeley (módulo #7).
- Recomendador de jugadas (módulo #8).
- Despliegue (módulo #9-10).
- Reconexión con token / recuperación de sesión (se decidió sin reconexión: el jugador que cae pierde sus turnos).
- Soporte para múltiples partidas simultáneas (el enunciado dice *"un bloqueo para cualquier otro participante hasta que no se termine la partida actual"*, confirmando una sola partida viva).

## Decisiones de diseño tomadas en brainstorming

| Tema | Decisión | Razón |
|---|---|---|
| Protocolo de transporte | **TCP crudo** (`socket`) | Cumple "Hilos y Sockets" del enunciado de forma literal |
| Modo de arranque de partida | **Host envía `start_game`** | Flexibilidad (jugar de a 2, 3 o 4 según quienes estén); mensaje extra trivial |
| Formato de mensaje | **JSON por líneas** (NDJSON) | Estándar de facto, parseable trivialmente, debuggable |
| Desconexión durante juego | **Saltar turno del desconectado** | Simple, tradicional, sin tokens/reconexión |
| Modelo de hilos | **Uno por cliente + `threading.Lock` global** | Explícito, clásico del curso, se ve "la semaforización" pedida |
| Verificación en este módulo | **Solo tests automatizados** | Sin UI aún; CLI sería trabajo desechable |
| Contenido del lock | **Incluye los `send()` a sockets** | Garantiza orden de eventos entre transiciones; seguro en localhost/LAN con buffers TCP amplios |

## Estructura del paquete

```
sd-parques/
├── core/                         # motor (módulo #1, no se toca)
│   └── ...
├── server/                       # NUEVO
│   ├── __init__.py
│   ├── protocol.py               # mensajes constantes + encode/decode JSON + validación
│   ├── connection.py             # ClientConnection: socket + buffer readline + send
│   ├── lobby.py                  # Lobby: jugadores en espera, host, colores
│   ├── session.py                # GameSession: wraps core.Game + color→connection map + disconnected set
│   ├── server.py                 # Server: accept loop, lock global, router de mensajes
│   └── __main__.py               # entry: `python -m server` (argparse, logging)
├── tests/                        # tests del motor (existentes)
├── tests_server/                 # NUEVO
│   ├── __init__.py
│   ├── conftest.py               # fixtures: spawn server, TestClient
│   ├── test_protocol.py          # encode/decode/validación (sin sockets)
│   ├── test_lobby.py             # Lobby aislado (sin sockets)
│   ├── test_session.py           # GameSession aislada (sin sockets, usa ScriptedRandom)
│   └── test_integration.py       # E2E con sockets reales, servidor en thread
└── pyproject.toml                # existente
```

**Decisiones de layout:**

1. **`server/` separado de `core/`.** El motor es una librería pura; el servidor es una aplicación que consume esa librería. Separar responsabilidades preserva la regla del módulo #1: `core/` no importa `socket` ni `threading`.
2. **Archivos por responsabilidad**, no por entidad: protocol (pura serialización), connection (socket lifecycle), lobby (pre-partida), session (durante-partida), server (orquestador), `__main__` (CLI).
3. **`tests_server/` separado de `tests/`.** Permite correr los tests del motor en aislamiento (rápidos, sin sockets) o los del servidor por separado. `pytest` sin argumentos corre todos.

**Dependencias externas:** solo `pytest` (dev), igual que en el módulo #1. Todo lo demás es Python 3.11+ stdlib.

## Protocolo

### Envelope

Un mensaje por línea UTF-8 terminada en `\n`:

```
<json-object>\n
```

El envelope siempre tiene un campo `type` que discrimina el resto de la estructura. Resto de campos específicos a cada tipo.

### Cliente → Servidor (comandos)

| `type` | Campos | Fases en que es válido |
|---|---|---|
| `join` | `username: str` | cliente recién conectado (pre-lobby) |
| `select_color` | `color: "red"\|"blue"\|"green"\|"yellow"` | LOBBY |
| `start_game` | — | LOBBY, solo host, ≥2 jugadores con color |
| `roll_initial` | — | IN_GAME, fase SETUP |
| `roll_dice` | — | IN_GAME, fase ROLLING, turno del emisor |
| `move_piece` | `piece_index: 0..3`, `dice_value: int`, `action: MoveAction` | IN_GAME, fase MOVING, turno del emisor |
| `skip_turn` | — | IN_GAME, fase MOVING, turno del emisor (voluntario cuando no hay movimientos legales; también lo dispara el servidor internamente cuando el jugador del turno está marcado `disconnected`) |
| `crown_piece` | `piece_index: 0..3` | IN_GAME, fase CROWNING, turno del emisor |
| `leave` | — | cualquier fase |

### Servidor → Cliente (eventos)

| `type` | Destinatario | Cuándo |
|---|---|---|
| `welcome` | solo al emisor de `join` | respuesta a `join` válido; incluye `username`, `is_host` |
| `lobby_update` | broadcast a lobby | cambios en la lista de jugadores o colores |
| `game_started` | broadcast a sala | tras `start_game`; marca la transición LOBBY → IN_GAME. **No lleva el estado inicial** — inmediatamente después se emite un `state_update` con el snapshot completo |
| `initial_roll` | broadcast | tras cada `roll_initial`; incluye `player_index`, `username`, `total` |
| `dice_result` | broadcast | tras `roll_dice`; incluye `player_index`, `d1`, `d2`, `is_pair` |
| `available_moves` | solo al jugador del turno | tras `roll_dice` y tras cada `move_piece` que deje dados pendientes |
| `move_applied` | broadcast | tras `move_piece` exitoso; incluye el `Move` y el `MoveResult` |
| `state_update` | broadcast | **después de cada acción que mute estado**; incluye `Game` serializado completo |
| `game_over` | broadcast | cuando el motor marca `winner`; incluye `winner_index` y `winner_username` |
| `error` | solo al emisor ofensor | ante comando inválido o mal formado |

### Serialización del `Game`

`core.Game` es un `@dataclass` mutable. Para serializar:

1. Hacer una copia shallow sin el atributo privado `_rng` (pegado al vuelo por `new_game`).
2. `dataclasses.asdict(...)` convierte recursivamente a dict.
3. Los enums (`Color`, `GamePhase`, `PieceState`, `MoveAction`) son `str, Enum` → se serializan como strings automáticamente con `json.dumps`.

Payload ejemplo del `state_update`:

```json
{
  "type": "state_update",
  "state": {
    "phase": "rolling",
    "turn_order": [1, 0],
    "current_turn_index": 0,
    "pending_dice": [],
    "initial_rolls": {"0": 7, "1": 11},      // JSON coerce int→str en claves; el cliente debe parsear de vuelta a int
    "initial_rolls_remaining": 0,
    "consecutive_pairs": 0,
    "winner": null,
    "players": [
      {
        "name": "Alice",
        "color": "red",
        "pieces": [
          {"index": 0, "state": "in_jail", "circuit_position": null, "home_stretch_position": null},
          ...
        ]
      },
      ...
    ]
  }
}
```

### Códigos de error

El evento `error` lleva `code` canónico (para que el cliente pueda reaccionar con UI) y `message` humano:

| Código | Cuándo |
|---|---|
| `BAD_MESSAGE` | JSON inválido, `type` desconocido, campos faltantes o de tipo incorrecto |
| `NOT_AUTHENTICATED` | Cualquier comando distinto de `join` enviado antes de `join` |
| `DUPLICATE_PLAYER` | Username o color duplicado |
| `WRONG_PHASE` | Comando en fase incorrecta (ej. `roll_dice` en LOBBY) |
| `INVALID_MOVE` | `move_piece` con un `Move` no listado en `available_moves` |
| `FORBIDDEN` | Comando no permitido para el rol (ej. `start_game` siendo no-host) o lobby lleno (5to intento de join con ya 4 jugadores) |
| `GAME_ENDED` | Cualquier comando cuando el servidor está en CLOSED (único código para este caso) |

### Validación

- El servidor **no confía** en el cliente. Cada mensaje se valida completo:
  1. Parseo JSON → `BAD_MESSAGE` si falla.
  2. Presencia y tipo del campo `type` → `BAD_MESSAGE` si ausente/mal.
  3. `type` en la lista blanca → `BAD_MESSAGE` si no.
  4. Campos requeridos presentes con el tipo correcto → `BAD_MESSAGE` si no.
  5. Comando válido para la fase actual → `WRONG_PHASE` o `FORBIDDEN`.
  6. Delegación al motor → puede lanzar `WrongPhase`, `InvalidMove`, `DuplicatePlayer` → mapeados a los códigos correspondientes.

## Máquina de estados del servidor

```
   ┌──────────┐  start_game (host)  ┌─────────┐  game_over   ┌──────────┐
──►│  LOBBY   │───────────────────► │ IN_GAME │────────────► │  CLOSED  │
   └──────────┘                     └─────────┘              └──────────┘
```

**Notas:**

- El servidor arranca en `LOBBY`.
- **Capacidad del LOBBY: máximo 4 conexiones simultáneas.** Una 5ta conexión que envíe `join` recibe `FORBIDDEN` y el servidor cierra su socket.
- Transición `LOBBY → IN_GAME` es disparada por `start_game` del host. Requiere 2-4 jugadores con color asignado.
- Transición `IN_GAME → CLOSED` es disparada por `game_over` (victoria normal) o por "quedan <2 conectados" (el último conectado gana por default; si no hay ninguno conectado el servidor también cierra sin ganador).
- En `CLOSED` el proceso sigue vivo para permitir inspección de logs, pero rechaza cualquier nuevo comando con `GAME_ENDED`. No hay reset automático a LOBBY en esta iteración.

### Manejo de desconexiones

- **En LOBBY:** el servidor quita al jugador de la lista; si era host, el siguiente en orden de llegada se promueve a host; broadcastea `lobby_update`.
- **En IN_GAME:** se marca su color como `disconnected` en la `GameSession`.
  - Cuando le toque el turno al desconectado, el servidor dispara `skip_turn` automáticamente (si la fase es MOVING) o avanza el turno directamente (si es ROLLING y no ha tirado aún).
  - Emite `state_update` para que los demás vean el salto.
  - Si quedan `<2` conectados, emite `game_over` con `winner_index = último_conectado | null` y pasa a CLOSED.
- En ambos casos se cierra el socket y se elimina la `ClientConnection` de la lista activa.

## Hilos y sincronización

### Hilos existentes

| Hilo | Rol | Tiempo de vida |
|---|---|---|
| Main thread (accept loop) | `accept()` en loop, spawnea un hilo por cliente | desde `python -m server` hasta Ctrl+C |
| Client threads (N) | uno por conexión; lee `readline`, parsea, dispatche | desde `accept()` hasta cierre/desconexión |

**No hay** thread pool, async ni selector multiplexing. Un hilo por cliente es el patrón explícito que el enunciado espera.

Todos los client threads son `daemon=True` para que al Ctrl+C mueran con el proceso.

### Lock global

Un único `threading.Lock` en `Server` protege:

- `Lobby` (lista de jugadores, host, colores).
- `GameSession` activa si existe.
- Fase del servidor (LOBBY / IN_GAME / CLOSED).

**Fuera del lock:** parseo JSON y validación de shape (operaciones puras sobre el mensaje entrante, no tocan estado).

**Dentro del lock:** mutación de estado **y** emisión de eventos (`sendall`). Sin esto, dos transiciones concurrentes podrían intercalar sus eventos y corromper el orden que ven los clientes.

### Patrón de manejo de mensaje

```python
def _handle_message(self, conn: ClientConnection, raw: bytes) -> None:
    # Fuera del lock: parseo y validación pura.
    try:
        msg = decode(raw)        # json.loads + validate shape
    except ProtocolError as e:
        conn.send_error(code="BAD_MESSAGE", message=str(e))
        return

    # Sección crítica.
    with self.lock:
        try:
            self._dispatch(conn, msg)
        except DomainError as e:
            conn.send_error(code=_domain_error_code(e), message=str(e))
```

`_dispatch` ejecuta la transición (llamando al motor si corresponde) y emite los eventos relevantes, todo mientras mantiene el lock. `conn.send_error` puede llamarse desde fuera del lock porque solo impacta a un cliente.

### Detección de desconexión

Cada client thread corre:

```python
def run(self):
    try:
        while True:
            line = self.conn.readline()
            if not line:
                break                      # cierre limpio
            self.server._handle_message(self, line)
    except (ConnectionResetError, OSError):
        pass                               # caída abrupta
    finally:
        self.server._on_disconnect(self)
```

`_on_disconnect` aplica la lógica de la sección anterior según la fase del servidor.

### Shutdown

Ctrl+C en el main thread:

- Rompe el `accept()` con `KeyboardInterrupt`.
- Cierra el socket de escucha.
- Los daemon threads de clientes mueren con el proceso.

No hay shutdown graceful (aviso a cada cliente, join de hilos). Para el alcance del proyecto académico es suficiente.

### `SO_REUSEADDR`

Se activa antes del `bind()` para permitir reiniciar el servidor inmediatamente tras Ctrl+C sin esperar TIME_WAIT (60s en Linux por default).

## Manejo de errores

### Clasificación

| Tipo | Cómo responde el servidor |
|---|---|
| Error de protocolo (mal JSON, type desconocido, campo faltante) | Envía `error` con `BAD_MESSAGE` al emisor; la conexión queda abierta |
| Error de fase/lógica del cliente (comando incorrecto para la fase) | Envía `error` con código apropiado; conexión abierta |
| Error del motor (`core.exceptions.*`) | Mapea a `WRONG_PHASE`, `INVALID_MOVE`, `DUPLICATE_PLAYER`; conexión abierta |
| Desconexión abrupta del cliente (TCP RST, read fail) | Se procesa en `_on_disconnect` como desconexión normal |
| Error interno del servidor (excepción no capturada en un hilo) | Se loggea con stack trace en nivel `ERROR`; el hilo termina; otros clientes siguen |

**Garantía transaccional:** si un comando lanza excepción dentro del lock, el estado del servidor **queda como estaba antes**. El motor ya garantiza esto para sus operaciones (del módulo #1); el servidor hereda la garantía al delegar.

## Testing

### Objetivo de cobertura

≥ 90% en `server/`. No se exige 95% como en el motor porque hay rutas de I/O puras difíciles de ejercitar determinísticamente.

### Organización

| Archivo | Qué prueba |
|---|---|
| `tests_server/test_protocol.py` | `encode`, `decode`, validación shape (sin sockets) |
| `tests_server/test_lobby.py` | `Lobby` en aislamiento (sin sockets): join, host, select_color, start |
| `tests_server/test_session.py` | `GameSession` en aislamiento: delegación al motor, desconexión |
| `tests_server/test_integration.py` | End-to-end con sockets reales: 2 clientes en localhost hasta `game_over` |

### Fixtures clave (`conftest.py`)

- `server_factory(rng=None)` — arranca un `Server` en un thread daemon en puerto 0 (dinámico), espera a que haga `listen()`, retorna `(host, port)`. Acepta `rng` para partidas determinísticas. Cleanup automático al terminar el test.
- `client_factory(host, port)` — retorna `TestClient` con métodos `send(dict)`, `recv(timeout=1.0)`, `close()`. Internamente levanta un hilo lector que encola mensajes en una `queue.Queue` para consumo sincronizado.

### Determinismo

Para que los tests E2E sean reproducibles, el `Server` acepta un `rng: random.Random | None` en su constructor y lo pasa a la `GameSession`. Los tests inyectan un `ScriptedRandom` (ya definido en el módulo #1) con la secuencia exacta de dados que necesitan.

### Convenciones

- Cada test arma el estado mínimo necesario y verifica una sola cosa.
- Nombres descriptivos: `test_host_can_start_with_two_players`, `test_duplicate_color_is_rejected`.
- Tests E2E usan `ScriptedRandom` para evitar flakiness por azar.
- Sin dependencias entre tests: fixtures por test, servidor fresco por test.

## Puesta en marcha

### Entry point

`server/__main__.py` expone un CLI con argparse:

```
python -m server [--host HOST] [--port PORT] [--log-level LEVEL]
```

- `--host` default `0.0.0.0` (todas las interfaces).
- `--port` default `5000`.
- `--log-level` default `INFO`. Valores: `DEBUG | INFO | WARNING | ERROR`.

### Logging

Configurado con `logging.basicConfig` y formato que incluye el nombre del thread:

```
%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s
```

Esto es crítico para debuguear threading: cada línea dice qué hilo la generó. Ejemplo:

```
2026-04-20 19:42:31 [INFO] [MainThread]   listening on 0.0.0.0:5000
2026-04-20 19:42:35 [INFO] [client-54321] Alice connected
2026-04-20 19:42:42 [INFO] [client-54322] Bob connected
2026-04-20 19:42:50 [INFO] [client-54321] Alice started game (2 players)
```

Niveles:

- `INFO`: ciclo de vida (listen, connect, disconnect, game_started, game_over).
- `DEBUG`: cada mensaje entrante y evento saliente.
- `WARNING`: validación fallida del cliente, desconexión abrupta.
- `ERROR`: excepciones no esperadas en un hilo (con stack trace).

## Limitaciones conocidas

(Para documentar en el futuro `README.md` del proyecto.)

- **Performance.** El servidor no está optimizado para miles de mensajes/segundo. Es suficiente para 4 jugadores de un juego de turnos; no para usos intensivos.
- **Seguridad.** Sin autenticación (llega en el módulo #5), sin rate limiting, sin validación contra mensajes anormalmente grandes. Aceptable en LAN académica; no se debe exponer a internet abierto sin añadir capas.
- **Red inestable.** Asume TCP fiable sobre LAN o localhost. No maneja red de calidad baja (pérdida persistente, partición, MTU extremos) más allá de lo que TCP y el OS ya ofrecen.
- **Concurrencia extrema.** Una sola partida viva a la vez, hasta 4 jugadores. No escala a miles de partidas simultáneas.
- **Sin reconexión.** Un jugador que se desconecta no puede volver. Sus turnos se saltan hasta terminar la partida o quedar solo.
- **Sin persistencia.** El estado vive en memoria; Ctrl+C o caída del proceso pierde la partida en curso.
- **Sin shutdown graceful.** Ctrl+C corta abruptamente; los clientes ven cierre TCP sin aviso.

Todas estas limitaciones se abordarán (o no) en módulos posteriores: autenticación (#5), persistencia (#4), mejor red (#7 Berkeley), despliegue con proxy en (#9).

## Asunciones pendientes de validación

1. **"Un solo juego a la vez" es lo que espera el profesor.** El enunciado lo sugiere explícitamente pero conviene confirmar antes de invertir en ello.
2. **Desconexión → saltar turnos sin reconexión** es aceptable como interpretación. Si el profesor espera reconexión con token, este módulo necesitará extensión (manejable localizada en `GameSession` + `Server._handle_connection`).
3. **TCP crudo sin WebSocket** es la lectura "literal" del enunciado. Si el profesor aclara "WebSocket o cualquier socket", nada impide mantener lo actual, pero podríamos haber simplificado con `websockets` o `Flask-SocketIO`. Se deja TCP por fidelidad al enunciado.
4. **El layout del tablero (módulo #1) sigue siendo válido.** El servidor delega al motor sin modificarlo; si el profesor aclara algo sobre el tablero, se cambia en `core/board.py` y el servidor lo hereda sin tocar.

## Siguientes pasos

1. Revisión de este spec por un subagente reviewer, iterar hasta aprobación.
2. Revisión por el usuario.
3. Escritura del plan de implementación en `docs/superpowers/plans/2026-04-20-parques-server.md` vía el skill `superpowers:writing-plans`.
4. Ejecución del plan con TDD (test → fail → implement → pass), en el mismo estilo del módulo #1.
5. Al cerrar el módulo (tests verdes, cobertura ≥90%, partida E2E funcional), iniciar brainstorming del módulo #3 (UI Quasar contra este servidor).
