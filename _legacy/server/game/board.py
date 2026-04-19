from server.game.constants import (
    BOARD_SIZE, HOME_STRETCH_SIZE, PIECES_PER_PLAYER, COLORS,
    EXIT_POSITIONS, SAFE_POSITIONS, HOME_ENTRY,
)

class Piece:
    def __init__(self, color: str, index: int):
        self.color = color
        self.index = index
        self.state = "jail"  # jail, board, home_stretch, finished
        self.position = -1   # -1 when in jail, 0-67 on board
        self.home_position = -1  # 0-7 in home stretch

    def to_dict(self) -> dict:
        return {
            "color": self.color, "index": self.index,
            "state": self.state, "position": self.position,
            "home_position": self.home_position,
        }

class Board:
    def __init__(self, player_colors: list[str]):
        self.player_colors = player_colors
        self.pieces: dict[str, list[Piece]] = {}
        for color in player_colors:
            self.pieces[color] = [Piece(color, i) for i in range(PIECES_PER_PLAYER)]

    def get_piece(self, color: str, index: int) -> Piece:
        return self.pieces[color][index]

    def exit_from_jail(self, color: str, piece_index: int) -> None:
        piece = self.get_piece(color, piece_index)
        piece.state = "board"
        piece.position = EXIT_POSITIONS[color]

    def is_safe_position(self, position: int) -> bool:
        return position in SAFE_POSITIONS

    def is_exit_position(self, position: int) -> bool:
        return position in EXIT_POSITIONS.values()

    def get_pieces_at(self, position: int, exclude_color: str = None) -> list[Piece]:
        result = []
        for color, pieces in self.pieces.items():
            if color == exclude_color:
                continue
            for piece in pieces:
                if piece.state == "board" and piece.position == position:
                    result.append(piece)
        return result

    def move_piece(self, color: str, piece_index: int, steps: int) -> dict:
        piece = self.get_piece(color, piece_index)
        result = {"action": "move", "captured": None}

        if piece.state == "board":
            home_entry = HOME_ENTRY[color]
            exit_pos = EXIT_POSITIONS[color]

            if piece.position >= exit_pos:
                distance_from_start = piece.position - exit_pos
            else:
                distance_from_start = BOARD_SIZE - exit_pos + piece.position

            new_distance = distance_from_start + steps

            home_entry_distance = (home_entry - exit_pos) % BOARD_SIZE
            if home_entry_distance == 0:
                home_entry_distance = BOARD_SIZE

            if distance_from_start <= home_entry_distance < new_distance:
                overflow = new_distance - home_entry_distance - 1
                if overflow < HOME_STRETCH_SIZE:
                    piece.state = "home_stretch"
                    piece.home_position = overflow
                    piece.position = -1
                    result["action"] = "enter"
                    if overflow == HOME_STRETCH_SIZE - 1:
                        piece.state = "finished"
                        result["action"] = "finish"
                    return result
                else:
                    return {"action": "invalid", "captured": None}

            new_position = (piece.position + steps) % BOARD_SIZE
            piece.position = new_position

            if not self.is_safe_position(new_position):
                victims = self.get_pieces_at(new_position, exclude_color=color)
                if victims:
                    victim = victims[0]
                    victim.state = "jail"
                    victim.position = -1
                    result["action"] = "eat"
                    result["captured"] = victim.to_dict()

        elif piece.state == "home_stretch":
            new_home = piece.home_position + steps
            if new_home == HOME_STRETCH_SIZE - 1:
                piece.home_position = new_home
                piece.state = "finished"
                result["action"] = "finish"
            elif new_home < HOME_STRETCH_SIZE:
                piece.home_position = new_home
            else:
                return {"action": "invalid", "captured": None}

        return result

    def all_finished(self, color: str) -> bool:
        return all(p.state == "finished" for p in self.pieces[color])

    def to_dict(self) -> dict:
        return {
            color: [p.to_dict() for p in pieces]
            for color, pieces in self.pieces.items()
        }
