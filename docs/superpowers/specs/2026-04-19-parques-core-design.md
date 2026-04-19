# Parqués Core — Spec de Diseño del Dominio

**Fecha:** 2026-04-19
**Autor:** CrisGO
**Estado:** Propuesto
**Módulo:** #1 de la ruta incremental (ver `## Contexto`)

## Resumen

Módulo de dominio puro del juego de Parqués colombiano: reglas, tablero, turnos y validaciones, implementado en Python 3.11+ sin red, sin base de datos, sin interfaz gráfica y sin concurrencia. El objetivo es tener el "corazón" del juego verificado y cubierto por tests antes de montar cualquier capa de servidor, persistencia o UI encima.

Convenciones del proyecto: **identificadores y comentarios en inglés**, **documentación y conversación de diseño en español**.

## Contexto

Proyecto final de la asignatura de Sistemas Distribuidos (UTP, semestre 2026-1). El proyecto completo se construye en capas incrementales, una a la vez:

1. **Reglas del juego en Python puro** ← este spec
2. Partida local multijugador en terminal
3. Servidor + cliente en `localhost` (sockets)
4. Interfaz gráfica
5. Persistencia (BD local)
6. Autenticación
7. Estadísticas y ranking
8. Sincronización de relojes (algoritmo de Berkeley)
9. Recomendador (heurística, luego LLM opcional)
10. Despliegue en nube (bonificación del enunciado)
11. APK Android (bonificación)

Este spec cubre **únicamente el módulo 1**. Los siguientes se especificarán en sus propios documentos.

Fuente de verdad para las reglas: `proyecto_final_distribuidos_2026-1.pdf` (raíz del repo). Ambigüedades del enunciado se resolvieron con el usuario y quedan documentadas en `## Reglas del juego`.

## Alcance

**Incluye:**
- Representación del tablero (96 casillas + 4 rectas finales de 8 casillas + cárceles).
- Entidades del dominio (`Piece`, `Player`, `Game`) como dataclasses mutables.
- Motor de reglas como módulo de funciones puras que recibe `Game` y lo muta.
- Sistema de excepciones del dominio.
- Suite de pruebas con `pytest`, incluyendo una simulación de partida completa con dados determinísticos.

**No incluye** (explícitamente fuera de alcance, van en módulos posteriores):
- Sockets, HTTP, WebSocket, Socket.IO o cualquier capa de red.
- Hilos, locks, semáforos. El dominio es single-threaded.
- Persistencia (SQLAlchemy, SQLite, PostgreSQL).
- Autenticación, JWT, hashing de contraseñas.
- Estadísticas acumuladas entre partidas.
- Sincronización de relojes (Berkeley).
- Recomendador de jugadas.
- UI de cualquier tipo (CLI, web, móvil).
- Despliegue.

## Reglas del juego

Derivadas del enunciado del profesor; ambigüedades resueltas en conversación de brainstorming.

### Tablero
- Circuito principal de **96 casillas**.
- **4 casillas de salida** (una por color).
- **12 casillas de seguro** distribuidas a lo largo del circuito.
- **4 rectas finales** (una por color), cada una de **8 casillas**, con la última siendo la meta.
- **4 cárceles**, una por color, en las esquinas.
- Los colores son `RED`, `BLUE`, `GREEN`, `YELLOW`.

### Inicio de partida
- De 2 a 4 jugadores.
- Cada jugador tiene **nombre único** y **color único**.
- Las 4 fichas de cada jugador empiezan en la cárcel de su color.
- El primer turno lo gana quien saque el **mayor total** con los dos dados; los demás lanzan también para determinar el orden (descendente por total).

