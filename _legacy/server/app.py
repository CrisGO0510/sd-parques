from flask import Flask
from flask_cors import CORS
from server.config import Config
from server.extensions import db, socketio

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)
    db.init_app(app)
    socketio.init_app(app)
    with app.app_context():
        import server.models  # noqa: F401
        db.create_all()
    from server.routes.auth import auth_bp
    app.register_blueprint(auth_bp)
    from server.routes.stats import stats_bp
    app.register_blueprint(stats_bp)
    import server.sockets.sync  # noqa: F401
    import server.sockets.lobby  # noqa: F401
    import server.sockets.game_events  # noqa: F401
    return app

if __name__ == "__main__":
    app = create_app()
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
