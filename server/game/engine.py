import random
import threading
from server.game.board import Board
from server.game.constants import PIECES_PER_PLAYER

class GameEngine:
    def __init__(self, game_id: int, player_colors: list[str]):
        self.game_id = game_id
        self.board = Board(player_colors)
        self.player_colors = player_colors
        self.current_turn_index = 0
        self.consecutive_pairs = 0
        self.dice = (0, 0)
        self.phase = "rolling"  # rolling, moving, finished
        self.move_count = 0
        self.lock = threading.Lock()
        self.winner = None
        self.disconnected: set[str] = set()
        self.initial_rolls: dict[str, int] = {}
        self.phase_initial = True  # True until initial dice roll determines order

    @property
    def current_color(self) -> str:
        return self.player_colors[self.current_turn_index]

    def roll_initial(self, color: str) -> tuple[int, int]:
        """Roll dice for initial turn order determination."""
        d1 = random.randint(1, 6)
        d2 = random.randint(1, 6)
        self.initial_rolls[color] = d1 + d2
        if len(self.initial_rolls) == len(self.player_colors):
            sorted_colors = sorted(
                self.initial_rolls.keys(),
                key=lambda c: self.initial_rolls[c],
                reverse=True,
            )
            self.player_colors = sorted_colors
            self.current_turn_index = 0
            self.phase_initial = False
            self.phase = "rolling"
        return d1, d2

    def roll_dice(self) -> tuple[int, int]:
        with self.lock:
            d1 = random.randint(1, 6)
            d2 = random.randint(1, 6)
            self.dice = (d1, d2)
            self.phase = "moving"
            return d1, d2

    def is_pair(self) -> bool:
        return self.dice[0] == self.dice[1]

    def dice_total(self) -> int:
        return self.dice[0] + self.dice[1]

    def get_jailed_pieces(self, color: str) -> list[int]:
        return [p.index for p in self.board.pieces[color] if p.state == "jail"]

    def get_movable_pieces(self, color: str) -> list[dict]:
        total = self.dice_total()
        movable = []
        for piece in self.board.pieces[color]:
            if piece.state in ("board", "home_stretch"):
                original_state = piece.state
                original_pos = piece.position
                original_home = piece.home_position
                # Snapshot potential victims
                victims_before = []
                if piece.state == "board":
                    new_pos = (piece.position + total) % 68
                    for vc, vps in self.board.pieces.items():
                        if vc == color:
                            continue
                        for vp in vps:
                            if vp.state == "board" and vp.position == new_pos:
                                victims_before.append((vp, vp.state, vp.position))
                result = self.board.move_piece(color, piece.index, total)
                # Revert
                piece.state = original_state
                piece.position = original_pos
                piece.home_position = original_home
                for vp, vs, vpos in victims_before:
                    vp.state = vs
                    vp.position = vpos
                if result["action"] != "invalid":
                    movable.append({
                        "piece_index": piece.index,
                        "steps": total,
                        "preview_action": result["action"],
                    })
        return movable

    def execute_move(self, color: str, piece_index: int) -> dict:
        with self.lock:
            if color != self.current_color:
                return {"error": "Not your turn"}
            if self.phase != "moving":
                return {"error": "Roll dice first"}

            total = self.dice_total()
            piece = self.board.get_piece(color, piece_index)

            if piece.state == "jail":
                if not self.is_pair():
                    return {"error": "Need pairs to exit jail"}
                self.board.exit_from_jail(color, piece_index)
                result = {"action": "enter", "captured": None}
            else:
                result = self.board.move_piece(color, piece_index, total)
                if result["action"] == "invalid":
                    return {"error": "Invalid move"}

            self.move_count += 1

            if self.board.all_finished(color):
                self.winner = color
                self.phase = "finished"
                result["winner"] = color

            if self.is_pair():
                self.consecutive_pairs += 1
                if self.consecutive_pairs >= 3:
                    result["triple_pairs"] = True
                    self.consecutive_pairs = 0
                self.phase = "rolling"
            else:
                self.consecutive_pairs = 0
                self._advance_turn()

            return result

    def _advance_turn(self) -> None:
        self.phase = "rolling"
        attempts = 0
        while attempts < len(self.player_colors):
            self.current_turn_index = (self.current_turn_index + 1) % len(self.player_colors)
            if self.current_color not in self.disconnected:
                return
            attempts += 1

    def finish_piece_by_choice(self, color: str, piece_index: int) -> dict:
        with self.lock:
            piece = self.board.get_piece(color, piece_index)
            if piece.state == "finished":
                return {"error": "Piece already finished"}
            piece.state = "finished"
            piece.position = -1
            piece.home_position = -1
            if self.board.all_finished(color):
                self.winner = color
                self.phase = "finished"
            return {"action": "finish", "piece_index": piece_index}

    def get_state(self) -> dict:
        return {
            "game_id": self.game_id,
            "board": self.board.to_dict(),
            "current_turn": self.current_color,
            "phase": self.phase,
            "dice": self.dice,
            "winner": self.winner,
        }