### Turnos y dados
- Dos dados por lanzamiento, **usados por separado**: cada dado puede aplicarse a una ficha distinta, o ambos a la misma ficha (acumulativo).
- **Pares → relanzar** (conservas el turno).
- **Al iniciar un turno con las 4 fichas en cárcel**, el jugador tiene **hasta 3 oportunidades** de sacar pares. Si ninguno de los 3 tiros es par, pasa el turno.
- **Tres pares consecutivos** en el mismo turno → el jugador **no mueve** con esos dados; en su lugar, **corona** una ficha de su elección (va directo a la meta). La ficha puede estar en cualquier estado (cárcel, tablero, recta final). El contador de pares consecutivos es **por turno**: se resetea al pasar al siguiente jugador (no solo cuando sale un tiro no-par).

### Sacar de cárcel
- Solo con **pares**. La ficha se posa en la casilla de **salida** del color.
- Los dados del par se consumen **sacando la ficha, no moviéndola**. El jugador relanza y usa los dados nuevos para mover (ese relanzamiento sigue las reglas normales).

### Movimiento y captura
- Las fichas avanzan por el circuito contando casillas; al llegar a la casilla 95 se continúa en la 0.
- Si una ficha llega a una casilla **no protegida** donde hay una ficha rival, la rival se va a la cárcel.
- Casillas **protegidas** (no se puede capturar a quien esté en ellas): seguros, salidas, y la recta final del color de la ficha.
- **Sin bloqueo con par**: dos fichas del mismo color pueden convivir en una casilla sin efectos especiales (ni bloquean tránsito, ni protegen).
- **Sin bonificaciones** por comer o coronar (no hay "+20" ni "+10" extra).
- **Sin soplo**: no se castiga al jugador por no mover una jugada óptima.

### Recta final
- Cada color tiene **8 casillas privadas** (la octava es la meta).
- **Entrada automática**: cuando una ficha pasa por el punto de entrada a la recta final de su color, se desvía hacia la recta final; no puede "ignorarla" y dar otra vuelta.
- Las fichas en recta final son **inmunes a captura**.
- Para llegar a la meta se requiere **número exacto**. Si el dado disponible se pasa, **ese dado no sirve para esa ficha** (el jugador puede usarlo con otra ficha, o si no aplica, se pierde con `skip_turn`).

### Ganar
- La partida termina cuando un jugador tiene sus 4 fichas en la meta (`CROWNED`).

## Arquitectura del paquete

```
sd-parques/
├── parques/
│   ├── __init__.py
│   ├── entities.py       # Dataclasses: Piece, Player, Game, Move, MoveResult
│   ├── board.py          # Layout constants + pure helpers
│   ├── engine.py         # All game rules (module-level functions)
│   └── exceptions.py     # Domain exceptions
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_board.py
│   ├── test_engine_turns.py
│   ├── test_engine_movement.py
│   ├── test_engine_capture.py
│   ├── test_engine_home_stretch.py
│   └── test_full_game.py
└── pyproject.toml
```

**Decisiones de layout:**

1. **Paquete plano** (`parques/`, no `src/parques/`) — más simple para un proyecto académico.
2. **Archivos por rol, no por entidad.** Todas las dataclasses viven en `entities.py` (son cortas); todas las funciones de reglas viven en `engine.py`.
3. **`board.py` separado del motor.** El layout del tablero es "geografía" (constantes de salidas, seguros, entradas a recta final). El motor consulta `board.py` cuando necesita saber si una casilla es segura o cuál es la salida de un color. Separarlo deja obvio que el mapa es dato estático y las reglas son comportamiento.
4. **`engine.py` monolítico por ahora.** Si crece más de ~400 líneas, se parte en submódulos (`engine/movement.py`, `engine/turns.py`). No adelantamos esa partición hasta verla necesaria.
5. **Tests agrupados por comportamiento**, no por clase. Un archivo por tema del juego (movimiento, captura, etc.).

**Dependencias externas:** solo `pytest` (dev). Todo lo demás es stdlib de Python 3.11.

## Entidades

