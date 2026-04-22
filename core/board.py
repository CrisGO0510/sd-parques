"""Board layout constants and pure helpers."""
from core.entities import Color

BOARD_SIZE = 68
HOME_STRETCH_SIZE = 8

# Each color's section spans 17 circuit cells. Colors are ordered
# counter-clockwise visually from RED: RED (bottom-right) → GREEN
# (top-right) → BLUE (top-left) → YELLOW (bottom-left). Must stay in
# sync with the coordinate tables in client/src/composables/
# useBoardGeometry.ts.
EXITS: dict[Color, int] = {
    Color.RED: 0,
    Color.GREEN: 17,
    Color.BLUE: 34,
    Color.YELLOW: 51,
}

# Each color walks 63 cells before entering its own home stretch. The
# entry sits inside the previous color's section, at the mid-arm
# LLEGADA column drawn in client/src/assets/board.svg.
HOME_STRETCH_ENTRY: dict[Color, int] = {
    Color.RED: 63,
    Color.GREEN: 12,
    Color.BLUE: 29,
    Color.YELLOW: 46,
}

# Safe cells: each SALIDA, each own-color SEGURO (7 past SALIDA), and
# each home-stretch entry (5 before the following SALIDA).
SAFES: frozenset[int] = frozenset({
    0, 7, 12, 17, 24, 29, 34, 41, 46, 51, 58, 63,
})


def is_safe(position: int) -> bool:
    """Return True if the circuit cell is a safe cell (no capture)."""
    return position in SAFES


def exit_position(color: Color) -> int:
    """Circuit cell where a piece lands when leaving jail."""
    return EXITS[color]


def home_stretch_entry_for(color: Color) -> int:
    """Last circuit cell before diverging into the color's home stretch."""
    return HOME_STRETCH_ENTRY[color]


def next_position(position: int, steps: int) -> int:
    """Advance `steps` cells on the circuit with wrap-around 95 → 0."""
    if steps < 0:
        raise ValueError("steps must be non-negative")
    return (position + steps) % BOARD_SIZE
