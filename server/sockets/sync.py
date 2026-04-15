from flask import request
from server.extensions import socketio

_synchronizers: dict[str, "BerkeleySynchronizer"] = {}


def get_synchronizer(game_room: str):
    from server.services.berkeley import BerkeleySynchronizer
    if game_room not in _synchronizers:
        _synchronizers[game_room] = BerkeleySynchronizer(game_room)
    return _synchronizers[game_room]


def remove_synchronizer(game_room: str):
    _synchronizers.pop(game_room, None)


@socketio.on("sync_response")
def handle_sync_response(data):
    game_room = data.get("game_room")
    client_time = data.get("client_time")
    if game_room and client_time:
        sync = get_synchronizer(game_room)
        sync.receive_response(request.sid, client_time)
