# Parqués Distribuido — Spec de Diseño

## Resumen

Juego de parqués colombiano distribuido para 2-4 jugadores en red. Servidor Python (Flask + Socket.IO) con cliente web/mobile (Quasar + Capacitor). Desplegado en Render con PostgreSQL managed.

## Contexto

Proyecto final de la asignatura de Sistemas Distribuidos. Debe demostrar uso de hilos, sockets, sincronización distribuida y comunicación cliente-servidor en red. Se buscan las bonificaciones de: entorno gráfico (+20%), despliegue en nube (+30%) y cliente móvil nativo Android (nota 5.0).

## Decisiones de Diseño

| Decisión | Elección | Razón |
|---|---|---|
| Arquitectura | Monolito Flask + Socket.IO | Simplicidad para un solo desarrollador, deploy sencillo |
| Comunicación RT | Socket.IO (python-socketio) | Eventos bidireccionales, rooms, reconexión nativa |
| Base de datos | PostgreSQL | Robusto, Render lo soporta managed |
| Deploy | Render | Deploy desde Git, free tier, PostgreSQL managed |
| Recomendación | Híbrido (heurísticas + LLM) | Correctitud garantizada por heurísticas, UX mejorada con LLM |
| Estadísticas | Frecuentista (wins/games) | Simple, cumple el enunciado |
| Sincronización | Algoritmo de Berkeley | Sugerido por el enunciado, demuestra conocimiento de SD |
| Cliente | Quasar (Vue 3) + Capacitor | Un codebase para web + APK Android |

## Arquitectura General

```
┌──────────────────────────────────────────────┐
│                RENDER (Nube)                  │
│                                               │
│  ┌─────────────────────────────────────────┐ │
│  │        Servidor Python (Flask)           │ │
│  │                                          │ │
│  │  ┌────────────┐  ┌──────────────────┐   │ │
│  │  │ Socket.IO   │  │ API REST (Flask) │   │ │
│  │  │ (juego RT)  │  │ (auth, stats)    │   │ │
│  │  └──────┬──────┘  └──────┬──────────┘   │ │
│  │         │                 │              │ │
│  │  ┌──────┴─────────────────┴───────────┐ │ │
│  │  │        Lógica del Juego             │ │ │
│  │  │  (tablero, turnos, reglas, dados)   │ │ │
│  │  └──────────────┬─────────────────────┘ │ │
│  │                 │                        │ │
│  │  ┌──────────────┴─────────────────────┐ │ │
│  │  │  Módulos auxiliares                 │ │ │
│  │  │  - Berkeley (sincronización)        │ │ │
│  │  │  - Recomendación (heurísticas+LLM)  │ │ │
│  │  │  - Estadísticas (frecuentista)      │ │ │
│  │  └──────────────┬─────────────────────┘ │ │
│  │                 │                        │ │
│  │  ┌──────────────┴──────┐                │ │
│  │  │  PostgreSQL (managed) │                │ │
│  │  └─────────────────────┘                │ │
│  └─────────────────────────────────────────┘ │
└──────────────────────────────────────────────┘
        │           │           │          │
   Socket.IO   Socket.IO   Socket.IO  Socket.IO
        │           │           │          │
  ┌─────┴──┐ ┌─────┴──┐ ┌─────┴──┐ ┌─────┴──┐
  │Client 1│ │Client 2│ │Client 3│ │Client 4│
  │Quasar  │ │Quasar  │ │Quasar  │ │Quasar  │
  │Web/APK │ │Web/APK │ │Web/APK │ │Web/APK │
  └────────┘ └────────┘ └────────┘ └────────┘
```

## Modelo de Datos (PostgreSQL)

### users
| Campo | Tipo | Notas |
|---|---|---|
| id | serial PK | |
| username | varchar unique | |
| password_hash | varchar | bcrypt |
| created_at | timestamp | default now() |

### games
| Campo | Tipo | Notas |
|---|---|---|
| id | serial PK | |
| status | enum | waiting, playing, finished |
| winner_id | FK → users | nullable |
| started_at | timestamp | |
| finished_at | timestamp | nullable |

