"""Protocol: JSON-per-line messages, encode / decode / validate."""
from __future__ import annotations

import json
from typing import Any


class ProtocolError(ValueError):
    """Raised when an incoming message is malformed or invalid."""


def encode(message: dict[str, Any]) -> bytes:
    """Serialize a dict to a single NDJSON line terminated by '\\n'."""
    return (json.dumps(message, separators=(",", ":")) + "\n").encode("utf-8")


def decode(raw: bytes) -> dict[str, Any]:
    """Parse a single NDJSON line into a dict.

    Raises ProtocolError on malformed or non-object payloads.
    """
    text = raw.strip()
    if not text:
        raise ProtocolError("empty line")
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as e:
        raise ProtocolError(f"not valid JSON: {e}") from e
    if not isinstance(obj, dict):
        raise ProtocolError(f"message must be a JSON object, got {type(obj).__name__}")
    return obj


# Command schemas: maps type → {field_name: expected_type}.
# Empty dict means "no fields required beyond type".
COMMAND_SCHEMAS: dict[str, dict[str, type]] = {
    "join":         {"username": str},
    "select_color": {"color": str},
    "start_game":   {},
    "roll_initial": {},
    "roll_dice":    {},
    "move_piece":   {"piece_index": int, "dice_value": int, "action": str},
    "skip_turn":    {},
    "crown_piece":  {"piece_index": int},
    "leave":        {},
}


def validate_command(msg: dict[str, Any]) -> None:
    """Validate an incoming command's shape.

    Raises ProtocolError if type is missing/unknown or required fields
    are missing or of the wrong type.
    """
    msg_type = msg.get("type")
    if msg_type is None:
        raise ProtocolError("missing 'type' field")
    if msg_type not in COMMAND_SCHEMAS:
        raise ProtocolError(f"unknown type: {msg_type}")
    schema = COMMAND_SCHEMAS[msg_type]
    for field, expected in schema.items():
        if field not in msg:
            raise ProtocolError(f"{msg_type}: missing field '{field}'")
        if not isinstance(msg[field], expected):
            raise ProtocolError(
                f"{msg_type}.{field}: expected {expected.__name__}, "
                f"got {type(msg[field]).__name__}"
            )
