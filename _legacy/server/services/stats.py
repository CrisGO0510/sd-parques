from server.extensions import db
from server.models.user import User
from server.models.game import Game, GamePlayer
from sqlalchemy import func


def get_ranking(limit: int = 20) -> list[dict]:
    results = (
        db.session.query(User.username, func.count(Game.id).label("wins"))
        .join(Game, Game.winner_id == User.id)
        .filter(Game.status == "finished")
        .group_by(User.id)
        .order_by(func.count(Game.id).desc())
        .limit(limit)
        .all()
    )
    return [{"username": r.username, "wins": r.wins} for r in results]


def get_player_stats(user_id: int) -> dict:
    total_games = (
        db.session.query(func.count(GamePlayer.id))
        .filter(GamePlayer.user_id == user_id)
        .scalar()
    ) or 0
    wins = (
        db.session.query(func.count(Game.id))
        .filter(Game.winner_id == user_id, Game.status == "finished")
        .scalar()
    ) or 0
    win_probability = wins / total_games if total_games > 0 else 0.0
    recent_games = (
        db.session.query(Game, GamePlayer)
        .join(GamePlayer, GamePlayer.game_id == Game.id)
        .filter(GamePlayer.user_id == user_id, Game.status == "finished")
        .order_by(Game.finished_at.desc())
        .limit(10)
        .all()
    )
    history = []
    for game, gp in recent_games:
        history.append({
            "game_id": game.id,
            "color": gp.color,
            "finish_position": gp.finish_position,
            "won": game.winner_id == user_id,
            "date": game.finished_at.isoformat() if game.finished_at else None,
        })
    return {
        "total_games": total_games,
        "wins": wins,
        "win_probability": round(win_probability, 4),
        "recent_games": history,
    }
