from flask_socketio import emit
from flask import request
from server.extensions import socketio, db
from server.game.manager import game_manager
from server.models.move import GameMove
from server.models.game import Game
from server.services.recommendation import get_recommendation
from datetime import datetime, timezone


@socketio.on("roll_dice")
def handle_roll_dice():
    engine = game_manager.active_game
    if not engine:
        emit("error", {"message": "No active game"})
        return
    color = game_manager.get_color_by_sid(request.sid)
    if color != engine.current_color:
        emit("error", {"message": "Not your turn"})
        return
    if engine.phase != "rolling":
        emit("error", {"message": "Already rolled"})
        return
    d1, d2 = engine.roll_dice()
    room = f"game_{engine.game_id}"
    socketio.emit("dice_result", {
        "dice_1": d1, "dice_2": d2, "is_pair": d1 == d2,
        "player": color,
        "movable": engine.get_movable_pieces(color),
        "jailed": engine.get_jailed_pieces(color),
        "can_exit_jail": d1 == d2,
    }, room=room)


@socketio.on("move_piece")
def handle_move_piece(data):
    engine = game_manager.active_game
    if not engine:
        emit("error", {"message": "No active game"})
        return
    color = game_manager.get_color_by_sid(request.sid)
    piece_index = data.get("piece_index")
    piece = engine.board.get_piece(color, piece_index)
    from_pos = piece.position
    from_state = piece.state
    result = engine.execute_move(color, piece_index)
    if "error" in result:
        emit("error", {"message": result["error"]})
        return
    room = f"game_{engine.game_id}"
    player = game_manager.game_players[color]
    move = GameMove(
        game_id=engine.game_id, user_id=player.user_id,
        move_number=engine.move_count,
        dice_1=engine.dice[0], dice_2=engine.dice[1],
        piece_index=piece_index,
        from_position=from_pos if from_state == "board" else -1,
        to_position=piece.position if piece.state == "board" else -1,
        action=result["action"],
    )
    db.session.add(move)
    db.session.commit()
    socketio.emit("board_update", engine.get_state(), room=room)
    if result.get("triple_pairs"):
        socketio.emit("triple_pairs", {"player": color, "message": "Choose a piece to finish!"}, room=room)
    if result.get("winner"):
        _handle_game_over(engine, result["winner"])


@socketio.on("finish_piece_choice")
def handle_finish_piece_choice(data):
    engine = game_manager.active_game
    if not engine:
        return
    color = game_manager.get_color_by_sid(request.sid)
    piece_index = data.get("piece_index")
    result = engine.finish_piece_by_choice(color, piece_index)
    if "error" in result:
        emit("error", {"message": result["error"]})
        return
    room = f"game_{engine.game_id}"
    socketio.emit("board_update", engine.get_state(), room=room)
    if engine.winner:
        _handle_game_over(engine, engine.winner)


@socketio.on("pass_turn")
def handle_pass_turn():
    engine = game_manager.active_game
    if not engine:
        return
    color = game_manager.get_color_by_sid(request.sid)
    if color != engine.current_color:
        return
    with engine.lock:
        engine._advance_turn()
        engine.phase = "rolling"
    room = f"game_{engine.game_id}"
    socketio.emit("board_update", engine.get_state(), room=room)


def _handle_game_over(engine, winner_color: str):
    room = f"game_{engine.game_id}"
    player = game_manager.game_players[winner_color]
    game = db.session.get(Game, engine.game_id)
    game.status = "finished"
    game.winner_id = player.user_id
    game.finished_at = datetime.now(timezone.utc)
    db.session.commit()
    socketio.emit("game_over", {"winner": winner_color, "winner_name": player.username}, room=room)
    game_manager.end_game()


@socketio.on("request_recommendation")
def handle_request_recommendation():
    engine = game_manager.active_game
    if not engine:
        emit("error", {"message": "No active game"})
        return
    color = game_manager.get_color_by_sid(request.sid)
    if color != engine.current_color:
        emit("error", {"message": "Not your turn"})
        return
    result = get_recommendation(engine, color)
    emit("recommendation", result)


@socketio.on("disconnect")
def handle_disconnect():
    color = game_manager.handle_disconnect(request.sid)
    if color and game_manager.active_game:
        room = f"game_{game_manager.active_game.game_id}"
        socketio.emit("player_disconnected", {"color": color}, room=room)