```python
# parques/entities.py
from dataclasses import dataclass, field
from enum import Enum

class Color(str, Enum):
    RED = "red"
    BLUE = "blue"
    GREEN = "green"
    YELLOW = "yellow"

class PieceState(str, Enum):
    IN_JAIL = "in_jail"
    ON_BOARD = "on_board"
    IN_HOME_STRETCH = "in_home_stretch"
    CROWNED = "crowned"

class GamePhase(str, Enum):
    SETUP = "setup"         # collecting initial rolls to decide order
    ROLLING = "rolling"     # current player must roll
    MOVING = "moving"       # dice rolled, pending moves
    CROWNING = "crowning"   # triple pairs → pick a piece to crown
    FINISHED = "finished"

class MoveAction(str, Enum):
    EXIT_JAIL = "exit_jail"
    ADVANCE = "advance"
    CAPTURE = "capture"
    ENTER_HOME_STRETCH = "enter_home_stretch"
    REACH_GOAL = "reach_goal"

@dataclass
class Piece:
    index: int                                  # 0..3
    state: PieceState = PieceState.IN_JAIL
    circuit_position: int | None = None         # 0..95 when ON_BOARD
    home_stretch_position: int | None = None    # 0..7 when IN_HOME_STRETCH

@dataclass
class Player:
    name: str
    color: Color
    pieces: list[Piece] = field(
        default_factory=lambda: [Piece(i) for i in range(4)]
    )

@dataclass
class Move:
    piece_index: int        # 0..3
    dice_value: int         # which pending die this consumes
    action: MoveAction

@dataclass
class MoveResult:
    action: MoveAction
    captured: Piece | None = None
    reached_goal: bool = False
    triggered_crowning: bool = False

@dataclass
class Game:
    players: list[Player]
    phase: GamePhase = GamePhase.SETUP
    turn_order: list[int] = field(default_factory=list)
    current_turn_index: int = 0
    pending_dice: list[int] = field(default_factory=list)
    initial_rolls: dict[int, int] = field(default_factory=dict)
    initial_rolls_remaining: int = 0
    consecutive_pairs: int = 0
    winner: int | None = None
```

**Decisiones clave:**

- **`Piece` no lleva color.** Lo hereda del `Player` dueño (normalizado). Para saber el color de una ficha, se mira en qué jugador vive.
- **Posiciones con `None`, no con `-1`.** Python tiene `Optional`; los sentinelas numéricos son estilo C y propician bugs sutiles.
- **`pending_dice: list[int]`** es el corazón del turno: lo llena `roll_dice`, lo consume `apply_move`, y cuando queda vacío se decide si pasa turno o se relanza.
- **`GamePhase.CROWNING` como fase propia.** Cuando los 3 pares se disparan, el jugador no puede hacer otra cosa hasta elegir qué ficha corona. Modelarlo como fase explícita permite que el motor valide que `crown_piece()` solo se llame cuando corresponde.
- **`Game` mutable.** No hay `frozen=True`. El motor muta in-place, consistente con el enfoque elegido (datos + motor central).
- **Sin `user_id` en `Player`.** El dominio puro no sabe de base de datos. Cuando se agregue persistencia (módulo 5), se añade el campo.

## API del motor

`parques/engine.py` — funciones puras que reciben `Game` y lo mutan. Sin clases, sin estado global.

