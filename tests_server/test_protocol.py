import pytest
from server.protocol import (
    ProtocolError, encode, decode, validate_command, COMMAND_SCHEMAS,
)


def test_encode_serializes_and_appends_newline():
    payload = {"type": "ping", "n": 1}
    result = encode(payload)
    assert result.endswith(b"\n")
    assert b'"type":"ping"' in result or b'"type": "ping"' in result


def test_decode_parses_valid_json():
    assert decode(b'{"type":"ping"}\n') == {"type": "ping"}


def test_decode_strips_trailing_whitespace():
    assert decode(b'  {"type":"ping"}  \n') == {"type": "ping"}


def test_decode_rejects_non_json():
    with pytest.raises(ProtocolError, match="JSON"):
        decode(b"not json\n")


def test_decode_rejects_non_object():
    with pytest.raises(ProtocolError, match="object"):
        decode(b'[1, 2, 3]\n')


def test_decode_rejects_empty_line():
    with pytest.raises(ProtocolError):
        decode(b"\n")


def test_validate_accepts_join_with_username():
    validate_command({"type": "join", "username": "Alice"})  # no raises


def test_validate_rejects_unknown_type():
    with pytest.raises(ProtocolError, match="unknown type"):
        validate_command({"type": "dance"})


def test_validate_rejects_missing_type():
    with pytest.raises(ProtocolError, match="'type'"):
        validate_command({})


def test_validate_rejects_join_without_username():
    with pytest.raises(ProtocolError, match="username"):
        validate_command({"type": "join"})


def test_validate_rejects_wrong_field_type():
    with pytest.raises(ProtocolError, match="str"):
        validate_command({"type": "join", "username": 42})


def test_validate_accepts_move_piece_with_three_fields():
    validate_command({
        "type": "move_piece",
        "piece_index": 0,
        "dice_value": 3,
        "action": "advance",
    })


def test_validate_rejects_move_piece_missing_field():
    with pytest.raises(ProtocolError, match="dice_value"):
        validate_command({"type": "move_piece", "piece_index": 0, "action": "advance"})


def test_all_commands_have_schema():
    # Sanity: the schema table is non-empty and contains known types.
    assert "join" in COMMAND_SCHEMAS
    assert "roll_dice" in COMMAND_SCHEMAS
