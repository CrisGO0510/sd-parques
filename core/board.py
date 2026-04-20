"""Board layout constants and pure helpers."""
from core.entities import Color

BOARD_SIZE = 96
HOME_STRETCH_SIZE = 8

EXITS: dict[Color, int] = {
    Color.RED: 0,
    Color.BLUE: 24,
    Color.GREEN: 48,
    Color.YELLOW: 72,
}

# Last circuit cell before diverging into the home stretch for each color.
# Chosen so each color runs a full loop (95 cells) before entering.
HOME_STRETCH_ENTRY: dict[Color, int] = {
    Color.RED: 71,
    Color.BLUE: 95,
    Color.GREEN: 23,
    Color.YELLOW: 47,
}

SAFES: frozenset[int] = frozenset({
    0, 6, 18, 24, 30, 42, 48, 54, 66, 72, 78, 90,
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
