from flask import Blueprint, request, jsonify
from server.services.stats import get_ranking, get_player_stats
from server.services.auth import decode_token
from server.models.user import User

stats_bp = Blueprint("stats", __name__, url_prefix="/api")


@stats_bp.route("/ranking", methods=["GET"])
def ranking():
    limit = request.args.get("limit", 20, type=int)
    return jsonify(get_ranking(limit))


@stats_bp.route("/stats", methods=["GET"])
def stats():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    payload = decode_token(token)
    if not payload:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify(get_player_stats(payload["user_id"]))


@stats_bp.route("/stats/<username>", methods=["GET"])
def stats_by_username(username):
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(get_player_stats(user.id))
