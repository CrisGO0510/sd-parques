import pytest
from core.board import (
    BOARD_SIZE, HOME_STRETCH_SIZE,
    EXITS, SAFES, HOME_STRETCH_ENTRY,
    is_safe, exit_position, home_stretch_entry_for, next_position,
)
from core.entities import Color


def test_board_size_is_68():
    assert BOARD_SIZE == 68


def test_home_stretch_size_is_8():
    assert HOME_STRETCH_SIZE == 8


def test_exits_one_per_color():
    assert set(EXITS.keys()) == set(Color)
    assert len(set(EXITS.values())) == 4


def test_safes_contains_twelve_cells():
    assert len(SAFES) == 12


def test_safes_contains_all_exits():
    for exit_pos in EXITS.values():
        assert exit_pos in SAFES


def test_is_safe_returns_true_for_every_safe_cell():
    for pos in SAFES:
        assert is_safe(pos)


def test_is_safe_returns_false_for_non_safe_cell():
    non_safe = next(i for i in range(BOARD_SIZE) if i not in SAFES)
    assert not is_safe(non_safe)


def test_exit_position_returns_mapped_value():
    assert exit_position(Color.RED) == EXITS[Color.RED]


def test_home_stretch_entry_for_returns_mapped_value():
    assert home_stretch_entry_for(Color.BLUE) == HOME_STRETCH_ENTRY[Color.BLUE]


def test_next_position_advances_within_range():
    assert next_position(0, 5) == 5


def test_next_position_wraps_around():
    assert next_position(66, 5) == 3


def test_next_position_lands_exactly_on_zero_after_full_loop():
    assert next_position(0, BOARD_SIZE) == 0


def test_next_position_rejects_negative_steps():
    with pytest.raises(ValueError):
        next_position(10, -1)