```python
def new_game(
    players: list[tuple[str, Color]],
    *,
    rng: random.Random | None = None,
) -> Game:
    """
    Create a new game in SETUP phase.

    Raises:
        DuplicatePlayer: duplicate names or colors.
        ValueError: len(players) not in 2..4.
    """

def roll_initial(game: Game, player_index: int) -> int:
    """
    SETUP phase: player rolls to determine turn order.
    When all players have rolled, sets turn_order (highest total first)
    and transitions to ROLLING.

    Returns: the rolled total (sum of both dice).

    Raises:
        WrongPhase: not in SETUP.
        ValueError: player already rolled or out of range.
    """

def roll_dice(game: Game) -> tuple[int, int]:
    """
    ROLLING phase: current player rolls both dice.
    Transitions to:
      - CROWNING if this is the 3rd consecutive pair (no movement).
      - MOVING otherwise (fills pending_dice).

    Handles the 'all pieces in jail' case: initializes
    initial_rolls_remaining = 3 on first such roll of the turn.
    """

def available_moves(game: Game) -> list[Move]:
    """
    Return every legal Move the current player can make with the
    dice still pending.

    The returned list is deterministic: sorted first by piece_index
    ascending, then by dice_value ascending. This makes tests
    reproducible and gives the future recommender a stable order
    to reason over.

    Returns []:
      - Outside MOVING phase.
      - If no legal move exists with remaining dice.
    """

def apply_move(game: Game, move: Move) -> MoveResult:
    """
    MOVING phase: consume one die from pending_dice and apply the move.

    When pending_dice empties:
      - If last roll was a pair and not 3rd consecutive → ROLLING (same player).
      - Otherwise → advance current_turn_index, back to ROLLING.

    Checks for win condition after applying.

    Raises:
        WrongPhase: not in MOVING.
        InvalidMove: move isn't among available_moves().
    """

def crown_piece(game: Game, piece_index: int) -> None:
    """
    CROWNING phase: triple-pairs reward.
    Pick one piece (any state except already CROWNED) and send it to CROWNED.
    Transitions back to ROLLING with the same player.

    Raises:
        WrongPhase: not in CROWNING.
        ValueError: piece_index invalid or piece already CROWNED.
    """

def skip_turn(game: Game) -> None:
    """
    MOVING phase: player has pending dice but no legal move.
    Discards pending dice and ends the turn.

    Raises:
        WrongPhase: not in MOVING.
        ValueError: pending_dice is empty (nothing to skip).
    """
```

**Decisiones clave:**

- **Motor como módulo**, no clase. El `Game` pasa por parámetro; sin singleton, sin estado global.
- **`available_moves()` antes de `apply_move()`.** El patrón de uso es: el cliente pide la lista, elige uno, lo pasa al motor para aplicarlo. El motor no adivina cuál ficha mover — solo valida y aplica.
- **`Move` es el "lenguaje" de jugadas.** Para ejecutar, el cliente construye un `Move` idéntico a uno de los de `available_moves()`.
- **RNG inyectable.** `new_game` acepta `rng: random.Random | None`. En producción, `None` → instancia interna. En tests, se inyecta uno con seed fijo o scripted.
- **Sin lock**. El dominio es single-threaded. La semaforización que pide el enunciado se añade en la capa de servidor (módulo 3), envolviendo las llamadas al motor.

## Flujo de partida

```
SETUP ──(all roll_initial done)──► ROLLING ──┐
                                             │
                          ┌──── roll_dice ◄──┤
                          │                  │
        (3rd consecutive pair?)              │
              │                              │
         yes  │  no                          │
              ▼                              │
           CROWNING                          │
              │                              │
              │ crown_piece                  │
              └──────────────►  MOVING ◄─────┘ (fills pending_dice)
                                 │
                     ┌───────────┤
                     │           │
                (last die,    (last die,
                was pair)    not pair)
                     │           │
                     ▼           ▼
                ROLLING      ROLLING
             (same player) (next player)

              (4 pieces CROWNED) → FINISHED
```

Ejemplo de uso desde el cliente:

```python
from parques import engine
from parques.entities import Color, GamePhase

game = engine.new_game([
    ("Alice", Color.RED),
    ("Bob", Color.BLUE),
])

engine.roll_initial(game, 0)
engine.roll_initial(game, 1)

while game.phase != GamePhase.FINISHED:
    engine.roll_dice(game)

    if game.phase == GamePhase.CROWNING:
        engine.crown_piece(game, choose_piece_to_crown(game))
        continue

    while game.pending_dice:
        moves = engine.available_moves(game)
        if not moves:
            engine.skip_turn(game)
            break
        engine.apply_move(game, choose_move(moves))

print(f"Ganador: {game.players[game.winner].name}")
```

**Sutilezas que el motor resuelve sin intervención del cliente:**

