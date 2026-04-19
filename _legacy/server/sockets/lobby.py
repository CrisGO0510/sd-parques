from flask_socketio import emit, join_room, leave_room
from flask import request
from server.extensions import socketio, db
from server.game.manager import game_manager
from server.services.auth import decode_token
from server.models.game import Game, GamePlayer


@socketio.on("join_lobby")
def handle_join_lobby(data):
    token = data.get("token")
    payload = decode_token(token)
    if not payload:
        emit("error", {"message": "Invalid token"})
        return
    result = game_manager.join_lobby(payload["user_id"], payload["username"], request.sid)
    if "error" in result:
        emit("error", {"message": result["error"]})
        return
    join_room("lobby")
    socketio.emit("lobby_update", result, room="lobby")


@socketio.on("leave_lobby")
def handle_leave_lobby():
    game_manager.leave_lobby(request.sid)
    leave_room("lobby")
    players = [{"username": p.username, "color": p.color} for p in game_manager.lobby]
    available = game_manager._available_colors()
    socketio.emit("lobby_update", {"players": players, "available_colors": available}, room="lobby")


@socketio.on("select_color")
def handle_select_color(data):
    color = data.get("color")
    result = game_manager.select_color(request.sid, color)
    if "error" in result:
        emit("error", {"message": result["error"]})
        return
    socketio.emit("lobby_update", result, room="lobby")


@socketio.on("start_game")
def handle_start_game():
    if not game_manager.can_start():
        emit("error", {"message": "Cannot start game yet"})
        return
    game_record = Game(status="playing")
    db.session.add(game_record)
    db.session.commit()
    for player in game_manager.lobby:
        gp = GamePlayer(game_id=game_record.id, user_id=player.user_id, color=player.color)
        db.session.add(gp)
    db.session.commit()
    engine = game_manager.start_game(game_record.id)
    for color, player in game_manager.game_players.items():
        leave_room("lobby", sid=player.sid)
        join_room(f"game_{game_record.id}", sid=player.sid)
    socketio.emit("game_start", engine.get_state(), room=f"game_{game_record.id}")
