"""Pruebas de validate_command para add_bot/remove_bot."""
from __future__ import annotations

import pytest

from server.protocol import ProtocolError, validate_command


def test_add_bot_accepts_no_payload():
    validate_command({"type": "add_bot"})


def test_remove_bot_requires_color_string():
    validate_command({"type": "remove_bot", "color": "red"})


def test_remove_bot_rejects_missing_color():
    with pytest.raises(ProtocolError):
        validate_command({"type": "remove_bot"})


def test_remove_bot_rejects_non_string_color():
    with pytest.raises(ProtocolError):
        validate_command({"type": "remove_bot", "color": 42})