1. **El 3er par se detecta en `roll_dice`, no en `apply_move`.** Salir con par por 3a vez consecutiva cambia fase a `CROWNING` inmediatamente; no se llena `pending_dice`, no hay movimiento con esos dados.
2. **`consecutive_pairs` se resetea** en cualquier tiro no-par.
3. **Las 3 oportunidades con las 4 fichas en cárcel** se manejan con `initial_rolls_remaining`, inicializado dentro de `roll_dice` cuando corresponde. Cada tiro sin pares lo decrementa; al llegar a 0 pasa el turno.
4. **Victoria.** `apply_move` y `crown_piece` verifican, al final, si el jugador actual tiene sus 4 fichas `CROWNED`. Si sí → `winner`, `phase = FINISHED`.
5. **Fichas en recta final con dado que se pasa** son omitidas por `available_moves()` para ese dado. Si ambos dados no sirven con ninguna ficha, la lista queda vacía y el cliente llama `skip_turn()`.
6. **Caso borde: 4 fichas en cárcel + triple par.** Si al jugador le salen 3 pares consecutivos con todas sus fichas aún en cárcel, la regla de triple par **gana** sobre "salir de cárcel con pares" en el 3er tiro. Como `roll_dice` detecta el triple par **antes** de llenar `pending_dice`, no se saca ficha con ese tiro — se salta directo a `CROWNING`, y ahí el jugador puede optar por coronar una de las fichas en cárcel (la regla de coronación no distingue estado).

## Manejo de errores

```python
# parques/exceptions.py

class DomainError(Exception):
    """Base class for all parques domain errors."""

class WrongPhase(DomainError):
    """An operation was called in the wrong GamePhase."""

class InvalidMove(DomainError):
    """The supplied Move is not among engine.available_moves()."""

class DuplicatePlayer(DomainError):
    """Two players share the same name or the same color."""
```

Tabla de validaciones:

| Operación         | Chequeos                                                                 |
| ----------------- | ------------------------------------------------------------------------ |
| `new_game`        | `2 ≤ len(players) ≤ 4`, nombres únicos, colores únicos                   |
| `roll_initial`    | fase `SETUP`; ese jugador no había tirado aún; índice válido             |
| `roll_dice`       | fase `ROLLING`                                                           |
| `available_moves` | fase `MOVING` (si no, retorna `[]` — no lanza)                           |
| `apply_move`      | fase `MOVING`; el `Move` es uno de los de `available_moves()`            |
| `crown_piece`     | fase `CROWNING`; `0 ≤ piece_index ≤ 3`; la ficha no está ya `CROWNED`    |
| `skip_turn`       | fase `MOVING`; `pending_dice` no vacío                                   |

**Fuera de responsabilidad del motor:**
- Calidad estratégica del movimiento (eso es el recomendador, módulo 9).
- Identidad, autenticación, sesiones (módulo 3 en adelante).
- Red, sincronización de relojes (módulo 3 en adelante).

**Garantía transaccional.** Si una función del motor lanza excepción, el `Game` queda exactamente como estaba antes de la llamada. Los chequeos se realizan **antes** de tocar estado — no a la mitad. Esto es importante para que tests y futuro servidor no tengan que deshacer operaciones a medio aplicar.

**Filosofía.** El motor es pedante. Si el cliente usa la API mal, recibe excepción clara — no respuestas silenciosas erróneas. Esto obliga al cliente a pasar siempre por `available_moves()` antes de `apply_move()`, que es el patrón correcto.

## Testing

**Objetivo de cobertura:** ≥95% en `engine.py`. Meta realista considerando que el dominio es el cimiento de todas las capas posteriores.

**Organización** (tests por comportamiento, no por clase):

