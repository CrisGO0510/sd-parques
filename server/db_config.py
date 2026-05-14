"""Database configuration and connection management."""
from __future__ import annotations

import mysql.connector
from mysql.connector import Error
from decimal import Decimal
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def convert_decimal(obj: any) -> any:
    """Convert Decimal objects to int or float for JSON serialization."""
    if isinstance(obj, dict):
        return {k: convert_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimal(item) for item in obj]
    elif isinstance(obj, Decimal):
        return float(obj) if obj % 1 else int(obj)
    return obj


class DatabaseConfig:
    """Configuration for MySQL database connection."""
    
    def __init__(
        self,
        host: str = "localhost",
        user: str = "root",
        password: str = "",
        database: str = "sd_parques",
        port: int = 3306,
    ):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port

    def get_connection(self):
        """Create and return a new database connection."""
        try:
            conn = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port,
            )
            return conn
        except Error as e:
            logger.error(f"Error connecting to MySQL: {e}")
            raise


class PlayerDatabase:
    """Manages player-related database operations."""
    
    def __init__(self, db_config: DatabaseConfig):
        self.db_config = db_config

    def get_or_create_player(self, username: str) -> dict:
        """
        Get existing player or create new one if not exists.
        Returns a dict with player data including stats.
        """
        conn = self.db_config.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Check if player exists
            cursor.execute(
                "SELECT id, username, games_played, games_won FROM players WHERE username = %s",
                (username,)
            )
            result = cursor.fetchone()
            
            if result:
                return convert_decimal(result)
            
            # Create new player
            cursor.execute(
                "INSERT INTO players (username, games_played, games_won) VALUES (%s, %s, %s)",
                (username, 0, 0)
            )
            conn.commit()
            
            # Return the created player
            cursor.execute(
                "SELECT id, username, games_played, games_won FROM players WHERE username = %s",
                (username,)
            )
            return convert_decimal(cursor.fetchone())
            
        finally:
            cursor.close()
            conn.close()

    def get_player_by_id(self, player_id: int) -> Optional[dict]:
        """Get player data by ID."""
        conn = self.db_config.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute(
                "SELECT id, username, games_played, games_won FROM players WHERE id = %s",
                (player_id,)
            )
            result = cursor.fetchone()
            return convert_decimal(result) if result else None
        finally:
            cursor.close()
            conn.close()

    def get_all_players(self) -> list[dict]:
        """Get all players sorted by win percentage."""
        conn = self.db_config.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute(
                """
                SELECT 
                    id, 
                    username, 
                    games_played, 
                    games_won,
                    CASE 
                        WHEN games_played > 0 THEN ROUND((games_won / games_played) * 100, 2)
                        ELSE 0
                    END as win_percentage
                FROM players
                ORDER BY win_percentage DESC, games_won DESC
                """
            )
            result = cursor.fetchall()
            return [convert_decimal(row) for row in result]
        finally:
            cursor.close()
            conn.close()

    def update_player_stats(self, player_id: int, game_won: bool) -> dict:
        """
        Update player statistics after a game.
        game_won: True if player won, False otherwise.
        Returns updated player data.
        """
        conn = self.db_config.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Increment games_played
            cursor.execute(
                "UPDATE players SET games_played = games_played + 1 WHERE id = %s",
                (player_id,)
            )
            
            # Increment games_won if applicable
            if game_won:
                cursor.execute(
                    "UPDATE players SET games_won = games_won + 1 WHERE id = %s",
                    (player_id,)
                )
            
            conn.commit()
            
            # Return updated player data
            cursor.execute(
                "SELECT id, username, games_played, games_won FROM players WHERE id = %s",
                (player_id,)
            )
            return convert_decimal(cursor.fetchone())
            
        finally:
            cursor.close()
            conn.close()
