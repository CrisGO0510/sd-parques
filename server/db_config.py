"""Database configuration and connection management."""
from __future__ import annotations

import os
import psycopg2
from psycopg2 import Error
from psycopg2.extras import RealDictCursor
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Configuration for PostgreSQL database connection."""
    
    def __init__(self, database_url: str | None = None):
        # Use DATABASE_URL from environment (Render provides this automatically)
        # Fallback to local PostgreSQL if not in production
        self.database_url = database_url or os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/sd_parques"
        )

    def get_connection(self):
        """Create and return a new database connection."""
        try:
            conn = psycopg2.connect(self.database_url)
            return conn
        except Error as e:
            logger.error(f"Error connecting to PostgreSQL: {e}")
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
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Check if player exists
            cursor.execute(
                "SELECT id, username, games_played, games_won FROM players WHERE username = %s",
                (username,)
            )
            result = cursor.fetchone()
            
            if result:
                return dict(result)
            
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
            return dict(cursor.fetchone())
            
        finally:
            cursor.close()
            conn.close()

    def get_player_by_id(self, player_id: int) -> Optional[dict]:
        """Get player data by ID."""
        conn = self.db_config.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute(
                "SELECT id, username, games_played, games_won FROM players WHERE id = %s",
                (player_id,)
            )
            result = cursor.fetchone()
            return dict(result) if result else None
        finally:
            cursor.close()
            conn.close()

    def get_all_players(self) -> list[dict]:
        """Get all players sorted by win percentage."""
        conn = self.db_config.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute(
                """
                SELECT 
                    id, 
                    username, 
                    games_played, 
                    games_won,
                    CASE 
                        WHEN games_played > 0 THEN ROUND((CAST(games_won AS numeric) / games_played) * 100, 2)
                        ELSE 0
                    END as win_percentage
                FROM players
                ORDER BY win_percentage DESC, games_won DESC
                """
            )
            result = cursor.fetchall()
            # `win_percentage` llega como Decimal (columna numeric) y no es
            # serializable a JSON; lo convertimos a float para el protocolo.
            players = []
            for row in result:
                player = dict(row)
                player["win_percentage"] = float(player["win_percentage"])
                players.append(player)
            return players
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
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
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
            return dict(cursor.fetchone())
            
        finally:
            cursor.close()
            conn.close()
