"""add_bot/remove_bot ya no son comandos válidos del protocolo."""
from __future__ import annotations

import pytest

from server.protocol import ProtocolError, validate_command


def test_add_bot_is_unknown_type():
    with pytest.raises(ProtocolError, match="unknown type"):
        validate_command({"type": "add_bot"})


def test_remove_bot_is_unknown_type():
    with pytest.raises(ProtocolError, match="unknown type"):
        validate_command({"type": "remove_bot", "color": "green"})
