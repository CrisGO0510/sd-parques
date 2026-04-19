from server.extensions import db
from datetime import datetime, timezone

class GameMove(db.Model):
    __tablename__ = "game_moves"
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("games.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    move_number = db.Column(db.Integer, nullable=False)
    dice_1 = db.Column(db.Integer, nullable=False)
    dice_2 = db.Column(db.Integer, nullable=False)
    piece_index = db.Column(db.Integer, nullable=False)
    from_position = db.Column(db.Integer, nullable=False)
    to_position = db.Column(db.Integer, nullable=False)
    action = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