### game_players
| Campo | Tipo | Notas |
|---|---|---|
| id | serial PK | |
| game_id | FK → games | |
| user_id | FK → users | |
| color | enum | red, blue, green, yellow |
| finish_position | int | nullable, 1-4 |

### game_moves
| Campo | Tipo | Notas |
|---|---|---|
| id | serial PK | |
| game_id | FK → games | |
| user_id | FK → users | |
| move_number | int | |
| dice_1 | int | 1-6 |
| dice_2 | int | 1-6 |
| piece_index | int | 0-3 |
| from_position | int | |
| to_position | int | |
| action | enum | move, jail, enter, finish, eat |
| created_at | timestamp | |

## Lógica del Tablero

### Representación
- Circuito principal de 68 casillas (0-67), compartido por todos los jugadores
- Cada jugador tiene offset de salida: 0, 17, 34, 51
- Recta final: 8 casillas privadas por color (fuera del circuito principal, indexadas aparte)
- Cada ficha tiene estado: `jail`, `board`, `home_stretch`, `finished`

### Casillas especiales
- **Salidas (4):** posiciones 0, 17, 34, 51
- **Seguros (12):** posiciones 5, 12, 22, 29, 39, 46, 56, 63, 73, 80, 90, 95
- **Recta final:** 8 casillas privadas por color (solo el dueño entra)

### Reglas implementadas
1. Se sacan fichas de cárcel con pares (ambos dados iguales)
2. Al inicio, 3 oportunidades para sacar primera ficha
3. Tres pares seguidos = sacar una ficha directo del juego (a elección)
4. Comer ficha rival = enviarla a cárcel (excepto en seguro o salida)
5. Fichas en recta final de su color = protegidas
6. Turno se retiene solo sacando pares
7. Gana quien lleve las 4 fichas a `finished`

## Comunicación Socket.IO

### Eventos Cliente → Servidor
| Evento | Payload | Descripción |
|---|---|---|
| `join_lobby` | `{username}` | Entrar al lobby |
| `select_color` | `{color}` | Elegir color |
| `roll_dice` | `{}` | Lanzar dados |
| `move_piece` | `{piece_index, target}` | Mover ficha |
| `request_recommendation` | `{}` | Pedir sugerencia |

### Eventos Servidor → Cliente
| Evento | Payload | Descripción |
|---|---|---|
| `lobby_update` | `{players, available_colors}` | Estado del lobby |
| `game_start` | `{game_id, players, board}` | Partida iniciada |
| `turn_update` | `{current_player, phase}` | Turno actual |
| `dice_result` | `{dice_1, dice_2, is_pair}` | Resultado dados |
| `board_update` | `{board_state, pieces}` | Estado del tablero |
| `player_jailed` | `{player, piece}` | Ficha a cárcel |
| `game_over` | `{winner, rankings}` | Fin de partida |
| `recommendation` | `{move, explanation}` | Sugerencia de jugada |
| `sync_clock` | `{offset_ms}` | Ajuste Berkeley |
| `sync_request` | `{}` | Pedir timestamp al cliente (Berkeley) |
| `sync_adjust` | `{offset_ms}` | Enviar corrección de reloj |

### Rooms
- `lobby` — sala de espera general
- `game_{id}` — sala por partida activa

## Módulo de Sincronización (Berkeley)

1. Al iniciar partida, servidor envía `sync_request` a todos los clientes
2. Cada cliente responde con su timestamp local
3. Servidor calcula promedio de diferencias
4. Envía `sync_adjust` con offset individual a cada cliente
5. Clientes aplican offset para timestamps de eventos
6. Re-sincronización cada 60 segundos

## Módulo de Recomendación (Híbrido)

### Capa de heurísticas
Evalúa todas las jugadas posibles y asigna score:

| Acción | Score |
|---|---|
| Comer ficha rival | +50 |
| Entrar a recta final | +40 |
| Llegar a seguro | +30 |
| Sacar ficha de cárcel | +25 |
| Mover ficha en riesgo | +20 |
| Avanzar ficha más atrasada | +15 |

### Capa LLM
- Input: estado del tablero + jugada recomendada + score + contexto
- Output: explicación en lenguaje natural
- Fallback: template de texto basado en la regla que activó el score más alto
- Si la API key no está configurada o la cuota se excede, se usa el fallback automáticamente
- API key se configura via variable de entorno `CLAUDE_API_KEY`

