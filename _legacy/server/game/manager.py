import threading
from server.game.engine import GameEngine
from server.game.constants import MAX_PLAYERS, COLORS

class LobbyPlayer:
    def __init__(self, user_id: int, username: str, sid: str):
        self.user_id = user_id
        self.username = username
        self.sid = sid
        self.color = None

class GameManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.lobby: list[LobbyPlayer] = []
        self.active_game: GameEngine | None = None
        self.game_players: dict[str, LobbyPlayer] = {}  # color -> LobbyPlayer
        self.sid_to_color: dict[str, str] = {}  # sid -> color
        self.game_thread: threading.Thread | None = None
        self.game_in_progress = False

    def join_lobby(self, user_id: int, username: str, sid: str) -> dict:
        with self.lock:
            if self.game_in_progress:
                return {"error": "A game is already in progress"}
            if len(self.lobby) >= MAX_PLAYERS:
                return {"error": "Lobby is full"}
            if any(p.user_id == user_id for p in self.lobby):
                return {"error": "Already in lobby"}
            player = LobbyPlayer(user_id, username, sid)
            self.lobby.append(player)
            return {
                "players": [{"username": p.username, "color": p.color} for p in self.lobby],
                "available_colors": self._available_colors(),
                "is_host": len(self.lobby) == 1,
            }

    def leave_lobby(self, sid: str) -> None:
        with self.lock:
            self.lobby = [p for p in self.lobby if p.sid != sid]

    def select_color(self, sid: str, color: str) -> dict:
        with self.lock:
            if color not in COLORS:
                return {"error": "Invalid color"}
            if any(p.color == color and p.sid != sid for p in self.lobby):
                return {"error": "Color already taken"}
            for player in self.lobby:
                if player.sid == sid:
                    player.color = color
                    break
            return {
                "players": [{"username": p.username, "color": p.color} for p in self.lobby],
                "available_colors": self._available_colors(),
            }

    def _available_colors(self) -> list[str]:
        taken = {p.color for p in self.lobby if p.color}
        return [c for c in COLORS if c not in taken]

    def can_start(self) -> bool:
        with self.lock:
            return (
                2 <= len(self.lobby) <= MAX_PLAYERS
                and all(p.color is not None for p in self.lobby)
                and not self.game_in_progress
            )

    def start_game(self, db_game_id: int) -> GameEngine:
        with self.lock:
            colors = [p.color for p in self.lobby]
            self.active_game = GameEngine(db_game_id, colors)
            self.game_in_progress = True
            for player in self.lobby:
                self.game_players[player.color] = player
                self.sid_to_color[player.sid] = player.color
            return self.active_game

    def end_game(self) -> None:
        with self.lock:
            self.active_game = None
            self.game_players.clear()
            self.sid_to_color.clear()
            self.game_in_progress = False
            self.lobby.clear()

    def get_color_by_sid(self, sid: str) -> str | None:
        return self.sid_to_color.get(sid)

    def get_player_by_sid(self, sid: str) -> LobbyPlayer | None:
        for player in self.lobby:
            if player.sid == sid:
                return player
        return None

    def handle_disconnect(self, sid: str) -> str | None:
        color = self.sid_to_color.get(sid)
        if color and self.active_game:
            self.active_game.disconnected.add(color)
        return color

    def handle_reconnect(self, sid: str, user_id: int) -> str | None:
        with self.lock:
            for color, player in self.game_players.items():
                if player.user_id == user_id:
                    old_sid = player.sid
                    player.sid = sid
                    if old_sid in self.sid_to_color:
                        del self.sid_to_color[old_sid]
                    self.sid_to_color[sid] = color
                    if self.active_game:
                        self.active_game.disconnected.discard(color)
                    return color
        return None

# Singleton
game_manager = GameManager()
