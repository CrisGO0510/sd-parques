"""Pruebas de serialización del ranking.

PostgreSQL devuelve las columnas `numeric` (como `win_percentage`, calculada con
ROUND(... AS numeric)) como objetos `Decimal`, que `json.dumps` no sabe serializar.
Estas pruebas verifican que `get_all_players()` entrega datos serializables a JSON.
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

from server.db_config import PlayerDatabase
from server.protocol import encode


def _make_db_returning(rows: list[dict]) -> PlayerDatabase:
    """Crea un PlayerDatabase cuyo cursor devuelve `rows` en fetchall()."""
    cursor = MagicMock()
    cursor.fetchall.return_value = rows
    conn = MagicMock()
    conn.cursor.return_value = cursor

    db_config = MagicMock()
    db_config.get_connection.return_value = conn
    return PlayerDatabase(db_config)


def test_get_all_players_returns_json_serializable_win_percentage():
    rows = [
        {
            "id": 1,
            "username": "alice",
            "games_played": 4,
            "games_won": 1,
            "win_percentage": Decimal("25.00"),  # tal como lo entrega psycopg2
        }
    ]
    db = _make_db_returning(rows)

    players = db.get_all_players()

    # No debe contener Decimal: json.dumps debe funcionar.
    encode({"type": "ranking_update", "players": players})
    assert isinstance(players[0]["win_percentage"], float)
    assert players[0]["win_percentage"] == 25.0