## Módulo Estadístico

- **Ranking:** jugadores ordenados por cantidad de victorias
- **Probabilidad de ganar:** `victorias / partidas_jugadas` por jugador
- **Historial:** últimas N partidas con detalle (rivales, posición, duración)

## Desconexión y Reconexión

- Si un jugador se desconecta, tiene 60 segundos para reconectarse
- Durante la desconexión, si es su turno, se pasa automáticamente tras 30 segundos de timeout
- Si no reconecta en 60 segundos, sus fichas quedan congeladas y el juego continúa sin él
- Al reconectar, recibe el estado completo del tablero vía `board_update`

## Lobby y Transición a Partida

- Los jugadores entran al lobby con `join_lobby`
- El primer jugador en el lobby se convierte en "host"
- El host puede iniciar la partida cuando hay 2-4 jugadores (botón "Iniciar partida")
- Al iniciar, se bloquea el lobby para nuevos jugadores hasta que termine la partida
- Fase de selección de color antes de empezar (cada jugador elige, sin repetir)
- Fase de dados iniciales: cada jugador lanza para determinar orden de turnos

## Concurrencia

- **Un hilo por partida** — cada instancia de Game corre en su propio `threading.Thread`
- **Semáforo de turno** — `threading.Event()` por jugador; solo el activo está en `set()`
- **Lock de estado** — `threading.Lock()` protege el estado del tablero
- **Lock de lobby** — controla acceso a lista de espera

## Estructura de Carpetas

```
parques-distribuido/
├── server/
│   ├── app.py                 # Entry point, Flask + Socket.IO
│   ├── config.py              # Config (DB, secrets)
│   ├── models/
│   │   ├── user.py            # Modelo User
│   │   ├── game.py            # Modelo Game, GamePlayer
│   │   └── move.py            # Modelo GameMove
│   ├── game/
│   │   ├── board.py           # Tablero: casillas, seguros, rectas
│   │   ├── engine.py          # Motor: reglas, validación, turnos
│   │   ├── manager.py         # GameManager: lobby, crear/destruir partidas
│   │   └── constants.py       # Constantes del juego
│   ├── services/
│   │   ├── auth.py            # Registro, login, JWT
│   │   ├── stats.py           # Estadísticas y ranking
│   │   ├── recommendation.py  # Heurísticas + LLM
│   │   └── berkeley.py        # Sincronización de relojes
│   ├── sockets/
│   │   ├── lobby.py           # Eventos del lobby
│   │   ├── game_events.py     # Eventos de partida
│   │   └── sync.py            # Eventos de sincronización
│   ├── routes/
│   │   ├── auth.py            # POST /register, /login
│   │   └── stats.py           # GET /stats, /ranking
│   ├── requirements.txt
│   └── Dockerfile
├── client/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── LoginPage.vue
│   │   │   ├── LobbyPage.vue
│   │   │   ├── GamePage.vue
│   │   │   └── StatsPage.vue
│   │   ├── components/
│   │   │   ├── BoardCanvas.vue
│   │   │   ├── DiceRoller.vue
│   │   │   ├── PlayerInfo.vue
│   │   │   └── Recommendation.vue
│   │   ├── composables/
│   │   │   ├── useSocket.js
│   │   │   ├── useGame.js
│   │   │   └── useAuth.js
│   │   ├── stores/
│   │   │   ├── gameStore.js
│   │   │   └── userStore.js
│   │   └── router/
│   │       └── index.js
│   ├── package.json
│   └── quasar.config.js
├── docker-compose.yml
└── render.yaml
```

## Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Servidor | Python 3.11 + Flask + Flask-SocketIO |
| Tiempo real | python-socketio (threading mode) |
| Base de datos | PostgreSQL + SQLAlchemy |
| Auth | JWT (PyJWT) |
| Cliente | Vue 3 + Quasar Framework |
| Estado cliente | Pinia |
| Mobile | Capacitor (APK Android) |
| Deploy | Render (web service + PostgreSQL managed) |
| Sincronización | Algoritmo de Berkeley |
| Recomendación | Heurísticas + Claude API |
| Concurrencia | threading + semáforos |