| Archivo                           | Qué prueba                                                                          |
| --------------------------------- | ----------------------------------------------------------------------------------- |
| `test_board.py`                   | `is_safe`, `exit_position`, `home_stretch_entry_for`, `next_position` (wrap 95→0)   |
| `test_engine_turns.py`            | Transiciones de fase, orden inicial, pares consecutivos, triple par → `CROWNING`, 3 oportunidades con todas en cárcel, `skip_turn` |
| `test_engine_movement.py`         | Salir de cárcel con pares, avance normal, un dado vs dos dados en misma ficha, `InvalidMove` |
| `test_engine_capture.py`          | Captura envía a cárcel, seguros/salidas/recta-final protegen, misma-color convive sin bloqueo |
| `test_engine_home_stretch.py`     | Entrada automática, protección dentro, número exacto para meta, dados que se pasan  |
| `test_full_game.py`               | Simula 2 partidas completas con dados scripted — una termina con Alice, otra con Bob |

**Dados determinísticos.** `new_game` acepta `rng: random.Random | None`. En tests se usa:
- un `random.Random(seed=N)` con semilla fija para reproducibilidad sin control granular, o
- un `ScriptedRandom(sequence: list[int])` que implementa la misma interfaz mínima que usa el motor (`randint(a, b)`) devolviendo los valores de `sequence` en orden; al agotarse lanza `IndexError`. Vive en `tests/conftest.py`.

**Fixtures en `conftest.py`:**
- `two_player_game` — SETUP con Alice (RED) y Bob (BLUE), RNG scripted.
- `playing_game` — post-SETUP, fase `ROLLING`.
- `force_dice(game, d1, d2)` — helper para tests unitarios que salta el `rng` y llena `pending_dice` directamente.

**pyproject.toml:**

```toml
[project]
name = "parques"
version = "0.1.0"
requires-python = ">=3.11"

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Convenciones:**
- Cada test monta el estado mínimo necesario y verifica **una sola cosa**.
- Nombres descriptivos: `test_three_consecutive_pairs_trigger_crowning`, `test_cannot_capture_piece_on_safe_cell`.
- Sin dependencias entre tests — fixtures por test.
- `test_full_game.py` sirve de humo: si pasa, la partida integral funciona.

## Asunciones pendientes de validación

Estas decisiones se tomaron por defecto razonable, pero podrían ajustarse si el profesor aclara lo contrario:

1. **Layout exacto del tablero.** Las posiciones numéricas concretas de las 4 salidas, los 12 seguros y los 4 puntos de entrada a recta final se decidirán al implementar `board.py` basándonos en la figura del enunciado y la variante tradicional colombiana (96 casillas con paso por el punto de entrada antes de desviarse).
2. **Dos fichas rivales en la misma casilla de seguro.** Conviven (ninguna come a la otra) — consistente con "en seguros no se come".
3. **Si el jugador puede mover, no está obligado a hacerlo.** Puede llamar `skip_turn` igual (aunque estratégicamente rara vez tenga sentido). No hay soplo, así que no hay castigo. Se valida en el spec del módulo 3 si se quiere cambiar.
4. **Coronar por triple par** puede elegir cualquier ficha no coronada (incluso si ya está en recta final o en la casilla anterior a la meta).
5. **Desempate en `roll_initial`**: si dos o más jugadores sacan el mismo total mayor, el spec no dice qué pasa. Propuesta por defecto: los jugadores empatados **relanzan** entre sí hasta que haya un ganador único para el primer puesto; el resto del orden se resuelve de la misma forma recursivamente. Confirmar con el profesor si prefiere otra regla (p. ej. orden de inscripción como desempate).

Las asunciones 1 y 4 son las de mayor impacto; conviene confirmarlas con el profesor antes o durante la implementación de `board.py` y `crown_piece`.

## Siguientes pasos

1. Revisión de este spec (subagente + usuario).
2. Escritura del plan de implementación paso a paso (`docs/superpowers/plans/2026-04-19-parques-core.md`).
3. Ejecución del plan con TDD: escribir tests → hacerlos pasar → refactorizar.
4. Al finalizar el módulo 1 (tests verdes, cobertura ≥95%), iniciar brainstorming del módulo 2 (partida local multijugador en terminal).
