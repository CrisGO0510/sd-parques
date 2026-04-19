import time
import threading
from server.extensions import socketio


class BerkeleySynchronizer:
    def __init__(self, game_room: str):
        self.game_room = game_room
        self.responses: dict[str, float] = {}
        self.lock = threading.Lock()
        self.waiting = threading.Event()

    def request_sync(self, player_sids: list[str]) -> None:
        self.responses.clear()
        server_time = time.time() * 1000
        socketio.emit("sync_request", {"server_time": server_time}, room=self.game_room)
        self.waiting.clear()
        deadline = time.time() + 5
        while len(self.responses) < len(player_sids) and time.time() < deadline:
            self.waiting.wait(timeout=0.5)
        if not self.responses:
            return
        diffs = []
        for sid, client_time in self.responses.items():
            diff = client_time - server_time
            diffs.append(diff)
        avg_diff = sum(diffs) / len(diffs)
        for sid, client_time in self.responses.items():
            adjustment = avg_diff - (client_time - server_time)
            socketio.emit("sync_adjust", {"offset_ms": round(adjustment, 2)}, to=sid)

    def receive_response(self, sid: str, client_time: float) -> None:
        with self.lock:
            self.responses[sid] = client_time
            if len(self.responses) >= 2:
                self.waiting.set()
