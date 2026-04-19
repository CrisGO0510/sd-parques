from server.extensions import db
from datetime import datetime, timezone

class Game(db.Model):
    __tablename__ = "games"
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), nullable=False, default="waiting")
    winner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    started_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at = db.Column(db.DateTime, nullable=True)
    winner = db.relationship("User", foreign_keys=[winner_id])
    players = db.relationship("GamePlayer", back_populates="game")

class GamePlayer(db.Model):
    __tablename__ = "game_players"
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("games.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    color = db.Column(db.String(10), nullable=False)
    finish_position = db.Column(db.Integer, nullable=True)
    game = db.relationship("Game", back_populates="players")
    user = db.relationship("User")
