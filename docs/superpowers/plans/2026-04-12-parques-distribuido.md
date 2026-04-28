# Parqués Distribuido — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a distributed Parqués board game where 2-4 players can play over the network via web or Android app, with real-time communication, clock synchronization, AI-powered recommendations, and player statistics.

**Architecture:** Monolithic Flask server with Flask-SocketIO handling both REST endpoints (auth, stats) and real-time game events. Quasar (Vue 3) client deployable as web app and Android APK via Capacitor. PostgreSQL for persistence. One thread per active game with semaphore-based turn control.

**Tech Stack:** Python 3.11, Flask, Flask-SocketIO, SQLAlchemy, PostgreSQL, PyJWT, Vue 3, Quasar Framework, Pinia, Capacitor, Claude API (anthropic SDK)

**Spec:** `docs/superpowers/specs/2026-04-12-parques-distribuido-design.md`

---

## File Structure

### Server (`server/`)

| File | Responsibility |
|---|---|
| `app.py` | Flask + SocketIO init, register blueprints/events, entry point |
| `config.py` | DB URI, JWT secret, Claude API key, env-based config |
| `extensions.py` | Shared instances: db (SQLAlchemy), socketio, jwt |
| `models/user.py` | User model (id, username, password_hash, created_at) |
| `models/game.py` | Game, GamePlayer models |
| `models/move.py` | GameMove model |
| `game/constants.py` | Board dimensions, safe positions, exit offsets, colors |
| `game/board.py` | Board class: piece positions, safe/exit logic, home stretch |
| `game/engine.py` | GameEngine: rules, validation, turn management, win condition |
| `game/manager.py` | GameManager: lobby, create/destroy games, thread lifecycle |
| `services/auth.py` | register, login, hash password, generate/verify JWT |
| `services/stats.py` | Ranking queries, win probability, match history |
| `services/recommendation.py` | Heuristic scorer + LLM explanation generator |
| `services/berkeley.py` | Berkeley clock sync algorithm |
| `sockets/lobby.py` | Socket events: join_lobby, select_color, start_game |
| `sockets/game_events.py` | Socket events: roll_dice, move_piece, request_recommendation |
| `sockets/sync.py` | Socket events: sync_request, sync_response |
| `routes/auth.py` | Flask blueprint: POST /api/register, POST /api/login |
| `routes/stats.py` | Flask blueprint: GET /api/stats, GET /api/ranking |
| `requirements.txt` | Python dependencies |
| `Dockerfile` | Container for Render deploy |

### Client (`client/`)

| File | Responsibility |
|---|---|
| `src/router/index.js` | Vue Router: login, register, lobby, game, stats routes |
| `src/stores/userStore.js` | Pinia: auth state, JWT token, user profile |
| `src/stores/gameStore.js` | Pinia: board state, players, turn, pieces, dice |
| `src/composables/useSocket.js` | Socket.IO connection, event binding, reconnection |
| `src/composables/useAuth.js` | Login/register API calls, token management |
| `src/composables/useGame.js` | Game action helpers: roll, move, get recommendation |
| `src/pages/LoginPage.vue` | Login + register form |
| `src/pages/LobbyPage.vue` | Lobby: player list, color picker, start button |
| `src/pages/GamePage.vue` | Main game view: board + dice + player info + recommendations |
| `src/pages/StatsPage.vue` | Ranking table, player search, win probability |
| `src/components/BoardCanvas.vue` | Canvas/SVG rendering of the 68-cell board + home stretches |
| `src/components/DiceRoller.vue` | Dice display with roll animation |
| `src/components/PlayerInfo.vue` | Current players panel: name, color, piece count |
| `src/components/RecommendationPanel.vue` | AI recommendation display |

### Root

| File | Responsibility |
|---|---|
| `docker-compose.yml` | Local dev: server + PostgreSQL containers |
| `render.yaml` | Render deploy config (web service + PostgreSQL) |
| `.gitignore` | Python, Node, .env, .superpowers |

---

## Task 1: Project Scaffolding & Database Setup

**Files:**
- Create: `server/app.py`, `server/config.py`, `server/extensions.py`, `server/requirements.txt`, `server/models/__init__.py`, `server/models/user.py`, `server/models/game.py`, `server/models/move.py`, `docker-compose.yml`, `.gitignore`

- [ ] **Step 1: Create .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/

# Node
node_modules/
dist/

# Env
.env

# IDE
.vscode/
.idea/

# Superpowers
.superpowers/
```

- [ ] **Step 2: Create docker-compose.yml for local dev**

```yaml
version: '3.8'
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: parques
      POSTGRES_USER: parques
      POSTGRES_PASSWORD: parques_dev
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

- [ ] **Step 3: Start PostgreSQL**

Run: `docker-compose up -d db`
Expected: PostgreSQL running on localhost:5432

- [ ] **Step 4: Create Python virtual environment and requirements.txt**

```
flask==3.1.1
flask-socketio==5.5.1
flask-sqlalchemy==3.1.1
flask-cors==5.0.1
psycopg2-binary==2.9.10
python-socketio==5.12.1
eventlet==0.37.0
PyJWT==2.10.1
bcrypt==4.3.0
anthropic==0.52.0
python-dotenv==1.1.0
```

Run: `cd server && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

- [ ] **Step 5: Create server/config.py**

```python
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-prod")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "postgresql://parques:parques_dev@localhost:5432/parques"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET = os.getenv("JWT_SECRET", "jwt-secret-change-in-prod")
    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
```

- [ ] **Step 6: Create server/extensions.py**

```python
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO

db = SQLAlchemy()
socketio = SocketIO(cors_allowed_origins="*", async_mode="eventlet")
```

- [ ] **Step 7: Create server/models/user.py**

```python
from server.extensions import db
from datetime import datetime, timezone


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
```

- [ ] **Step 8: Create server/models/game.py**

```python
from server.extensions import db
from datetime import datetime, timezone


class Game(db.Model):
    __tablename__ = "games"

    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(
        db.String(20), nullable=False, default="waiting"
    )  # waiting, playing, finished
    winner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    started_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    finished_at = db.Column(db.DateTime, nullable=True)

    winner = db.relationship("User", foreign_keys=[winner_id])
    players = db.relationship("GamePlayer", back_populates="game")


class GamePlayer(db.Model):
    __tablename__ = "game_players"

    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("games.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    color = db.Column(
        db.String(10), nullable=False
    )  # red, blue, green, yellow
    finish_position = db.Column(db.Integer, nullable=True)

    game = db.relationship("Game", back_populates="players")
    user = db.relationship("User")
```

- [ ] **Step 9: Create server/models/move.py**

```python
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
    action = db.Column(
        db.String(10), nullable=False
    )  # move, jail, enter, finish, eat
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
```

- [ ] **Step 10: Create server/models/__init__.py**

```python
from server.models.user import User
from server.models.game import Game, GamePlayer
from server.models.move import GameMove

__all__ = ["User", "Game", "GamePlayer", "GameMove"]
```

- [ ] **Step 11: Create server/app.py**

```python
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

    return app


if __name__ == "__main__":
    app = create_app()
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
```

- [ ] **Step 12: Verify server starts and tables are created**

Run: `cd server && python -m server.app`
Expected: Server starts on port 5000, tables created in PostgreSQL. Verify with: `docker exec -it <container> psql -U parques -c "\dt"` — should show users, games, game_players, game_moves tables.

- [ ] **Step 13: Commit**

```bash
git add .gitignore docker-compose.yml server/
git commit -m "feat: project scaffolding with Flask, SQLAlchemy, PostgreSQL models"
```

---

## Task 2: Authentication (Register + Login + JWT)

**Files:**
- Create: `server/services/auth.py`, `server/routes/__init__.py`, `server/routes/auth.py`
- Modify: `server/app.py` (register blueprint)

- [ ] **Step 1: Create server/services/auth.py**

```python
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from server.extensions import db
from server.models.user import User
from server.config import Config


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def generate_token(user_id: int, username: str) -> str:
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        return None


def register_user(username: str, password: str) -> tuple[User | None, str]:
    if User.query.filter_by(username=username).first():
        return None, "Username already exists"
    user = User(username=username, password_hash=hash_password(password))
    db.session.add(user)
    db.session.commit()
    return user, ""


def login_user(username: str, password: str) -> tuple[str | None, str]:
    user = User.query.filter_by(username=username).first()
    if not user or not check_password(password, user.password_hash):
        return None, "Invalid username or password"
    token = generate_token(user.id, user.username)
    return token, ""
```

- [ ] **Step 2: Create server/routes/__init__.py**

```python
```

- [ ] **Step 3: Create server/routes/auth.py**

```python
from flask import Blueprint, request, jsonify
from server.services.auth import register_user, login_user

auth_bp = Blueprint("auth", __name__, url_prefix="/api")


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    if len(username) < 3 or len(username) > 50:
        return jsonify({"error": "Username must be 3-50 characters"}), 400
    if len(password) < 4:
        return jsonify({"error": "Password must be at least 4 characters"}), 400

    user, error = register_user(username, password)
    if error:
        return jsonify({"error": error}), 409

    return jsonify({"message": "User registered", "user_id": user.id}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "")

    token, error = login_user(username, password)
    if error:
        return jsonify({"error": error}), 401

    return jsonify({"token": token, "username": username}), 200
```

- [ ] **Step 4: Register blueprint in server/app.py**

Add after `db.create_all()`:

```python
    from server.routes.auth import auth_bp
    app.register_blueprint(auth_bp)
```

- [ ] **Step 5: Test auth endpoints manually**

Run server, then:
```bash
# Register
curl -X POST http://localhost:5000/api/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"1234"}'
# Expected: {"message":"User registered","user_id":1}

# Login
curl -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"1234"}'
# Expected: {"token":"eyJ...","username":"testuser"}
```

- [ ] **Step 6: Commit**

```bash
git add server/services/auth.py server/routes/ server/app.py
git commit -m "feat: add user registration and login with JWT"
```

---

## Task 3: Game Constants & Board Logic

**Files:**
- Create: `server/game/__init__.py`, `server/game/constants.py`, `server/game/board.py`
- Test: `server/tests/test_board.py`

- [ ] **Step 1: Create server/game/__init__.py**

```python
```

- [ ] **Step 2: Create server/game/constants.py**

```python
BOARD_SIZE = 68  # Main circuit cells
HOME_STRETCH_SIZE = 8  # Private cells per player before finish
PIECES_PER_PLAYER = 4
MAX_PLAYERS = 4

COLORS = ["red", "blue", "green", "yellow"]

# Each player's exit position on the main circuit
EXIT_POSITIONS = {
    "red": 0,
    "blue": 17,
    "green": 34,
    "yellow": 51,
}

# Safe positions on the main circuit (no captures allowed)
SAFE_POSITIONS = {5, 12, 17, 22, 29, 34, 39, 46, 51, 56, 63, 0}

# Entry to home stretch: the cell BEFORE entering the private corridor
# Each player enters home stretch after completing almost a full lap
HOME_ENTRY = {
    "red": 63,
    "blue": 12,
    "green": 29,
    "yellow": 46,
}
```

- [ ] **Step 3: Create server/game/board.py**

```python
from server.game.constants import (
    BOARD_SIZE,
    HOME_STRETCH_SIZE,
    PIECES_PER_PLAYER,
    COLORS,
    EXIT_POSITIONS,
    SAFE_POSITIONS,
    HOME_ENTRY,
)


class Piece:
    def __init__(self, color: str, index: int):
        self.color = color
        self.index = index
        self.state = "jail"  # jail, board, home_stretch, finished
        self.position = -1  # -1 when in jail, 0-67 on board
        self.home_position = -1  # 0-7 in home stretch

    def to_dict(self) -> dict:
        return {
            "color": self.color,
            "index": self.index,
            "state": self.state,
            "position": self.position,
            "home_position": self.home_position,
        }


class Board:
    def __init__(self, player_colors: list[str]):
        self.player_colors = player_colors
        self.pieces: dict[str, list[Piece]] = {}
        for color in player_colors:
            self.pieces[color] = [
                Piece(color, i) for i in range(PIECES_PER_PLAYER)
            ]

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

            # Calculate distance from exit to current position (in player's perspective)
            if piece.position >= exit_pos:
                distance_from_start = piece.position - exit_pos
            else:
                distance_from_start = BOARD_SIZE - exit_pos + piece.position

            new_distance = distance_from_start + steps

            # Check if entering home stretch
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

            # Normal move on main circuit
            new_position = (piece.position + steps) % BOARD_SIZE
            old_position = piece.position
            piece.position = new_position

            # Check for capture
            if not self.is_safe_position(new_position) and not self.is_exit_position(new_position):
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
```

- [ ] **Step 4: Write test server/tests/test_board.py**

```python
import pytest
from server.game.board import Board, Piece
from server.game.constants import EXIT_POSITIONS, SAFE_POSITIONS


def test_initial_state():
    board = Board(["red", "blue"])
    for color in ["red", "blue"]:
        for piece in board.pieces[color]:
            assert piece.state == "jail"
            assert piece.position == -1


def test_exit_from_jail():
    board = Board(["red"])
    board.exit_from_jail("red", 0)
    piece = board.get_piece("red", 0)
    assert piece.state == "board"
    assert piece.position == EXIT_POSITIONS["red"]


def test_move_piece():
    board = Board(["red"])
    board.exit_from_jail("red", 0)
    result = board.move_piece("red", 0, 5)
    piece = board.get_piece("red", 0)
    assert piece.state == "board"
    assert piece.position == 5
    assert result["action"] == "move"


def test_capture():
    board = Board(["red", "blue"])
    board.exit_from_jail("red", 0)
    board.exit_from_jail("blue", 0)
    # Move red to blue's position (17)
    result = board.move_piece("red", 0, 17)
    assert result["action"] == "eat"
    blue_piece = board.get_piece("blue", 0)
    assert blue_piece.state == "jail"


def test_no_capture_on_safe():
    board = Board(["red", "blue"])
    board.exit_from_jail("red", 0)
    board.exit_from_jail("blue", 0)
    # Move blue to safe position 22
    board.move_piece("blue", 0, 5)  # 17 + 5 = 22 (safe)
    # Move red to same safe position
    result = board.move_piece("red", 0, 22)
    assert result["action"] == "move"
    blue_piece = board.get_piece("blue", 0)
    assert blue_piece.state == "board"  # NOT captured


def test_all_finished():
    board = Board(["red"])
    for piece in board.pieces["red"]:
        piece.state = "finished"
    assert board.all_finished("red") is True


def test_to_dict():
    board = Board(["red"])
    d = board.to_dict()
    assert "red" in d
    assert len(d["red"]) == 4
```

- [ ] **Step 5: Run tests**

Run: `cd server && python -m pytest tests/test_board.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add server/game/ server/tests/
git commit -m "feat: board logic with piece movement, captures, and home stretch"
```

---

## Task 4: Game Engine (Rules, Turns, Dice)

**Files:**
- Create: `server/game/engine.py`
- Test: `server/tests/test_engine.py`

- [ ] **Step 1: Create server/game/engine.py**

```python
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
        self.initial_rolls: dict[str, int] = {}  # color -> roll total for turn order
        self.phase_initial = True  # True until initial dice roll determines order

    @property
    def current_color(self) -> str:
        return self.player_colors[self.current_turn_index]

    def roll_initial(self, color: str) -> tuple[int, int]:
        """Roll dice for initial turn order determination."""
        d1 = random.randint(1, 6)
        d2 = random.randint(1, 6)
        self.initial_rolls[color] = d1 + d2
        # Once all players rolled, determine order
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
        return [
            p.index
            for p in self.board.pieces[color]
            if p.state == "jail"
        ]

    def get_movable_pieces(self, color: str) -> list[dict]:
        total = self.dice_total()
        movable = []
        for piece in self.board.pieces[color]:
            if piece.state in ("board", "home_stretch"):
                # Simulate move: save full state including potential victims
                original_state = piece.state
                original_pos = piece.position
                original_home = piece.home_position
                # Snapshot potential victim state before move
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
                # Revert piece
                piece.state = original_state
                piece.position = original_pos
                piece.home_position = original_home
                # Revert any captured victims
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

            # Exit from jail with pairs
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

            # Check win
            if self.board.all_finished(color):
                self.winner = color
                self.phase = "finished"
                result["winner"] = color

            # Handle consecutive pairs
            if self.is_pair():
                self.consecutive_pairs += 1
                if self.consecutive_pairs >= 3:
                    # Reward: finish a piece of choice
                    result["triple_pairs"] = True
                    self.consecutive_pairs = 0
                self.phase = "rolling"  # Roll again
            else:
                self.consecutive_pairs = 0
                self._advance_turn()

            return result

    def _advance_turn(self) -> None:
        self.phase = "rolling"
        attempts = 0
        while attempts < len(self.player_colors):
            self.current_turn_index = (
                (self.current_turn_index + 1) % len(self.player_colors)
            )
            if self.current_color not in self.disconnected:
                return
            attempts += 1

    def finish_piece_by_choice(self, color: str, piece_index: int) -> dict:
        """Used when a player gets triple pairs and can finish any piece."""
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
```

- [ ] **Step 2: Write test server/tests/test_engine.py**

```python
from server.game.engine import GameEngine


def test_roll_dice():
    engine = GameEngine(1, ["red", "blue"])
    d1, d2 = engine.roll_dice()
    assert 1 <= d1 <= 6
    assert 1 <= d2 <= 6
    assert engine.phase == "moving"


def test_turn_advances():
    engine = GameEngine(1, ["red", "blue"])
    assert engine.current_color == "red"
    engine.roll_dice()
    # Force non-pair dice
    engine.dice = (1, 2)
    # Put a piece on the board to move
    engine.board.exit_from_jail("red", 0)
    result = engine.execute_move("red", 0)
    assert engine.current_color == "blue"


def test_pairs_keep_turn():
    engine = GameEngine(1, ["red", "blue"])
    engine.roll_dice()
    engine.dice = (3, 3)  # pair
    engine.board.exit_from_jail("red", 0)
    # Exiting from jail with pair
    engine.board.pieces["red"][0].state = "jail"
    engine.board.pieces["red"][0].position = -1
    result = engine.execute_move("red", 0)
    assert engine.current_color == "red"  # keeps turn


def test_wrong_turn_rejected():
    engine = GameEngine(1, ["red", "blue"])
    engine.roll_dice()
    result = engine.execute_move("blue", 0)
    assert "error" in result


def test_get_state():
    engine = GameEngine(1, ["red", "blue"])
    state = engine.get_state()
    assert state["game_id"] == 1
    assert "board" in state
    assert state["current_turn"] == "red"
```

- [ ] **Step 3: Run tests**

Run: `cd server && python -m pytest tests/test_engine.py -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add server/game/engine.py server/tests/test_engine.py
git commit -m "feat: game engine with rules, turns, dice, and pair logic"
```

---

## Task 5: Game Manager (Lobby, Game Lifecycle, Threads)

**Files:**
- Create: `server/game/manager.py`

- [ ] **Step 1: Create server/game/manager.py**

```python
import threading
from server.game.engine import GameEngine
from server.game.constants import MAX_PLAYERS, COLORS


class LobbyPlayer:
    def __init__(self, user_id: int, username: str, sid: str):
        self.user_id = user_id
        self.username = username
        self.sid = sid
        self.color = None


class GameManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.lobby: list[LobbyPlayer] = []
        self.active_game: GameEngine | None = None
        self.game_players: dict[str, LobbyPlayer] = {}  # color -> LobbyPlayer
        self.sid_to_color: dict[str, str] = {}  # sid -> color
        self.game_thread: threading.Thread | None = None
        self.game_in_progress = False

    def join_lobby(self, user_id: int, username: str, sid: str) -> dict:
        with self.lock:
            if self.game_in_progress:
                return {"error": "A game is already in progress"}
            if len(self.lobby) >= MAX_PLAYERS:
                return {"error": "Lobby is full"}
            if any(p.user_id == user_id for p in self.lobby):
                return {"error": "Already in lobby"}

            player = LobbyPlayer(user_id, username, sid)
            self.lobby.append(player)

            return {
                "players": [
                    {"username": p.username, "color": p.color}
                    for p in self.lobby
                ],
                "available_colors": self._available_colors(),
                "is_host": len(self.lobby) == 1,
            }

    def leave_lobby(self, sid: str) -> None:
        with self.lock:
            self.lobby = [p for p in self.lobby if p.sid != sid]

    def select_color(self, sid: str, color: str) -> dict:
        with self.lock:
            if color not in COLORS:
                return {"error": "Invalid color"}
            if any(p.color == color and p.sid != sid for p in self.lobby):
                return {"error": "Color already taken"}

            for player in self.lobby:
                if player.sid == sid:
                    player.color = color
                    break

            return {
                "players": [
                    {"username": p.username, "color": p.color}
                    for p in self.lobby
                ],
                "available_colors": self._available_colors(),
            }

    def _available_colors(self) -> list[str]:
        taken = {p.color for p in self.lobby if p.color}
        return [c for c in COLORS if c not in taken]

    def can_start(self) -> bool:
        with self.lock:
            return (
                2 <= len(self.lobby) <= MAX_PLAYERS
                and all(p.color is not None for p in self.lobby)
                and not self.game_in_progress
            )

    def start_game(self, db_game_id: int) -> GameEngine:
        with self.lock:
            colors = [p.color for p in self.lobby]
            self.active_game = GameEngine(db_game_id, colors)
            self.game_in_progress = True

            for player in self.lobby:
                self.game_players[player.color] = player
                self.sid_to_color[player.sid] = player.color

            return self.active_game

    def end_game(self) -> None:
        with self.lock:
            self.active_game = None
            self.game_players.clear()
            self.sid_to_color.clear()
            self.game_in_progress = False
            self.lobby.clear()

    def get_color_by_sid(self, sid: str) -> str | None:
        return self.sid_to_color.get(sid)

    def get_player_by_sid(self, sid: str) -> LobbyPlayer | None:
        for player in self.lobby:
            if player.sid == sid:
                return player
        return None

    def handle_disconnect(self, sid: str) -> str | None:
        color = self.sid_to_color.get(sid)
        if color and self.active_game:
            self.active_game.disconnected.add(color)
        return color

    def handle_reconnect(self, sid: str, user_id: int) -> str | None:
        with self.lock:
            for color, player in self.game_players.items():
                if player.user_id == user_id:
                    old_sid = player.sid
                    player.sid = sid
                    del self.sid_to_color[old_sid]
                    self.sid_to_color[sid] = color
                    if self.active_game:
                        self.active_game.disconnected.discard(color)
                    return color
        return None


# Singleton
game_manager = GameManager()
```

- [ ] **Step 2: Commit**

```bash
git add server/game/manager.py
git commit -m "feat: game manager with lobby, lifecycle, and reconnection"
```

---

## Task 6: Socket.IO Events (Lobby + Game)

**Files:**
- Create: `server/sockets/__init__.py`, `server/sockets/lobby.py`, `server/sockets/game_events.py`
- Modify: `server/app.py` (import socket handlers)

- [ ] **Step 1: Create server/sockets/__init__.py**

```python
```

- [ ] **Step 2: Create server/sockets/lobby.py**

```python
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

    result = game_manager.join_lobby(
        payload["user_id"], payload["username"], request.sid
    )
    if "error" in result:
        emit("error", {"message": result["error"]})
        return

    join_room("lobby")
    socketio.emit("lobby_update", result, room="lobby")


@socketio.on("leave_lobby")
def handle_leave_lobby():
    game_manager.leave_lobby(request.sid)
    leave_room("lobby")
    # Broadcast updated lobby
    players = [
        {"username": p.username, "color": p.color}
        for p in game_manager.lobby
    ]
    available = game_manager._available_colors()
    socketio.emit(
        "lobby_update",
        {"players": players, "available_colors": available},
        room="lobby",
    )


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

    # Create DB record
    game_record = Game(status="playing")
    db.session.add(game_record)
    db.session.commit()

    for player in game_manager.lobby:
        gp = GamePlayer(
            game_id=game_record.id,
            user_id=player.user_id,
            color=player.color,
        )
        db.session.add(gp)
    db.session.commit()

    engine = game_manager.start_game(game_record.id)

    # Move all players from lobby room to game room
    for color, player in game_manager.game_players.items():
        leave_room("lobby", sid=player.sid)
        join_room(f"game_{game_record.id}", sid=player.sid)

    socketio.emit(
        "game_start",
        engine.get_state(),
        room=f"game_{game_record.id}",
    )
```

- [ ] **Step 3: Create server/sockets/game_events.py**

```python
from flask_socketio import emit
from flask import request
from server.extensions import socketio, db
from server.game.manager import game_manager
from server.models.move import GameMove
from server.models.game import Game, GamePlayer
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

    socketio.emit(
        "dice_result",
        {
            "dice_1": d1,
            "dice_2": d2,
            "is_pair": d1 == d2,
            "player": color,
            "movable": engine.get_movable_pieces(color),
            "jailed": engine.get_jailed_pieces(color),
            "can_exit_jail": d1 == d2,
        },
        room=room,
    )


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

    # Save move to DB
    player = game_manager.game_players[color]
    move = GameMove(
        game_id=engine.game_id,
        user_id=player.user_id,
        move_number=engine.move_count,
        dice_1=engine.dice[0],
        dice_2=engine.dice[1],
        piece_index=piece_index,
        from_position=from_pos if from_state == "board" else -1,
        to_position=piece.position if piece.state == "board" else -1,
        action=result["action"],
    )
    db.session.add(move)
    db.session.commit()

    # Broadcast updated board
    socketio.emit("board_update", engine.get_state(), room=room)

    # Handle triple pairs
    if result.get("triple_pairs"):
        socketio.emit(
            "triple_pairs",
            {"player": color, "message": "Choose a piece to finish!"},
            room=room,
        )

    # Handle game over
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

    # Update DB
    game = Game.query.get(engine.game_id)
    game.status = "finished"
    game.winner_id = player.user_id
    game.finished_at = datetime.now(timezone.utc)
    db.session.commit()

    socketio.emit(
        "game_over",
        {"winner": winner_color, "winner_name": player.username},
        room=room,
    )

    game_manager.end_game()


@socketio.on("disconnect")
def handle_disconnect():
    color = game_manager.handle_disconnect(request.sid)
    if color and game_manager.active_game:
        room = f"game_{game_manager.active_game.game_id}"
        socketio.emit(
            "player_disconnected",
            {"color": color},
            room=room,
        )
```

- [ ] **Step 4: Register socket handlers in server/app.py**

Add inside `create_app()`, after blueprint registration:

```python
    import server.sockets.lobby  # noqa: F401
    import server.sockets.game_events  # noqa: F401
```

- [ ] **Step 5: Commit**

```bash
git add server/sockets/ server/app.py
git commit -m "feat: Socket.IO events for lobby and game play"
```

---

## Task 7: Berkeley Clock Synchronization

**Files:**
- Create: `server/services/berkeley.py`, `server/sockets/sync.py`

- [ ] **Step 1: Create server/services/berkeley.py**

```python
import time
import threading
from server.extensions import socketio


class BerkeleySynchronizer:
    def __init__(self, game_room: str):
        self.game_room = game_room
        self.responses: dict[str, float] = {}
        self.lock = threading.Lock()
        self.waiting = threading.Event()

    def request_sync(self, player_sids: list[str]) -> None:
        self.responses.clear()
        server_time = time.time() * 1000  # ms

        socketio.emit("sync_request", {"server_time": server_time}, room=self.game_room)

        # Wait up to 5 seconds for all responses
        self.waiting.clear()
        deadline = time.time() + 5
        while len(self.responses) < len(player_sids) and time.time() < deadline:
            self.waiting.wait(timeout=0.5)

        if not self.responses:
            return

        # Calculate average difference
        diffs = []
        for sid, client_time in self.responses.items():
            diff = client_time - server_time
            diffs.append(diff)

        avg_diff = sum(diffs) / len(diffs)

        # Send adjustment to each client
        for sid, client_time in self.responses.items():
            adjustment = avg_diff - (client_time - server_time)
            socketio.emit(
                "sync_adjust",
                {"offset_ms": round(adjustment, 2)},
                to=sid,
            )

    def receive_response(self, sid: str, client_time: float) -> None:
        with self.lock:
            self.responses[sid] = client_time
            if len(self.responses) >= 2:
                self.waiting.set()
```

- [ ] **Step 2: Create server/sockets/sync.py**

```python
from flask import request
from server.extensions import socketio

# Will be initialized per game
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
```

- [ ] **Step 3: Add import in server/app.py**

```python
    import server.sockets.sync  # noqa: F401
```

- [ ] **Step 4: Commit**

```bash
git add server/services/berkeley.py server/sockets/sync.py server/app.py
git commit -m "feat: Berkeley clock synchronization algorithm"
```

---

## Task 8: Statistics Service & Routes

**Files:**
- Create: `server/services/stats.py`, `server/routes/stats.py`
- Modify: `server/app.py` (register blueprint)

- [ ] **Step 1: Create server/services/stats.py**

```python
from server.extensions import db
from server.models.user import User
from server.models.game import Game, GamePlayer
from sqlalchemy import func


def get_ranking(limit: int = 20) -> list[dict]:
    results = (
        db.session.query(
            User.username,
            func.count(Game.id).label("wins"),
        )
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
```

- [ ] **Step 2: Create server/routes/stats.py**

```python
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
```

- [ ] **Step 3: Register blueprint in server/app.py**

```python
    from server.routes.stats import stats_bp
    app.register_blueprint(stats_bp)
```

- [ ] **Step 4: Commit**

```bash
git add server/services/stats.py server/routes/stats.py server/app.py
git commit -m "feat: statistics service with ranking and win probability"
```

---

## Task 9: Recommendation Service (Heuristics + LLM)

**Files:**
- Create: `server/services/recommendation.py`

- [ ] **Step 1: Create server/services/recommendation.py**

```python
import os
from server.game.engine import GameEngine
from server.game.constants import SAFE_POSITIONS, HOME_ENTRY


def score_moves(engine: GameEngine, color: str) -> list[dict]:
    total = engine.dice_total()
    scored = []

    for piece in engine.board.pieces[color]:
        if piece.state == "finished":
            continue

        score = 0
        reasons = []

        if piece.state == "jail":
            if engine.is_pair():
                score += 25
                reasons.append("Sacar ficha de la carcel")
            else:
                continue

        elif piece.state in ("board", "home_stretch"):
            # Simulate move
            original = (piece.state, piece.position, piece.home_position)
            result = engine.board.move_piece(color, piece.index, total)
            new_pos = piece.position
            new_state = piece.state
            # Revert
            piece.state, piece.position, piece.home_position = original

            if result["action"] == "invalid":
                continue

            if result["action"] == "eat":
                score += 50
                reasons.append("Comer ficha rival")

            if result["action"] == "finish":
                score += 60
                reasons.append("Llevar ficha a la meta")

            if result["action"] == "enter":
                score += 40
                reasons.append("Entrar a la recta final")

            if new_state == "board" and new_pos in SAFE_POSITIONS:
                score += 30
                reasons.append("Llegar a casilla segura")

            # Check if piece is in danger (rival within 6 cells behind)
            if piece.state == "board":
                for rival_color, rival_pieces in engine.board.pieces.items():
                    if rival_color == color:
                        continue
                    for rp in rival_pieces:
                        if rp.state == "board":
                            dist = (piece.position - rp.position) % 68
                            if 1 <= dist <= 12:
                                score += 20
                                reasons.append("Mover ficha en riesgo")
                                break

            if score == 0:
                score += 15
                reasons.append("Avanzar ficha")

        scored.append({
            "piece_index": piece.index,
            "score": score,
            "reasons": reasons,
            "state": piece.state,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


def get_fallback_explanation(best_move: dict) -> str:
    reasons = best_move.get("reasons", [])
    piece = best_move.get("piece_index", 0)
    if not reasons:
        return f"Te recomiendo mover la ficha {piece + 1}."
    main_reason = reasons[0]
    return f"Te recomiendo mover la ficha {piece + 1}: {main_reason.lower()}."


def get_llm_explanation(engine: GameEngine, color: str, best_move: dict) -> str:
    api_key = os.getenv("CLAUDE_API_KEY", "")
    if not api_key:
        return get_fallback_explanation(best_move)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        board_state = engine.get_state()
        prompt = f"""Eres un asistente de juego de Parques colombiano. Analiza el estado del tablero y recomienda la mejor jugada.

Estado actual:
- Jugador: {color}
- Dados: {engine.dice[0]} y {engine.dice[1]} (total: {engine.dice_total()})
- Tablero: {board_state['board']}
- Jugada recomendada: mover ficha {best_move['piece_index'] + 1}
- Razones del analisis: {', '.join(best_move['reasons'])}
- Puntaje: {best_move['score']}

Explica en 1-2 oraciones por que esta es la mejor jugada. Se conciso y usa lenguaje casual."""

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    except Exception:
        return get_fallback_explanation(best_move)


def get_recommendation(engine: GameEngine, color: str) -> dict:
    scored = score_moves(engine, color)
    if not scored:
        return {"recommendation": None, "explanation": "No hay jugadas disponibles."}

    best = scored[0]
    explanation = get_fallback_explanation(best)

    return {
        "recommendation": {
            "piece_index": best["piece_index"],
            "score": best["score"],
            "reasons": best["reasons"],
        },
        "explanation": explanation,
        "all_moves": scored,
    }
```

- [ ] **Step 2: Wire recommendation into game_events.py**

Add to `server/sockets/game_events.py`:

```python
from server.services.recommendation import get_recommendation

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
```

- [ ] **Step 3: Commit**

```bash
git add server/services/recommendation.py server/sockets/game_events.py
git commit -m "feat: hybrid recommendation engine with heuristics and LLM fallback"
```

---

## Task 10: Quasar Client Scaffolding

**Files:**
- Create: Quasar project in `client/`

- [ ] **Step 1: Create Quasar project**

Run:
```bash
cd "/home/cris/Documents/sistemas-distribuidos/Proyecto Final"
npm init quasar@latest client -- --template app-vite --typescript no --quasar-version 2 --script-type composition --css-preprocessor scss
```

Follow prompts: select Pinia, Vue Router.

- [ ] **Step 2: Install dependencies**

Run:
```bash
cd client
npm install socket.io-client axios pinia-plugin-persistedstate
```

- [ ] **Step 3: Configure quasar.config.js for Capacitor**

In `client/quasar.config.js`, ensure capacitor section is present (Quasar scaffolds it by default). Verify:
```javascript
capacitor: {
  hideSplashscreen: true
}
```

- [ ] **Step 4: Commit**

```bash
git add client/
git commit -m "feat: scaffold Quasar client with Vue 3, Pinia, Socket.IO"
```

---

## Task 11: Client Auth (Login + Register Pages)

**Files:**
- Create: `client/src/composables/useAuth.js`, `client/src/stores/userStore.js`, `client/src/pages/LoginPage.vue`
- Modify: `client/src/router/routes.js`

- [ ] **Step 1: Create client/src/stores/userStore.js**

```javascript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const username = ref(localStorage.getItem('username') || '')

  const isLoggedIn = computed(() => !!token.value)

  function setAuth(newToken, newUsername) {
    token.value = newToken
    username.value = newUsername
    localStorage.setItem('token', newToken)
    localStorage.setItem('username', newUsername)
  }

  function logout() {
    token.value = ''
    username.value = ''
    localStorage.removeItem('token')
    localStorage.removeItem('username')
  }

  return { token, username, isLoggedIn, setAuth, logout }
})
```

- [ ] **Step 2: Create client/src/composables/useAuth.js**

```javascript
import axios from 'axios'
import { useUserStore } from 'src/stores/userStore'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

export function useAuth() {
  const userStore = useUserStore()

  async function login(username, password) {
    const { data } = await axios.post(`${API_URL}/login`, { username, password })
    userStore.setAuth(data.token, data.username)
    return data
  }

  async function register(username, password) {
    const { data } = await axios.post(`${API_URL}/register`, { username, password })
    return data
  }

  function logout() {
    userStore.logout()
  }

  return { login, register, logout }
}
```

- [ ] **Step 3: Create client/src/pages/LoginPage.vue**

```vue
<template>
  <q-page class="flex flex-center">
    <q-card style="min-width: 350px">
      <q-card-section>
        <div class="text-h5 text-center">Parques Distribuido</div>
      </q-card-section>

      <q-card-section>
        <q-form @submit="onSubmit">
          <q-input
            v-model="username"
            label="Usuario"
            outlined
            class="q-mb-md"
            :rules="[val => val.length >= 3 || 'Minimo 3 caracteres']"
          />
          <q-input
            v-model="password"
            label="Contrasena"
            type="password"
            outlined
            class="q-mb-md"
            :rules="[val => val.length >= 4 || 'Minimo 4 caracteres']"
          />
          <q-btn
            :label="isLogin ? 'Ingresar' : 'Registrarse'"
            type="submit"
            color="primary"
            class="full-width q-mb-sm"
            :loading="loading"
          />
          <q-btn
            :label="isLogin ? 'Crear cuenta' : 'Ya tengo cuenta'"
            flat
            class="full-width"
            @click="isLogin = !isLogin"
          />
        </q-form>
      </q-card-section>

      <q-card-section v-if="error">
        <q-banner class="bg-negative text-white">{{ error }}</q-banner>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from 'src/composables/useAuth'

const router = useRouter()
const { login, register } = useAuth()

const username = ref('')
const password = ref('')
const isLogin = ref(true)
const loading = ref(false)
const error = ref('')

async function onSubmit() {
  loading.value = true
  error.value = ''
  try {
    if (isLogin.value) {
      await login(username.value, password.value)
    } else {
      await register(username.value, password.value)
      await login(username.value, password.value)
    }
    router.push('/lobby')
  } catch (e) {
    error.value = e.response?.data?.error || 'Error de conexion'
  } finally {
    loading.value = false
  }
}
</script>
```

- [ ] **Step 4: Update router**

Replace `client/src/router/routes.js`:

```javascript
const routes = [
  {
    path: '/',
    redirect: '/login',
  },
  {
    path: '/login',
    component: () => import('pages/LoginPage.vue'),
  },
  {
    path: '/lobby',
    component: () => import('pages/LobbyPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/game',
    component: () => import('pages/GamePage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/stats',
    component: () => import('pages/StatsPage.vue'),
    meta: { requiresAuth: true },
  },
]

export default routes
```

- [ ] **Step 5: Commit**

```bash
git add client/src/
git commit -m "feat: client auth with login/register pages and JWT storage"
```

---

## Task 12: Client Socket.IO Connection & Game Store

**Files:**
- Create: `client/src/composables/useSocket.js`, `client/src/stores/gameStore.js`

- [ ] **Step 1: Create client/src/composables/useSocket.js**

```javascript
import { ref } from 'vue'
import { io } from 'socket.io-client'
import { useUserStore } from 'src/stores/userStore'

const SOCKET_URL = import.meta.env.VITE_SOCKET_URL || 'http://localhost:5000'

let socket = null
const connected = ref(false)

export function useSocket() {
  const userStore = useUserStore()

  function connect() {
    if (socket?.connected) return socket

    socket = io(SOCKET_URL, {
      transports: ['websocket'],
      auth: { token: userStore.token },
    })

    socket.on('connect', () => {
      connected.value = true
    })

    socket.on('disconnect', () => {
      connected.value = false
    })

    return socket
  }

  function disconnect() {
    if (socket) {
      socket.disconnect()
      socket = null
      connected.value = false
    }
  }

  function getSocket() {
    return socket
  }

  return { connect, disconnect, getSocket, connected }
}
```

- [ ] **Step 2: Create client/src/stores/gameStore.js**

```javascript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useGameStore = defineStore('game', () => {
  const gameId = ref(null)
  const board = ref({})
  const currentTurn = ref('')
  const phase = ref('')
  const dice = ref([0, 0])
  const winner = ref(null)
  const players = ref([])
  const myColor = ref('')
  const recommendation = ref(null)
  const clockOffset = ref(0)

  const isMyTurn = computed(() => currentTurn.value === myColor.value)

  function updateFromState(state) {
    gameId.value = state.game_id
    board.value = state.board
    currentTurn.value = state.current_turn
    phase.value = state.phase
    dice.value = state.dice
    winner.value = state.winner
  }

  function setPlayers(p) {
    players.value = p
  }

  function setMyColor(color) {
    myColor.value = color
  }

  function setRecommendation(rec) {
    recommendation.value = rec
  }

  function setClockOffset(offset) {
    clockOffset.value = offset
  }

  function reset() {
    gameId.value = null
    board.value = {}
    currentTurn.value = ''
    phase.value = ''
    dice.value = [0, 0]
    winner.value = null
    players.value = []
    myColor.value = ''
    recommendation.value = null
    clockOffset.value = 0
  }

  return {
    gameId, board, currentTurn, phase, dice, winner,
    players, myColor, recommendation, clockOffset,
    isMyTurn, updateFromState, setPlayers, setMyColor,
    setRecommendation, setClockOffset, reset,
  }
})
```

- [ ] **Step 3: Commit**

```bash
git add client/src/composables/useSocket.js client/src/stores/gameStore.js
git commit -m "feat: Socket.IO connection composable and game state store"
```

---

## Task 13: Lobby Page

**Files:**
- Create: `client/src/pages/LobbyPage.vue`

- [ ] **Step 1: Create client/src/pages/LobbyPage.vue**

```vue
<template>
  <q-page class="q-pa-md">
    <div class="text-h4 text-center q-mb-lg">Sala de Espera</div>

    <div class="row justify-center q-gutter-md">
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">Jugadores ({{ lobbyPlayers.length }}/4)</div>
        </q-card-section>

        <q-list separator>
          <q-item v-for="player in lobbyPlayers" :key="player.username">
            <q-item-section avatar>
              <q-avatar :color="player.color || 'grey'" text-color="white">
                {{ player.username[0].toUpperCase() }}
              </q-avatar>
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ player.username }}</q-item-label>
              <q-item-label caption>{{ player.color || 'Sin color' }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>

        <q-card-section>
          <div class="text-subtitle2 q-mb-sm">Elige tu color:</div>
          <div class="row q-gutter-sm">
            <q-btn
              v-for="color in availableColors"
              :key="color"
              :color="color === 'yellow' ? 'amber' : color"
              :label="color"
              @click="selectColor(color)"
              :outline="myColor !== color"
            />
          </div>
        </q-card-section>

        <q-card-actions align="center">
          <q-btn
            v-if="isHost"
            label="Iniciar Partida"
            color="positive"
            size="lg"
            :disable="!canStart"
            @click="startGame"
          />
          <div v-else class="text-caption">Esperando a que el host inicie...</div>
        </q-card-actions>
      </q-card>
    </div>
  </q-page>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSocket } from 'src/composables/useSocket'
import { useUserStore } from 'src/stores/userStore'
import { useGameStore } from 'src/stores/gameStore'

const router = useRouter()
const userStore = useUserStore()
const gameStore = useGameStore()
const { connect, getSocket } = useSocket()

const lobbyPlayers = ref([])
const availableColors = ref([])
const isHost = ref(false)
const canStart = ref(false)
const myColor = ref('')

onMounted(() => {
  const socket = connect()

  socket.emit('join_lobby', { token: userStore.token })

  socket.on('lobby_update', (data) => {
    lobbyPlayers.value = data.players
    availableColors.value = data.available_colors
    if (data.is_host !== undefined) isHost.value = data.is_host
    canStart.value = lobbyPlayers.value.length >= 2
      && lobbyPlayers.value.every(p => p.color)
  })

  socket.on('game_start', (state) => {
    gameStore.updateFromState(state)
    gameStore.setMyColor(myColor.value)
    gameStore.setPlayers(lobbyPlayers.value)
    router.push('/game')
  })

  socket.on('error', (data) => {
    console.error('Socket error:', data.message)
  })
})

function selectColor(color) {
  myColor.value = color
  getSocket().emit('select_color', { color })
}

function startGame() {
  getSocket().emit('start_game')
}

onUnmounted(() => {
  const socket = getSocket()
  if (socket) socket.emit('leave_lobby')
})
</script>
```

- [ ] **Step 2: Commit**

```bash
git add client/src/pages/LobbyPage.vue
git commit -m "feat: lobby page with color selection and game start"
```

---

## Task 14: Game Board Component (Canvas/SVG)

**Files:**
- Create: `client/src/components/BoardCanvas.vue`

- [ ] **Step 1: Create client/src/components/BoardCanvas.vue**

This is the most complex UI component. It renders the Parqués board as SVG with:
- 68 main circuit cells in a cross pattern
- 4 home stretches (colored corridors)
- 4 jail areas (corners)
- Clickable pieces for the active player

```vue
<template>
  <div class="board-container">
    <svg :viewBox="`0 0 ${SIZE} ${SIZE}`" class="board-svg">
      <!-- Board background -->
      <rect :width="SIZE" :height="SIZE" fill="#f5e6c8" rx="8" />

      <!-- Corner jails -->
      <rect v-for="(jail, i) in jails" :key="'jail-'+i"
        :x="jail.x" :y="jail.y" :width="CORNER" :height="CORNER"
        :fill="jail.color" opacity="0.3" rx="4" />
      <text v-for="(jail, i) in jails" :key="'jail-text-'+i"
        :x="jail.x + CORNER/2" :y="jail.y + CORNER/2"
        text-anchor="middle" dominant-baseline="middle"
        font-size="12" fill="#333">CARCEL</text>

      <!-- Main circuit cells -->
      <g v-for="(cell, idx) in mainCells" :key="'cell-'+idx">
        <rect
          :x="cell.x" :y="cell.y" :width="CELL" :height="CELL"
          :fill="getCellColor(idx)"
          stroke="#999" stroke-width="0.5" rx="2"
        />
        <text :x="cell.x+CELL/2" :y="cell.y+CELL/2"
          text-anchor="middle" dominant-baseline="middle"
          font-size="6" fill="#666">{{ idx }}</text>
      </g>

      <!-- Home stretch cells -->
      <g v-for="(stretch, color) in homeStretches" :key="'hs-'+color">
        <rect v-for="(cell, i) in stretch" :key="'hs-cell-'+color+'-'+i"
          :x="cell.x" :y="cell.y" :width="CELL" :height="CELL"
          :fill="getPlayerColor(color)" opacity="0.5"
          stroke="#999" stroke-width="0.5" rx="2"
        />
      </g>

      <!-- Center circle -->
      <circle :cx="SIZE/2" :cy="SIZE/2" :r="CELL*2"
        fill="#87CEEB" stroke="#666" stroke-width="1" />
      <text :x="SIZE/2" :y="SIZE/2"
        text-anchor="middle" dominant-baseline="middle"
        font-size="10" fill="#333">META</text>

      <!-- Pieces on board -->
      <g v-for="(pieces, color) in board" :key="'pieces-'+color">
        <circle v-for="piece in pieces.filter(p => p.state === 'board')"
          :key="'p-'+color+'-'+piece.index"
          :cx="getPieceX(piece)" :cy="getPieceY(piece)"
          :r="CELL/3"
          :fill="getPlayerColor(color)"
          stroke="#333" stroke-width="1"
          :class="{ clickable: isClickable(piece, color) }"
          @click="onPieceClick(piece, color)"
        />
      </g>

      <!-- Pieces in jail -->
      <g v-for="(pieces, color) in board" :key="'jail-pieces-'+color">
        <circle v-for="(piece, pi) in pieces.filter(p => p.state === 'jail')"
          :key="'jp-'+color+'-'+piece.index"
          :cx="getJailPieceX(color, pi)"
          :cy="getJailPieceY(color, pi)"
          :r="CELL/3"
          :fill="getPlayerColor(color)"
          stroke="#333" stroke-width="1"
          :class="{ clickable: isClickable(piece, color) }"
          @click="onPieceClick(piece, color)"
        />
      </g>

      <!-- Pieces in home stretch -->
      <g v-for="(pieces, color) in board" :key="'hs-pieces-'+color">
        <circle v-for="piece in pieces.filter(p => p.state === 'home_stretch')"
          :key="'hp-'+color+'-'+piece.index"
          :cx="getHomePieceX(color, piece.home_position)"
          :cy="getHomePieceY(color, piece.home_position)"
          :r="CELL/3"
          :fill="getPlayerColor(color)"
          stroke="#333" stroke-width="1"
          :class="{ clickable: isClickable(piece, color) }"
          @click="onPieceClick(piece, color)"
        />
      </g>
    </svg>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useGameStore } from 'src/stores/gameStore'

const emit = defineEmits(['piece-click'])
const gameStore = useGameStore()

const SIZE = 500
const CELL = 28
const CORNER = 140
const MARGIN = 10

const board = computed(() => gameStore.board)

const SAFE_POSITIONS = new Set([0, 5, 12, 17, 22, 29, 34, 39, 46, 51, 56, 63])
const EXIT_POSITIONS = new Set([0, 17, 34, 51])

const COLOR_MAP = {
  red: '#e74c3c',
  blue: '#3498db',
  green: '#27ae60',
  yellow: '#f1c40f',
}

const jails = [
  { x: MARGIN, y: MARGIN, color: COLOR_MAP.red },
  { x: SIZE - CORNER - MARGIN, y: MARGIN, color: COLOR_MAP.green },
  { x: MARGIN, y: SIZE - CORNER - MARGIN, color: COLOR_MAP.yellow },
  { x: SIZE - CORNER - MARGIN, y: SIZE - CORNER - MARGIN, color: COLOR_MAP.blue },
]

// Generate main circuit cell positions (simplified cross layout)
// This is a simplified representation - the actual layout follows
// the traditional Parques cross pattern
const mainCells = computed(() => {
  const cells = []
  const mid = SIZE / 2
  const startOffset = CORNER + MARGIN + 5

  // Build the cross-shaped path of 68 cells
  // Top arm (going down): cells on the top section
  for (let i = 0; i < 8; i++) {
    cells.push({ x: mid - CELL / 2 - CELL, y: startOffset + i * CELL })
    if (cells.length <= 7) {
      cells.push({ x: mid - CELL / 2 + CELL, y: startOffset + (7 - i) * CELL })
    }
  }

  // Fill remaining cells around the board
  // Right arm
  for (let i = 0; i < 8; i++) {
    cells.push({ x: mid + CELL * 2 + i * CELL, y: mid - CELL / 2 - CELL })
  }

  // Bottom arm
  for (let i = 0; i < 8; i++) {
    cells.push({ x: mid + CELL / 2, y: mid + CELL * 2 + i * CELL })
  }

  // Left arm
  for (let i = 0; i < 8; i++) {
    cells.push({ x: startOffset + (7 - i) * CELL, y: mid + CELL / 2 })
  }

  // Pad to 68 if needed (simplified)
  while (cells.length < 68) {
    const angle = (cells.length / 68) * Math.PI * 2
    cells.push({
      x: mid + Math.cos(angle) * (mid - CORNER),
      y: mid + Math.sin(angle) * (mid - CORNER),
    })
  }

  return cells.slice(0, 68)
})

const homeStretches = computed(() => {
  const mid = SIZE / 2
  const stretches = {}
  const colors = ['red', 'blue', 'green', 'yellow']
  const directions = [
    { dx: 0, dy: CELL }, // red: top to center
    { dx: 0, dy: -CELL }, // blue: bottom to center
    { dx: CELL, dy: 0 }, // green: right to center
    { dx: -CELL, dy: 0 }, // yellow: left to center
  ]
  const starts = [
    { x: mid - CELL / 2, y: CORNER + MARGIN + 10 },
    { x: mid - CELL / 2, y: SIZE - CORNER - MARGIN - 10 - CELL },
    { x: CORNER + MARGIN + 10, y: mid - CELL / 2 },
    { x: SIZE - CORNER - MARGIN - 10 - CELL, y: mid - CELL / 2 },
  ]

  colors.forEach((color, ci) => {
    stretches[color] = []
    for (let i = 0; i < 8; i++) {
      stretches[color].push({
        x: starts[ci].x + directions[ci].dx * i,
        y: starts[ci].y + directions[ci].dy * i,
      })
    }
  })
  return stretches
})

function getCellColor(idx) {
  if (EXIT_POSITIONS.has(idx)) return '#ffeb3b'
  if (SAFE_POSITIONS.has(idx)) return '#c8e6c9'
  return '#fff'
}

function getPlayerColor(color) {
  return COLOR_MAP[color] || '#999'
}

function getPieceX(piece) {
  const cell = mainCells.value[piece.position]
  return cell ? cell.x + CELL / 2 : 0
}

function getPieceY(piece) {
  const cell = mainCells.value[piece.position]
  return cell ? cell.y + CELL / 2 : 0
}

function getJailPieceX(color, index) {
  const jail = jails[['red', 'green', 'yellow', 'blue'].indexOf(color)]
  return jail.x + CORNER / 3 + (index % 2) * (CORNER / 3)
}

function getJailPieceY(color, index) {
  const jail = jails[['red', 'green', 'yellow', 'blue'].indexOf(color)]
  return jail.y + CORNER / 3 + Math.floor(index / 2) * (CORNER / 3)
}

function getHomePieceX(color, homePos) {
  const stretch = homeStretches.value[color]
  return stretch && stretch[homePos] ? stretch[homePos].x + CELL / 2 : 0
}

function getHomePieceY(color, homePos) {
  const stretch = homeStretches.value[color]
  return stretch && stretch[homePos] ? stretch[homePos].y + CELL / 2 : 0
}

function isClickable(piece, color) {
  return gameStore.isMyTurn && color === gameStore.myColor && gameStore.phase === 'moving'
}

function onPieceClick(piece, color) {
  if (isClickable(piece, color)) {
    emit('piece-click', { piece_index: piece.index })
  }
}
</script>

<style scoped>
.board-container {
  display: flex;
  justify-content: center;
  align-items: center;
}
.board-svg {
  width: 100%;
  max-width: 500px;
  height: auto;
}
.clickable {
  cursor: pointer;
  filter: drop-shadow(0 0 4px rgba(255, 255, 0, 0.8));
}
.clickable:hover {
  filter: drop-shadow(0 0 8px rgba(255, 255, 0, 1));
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add client/src/components/BoardCanvas.vue
git commit -m "feat: SVG board component with pieces, jails, and home stretches"
```

---

## Task 15: Game Page (Board + Dice + Controls)

**Files:**
- Create: `client/src/components/DiceRoller.vue`, `client/src/components/PlayerInfo.vue`, `client/src/components/RecommendationPanel.vue`, `client/src/pages/GamePage.vue`
- Create: `client/src/composables/useGame.js`

- [ ] **Step 1: Create client/src/components/DiceRoller.vue**

```vue
<template>
  <div class="dice-container row q-gutter-md justify-center items-center">
    <div class="dice" :class="{ rolling }">{{ dice[0] || '?' }}</div>
    <div class="dice" :class="{ rolling }">{{ dice[1] || '?' }}</div>
    <q-btn
      v-if="canRoll"
      label="Lanzar Dados"
      color="primary"
      @click="$emit('roll')"
      :loading="rolling"
    />
    <q-chip v-if="isPair" color="amber" text-color="black">PARES!</q-chip>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  dice: { type: Array, default: () => [0, 0] },
  canRoll: Boolean,
  rolling: Boolean,
})
defineEmits(['roll'])

const isPair = computed(() => props.dice[0] > 0 && props.dice[0] === props.dice[1])
</script>

<style scoped>
.dice {
  width: 60px; height: 60px;
  background: white; border: 2px solid #333; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 28px; font-weight: bold;
}
.rolling { animation: shake 0.3s ease-in-out 3; }
@keyframes shake {
  0%, 100% { transform: rotate(0deg); }
  25% { transform: rotate(-10deg); }
  75% { transform: rotate(10deg); }
}
</style>
```

- [ ] **Step 2: Create client/src/components/PlayerInfo.vue**

```vue
<template>
  <q-list bordered separator>
    <q-item v-for="player in players" :key="player.username"
      :class="{ 'bg-blue-1': player.color === currentTurn }">
      <q-item-section avatar>
        <q-avatar :style="{ background: colorMap[player.color] }" text-color="white">
          {{ player.username[0].toUpperCase() }}
        </q-avatar>
      </q-item-section>
      <q-item-section>
        <q-item-label>{{ player.username }}</q-item-label>
        <q-item-label caption>{{ player.color }}</q-item-label>
      </q-item-section>
      <q-item-section side>
        <q-icon v-if="player.color === currentTurn" name="arrow_forward" color="primary" />
      </q-item-section>
    </q-item>
  </q-list>
</template>

<script setup>
defineProps({
  players: Array,
  currentTurn: String,
})

const colorMap = {
  red: '#e74c3c', blue: '#3498db', green: '#27ae60', yellow: '#f1c40f',
}
</script>
```

- [ ] **Step 3: Create client/src/components/RecommendationPanel.vue**

```vue
<template>
  <q-card v-if="recommendation" bordered class="q-mt-md">
    <q-card-section>
      <div class="text-subtitle2">Recomendacion IA</div>
      <p>{{ recommendation.explanation }}</p>
      <q-chip v-if="recommendation.recommendation"
        color="primary" text-color="white">
        Ficha {{ recommendation.recommendation.piece_index + 1 }}
        (score: {{ recommendation.recommendation.score }})
      </q-chip>
    </q-card-section>
  </q-card>
</template>

<script setup>
defineProps({ recommendation: Object })
</script>
```

- [ ] **Step 4: Create client/src/composables/useGame.js**

```javascript
import { useSocket } from './useSocket'
import { useGameStore } from 'src/stores/gameStore'

export function useGame() {
  const { getSocket } = useSocket()
  const gameStore = useGameStore()

  function rollDice() {
    getSocket()?.emit('roll_dice')
  }

  function movePiece(pieceIndex) {
    getSocket()?.emit('move_piece', { piece_index: pieceIndex })
  }

  function passTurn() {
    getSocket()?.emit('pass_turn')
  }

  function requestRecommendation() {
    getSocket()?.emit('request_recommendation')
  }

  function finishPieceChoice(pieceIndex) {
    getSocket()?.emit('finish_piece_choice', { piece_index: pieceIndex })
  }

  function setupListeners() {
    const socket = getSocket()
    if (!socket) return

    socket.on('board_update', (state) => {
      gameStore.updateFromState(state)
    })

    socket.on('dice_result', (data) => {
      gameStore.dice = [data.dice_1, data.dice_2]
    })

    socket.on('recommendation', (data) => {
      gameStore.setRecommendation(data)
    })

    socket.on('game_over', (data) => {
      gameStore.winner = data.winner
    })

    socket.on('sync_request', (data) => {
      socket.emit('sync_response', {
        game_room: `game_${gameStore.gameId}`,
        client_time: Date.now(),
      })
    })

    socket.on('sync_adjust', (data) => {
      gameStore.setClockOffset(data.offset_ms)
    })
  }

  return { rollDice, movePiece, passTurn, requestRecommendation, finishPieceChoice, setupListeners }
}
```

- [ ] **Step 5: Create client/src/pages/GamePage.vue**

```vue
<template>
  <q-page class="q-pa-md">
    <div class="row q-gutter-md">
      <!-- Left: Player info -->
      <div class="col-3">
        <PlayerInfo :players="gameStore.players" :current-turn="gameStore.currentTurn" />
        <RecommendationPanel :recommendation="gameStore.recommendation" class="q-mt-md" />
        <q-btn
          v-if="gameStore.isMyTurn && gameStore.phase === 'moving'"
          label="Pedir Recomendacion"
          color="secondary"
          class="full-width q-mt-md"
          @click="requestRecommendation"
        />
      </div>

      <!-- Center: Board -->
      <div class="col">
        <BoardCanvas @piece-click="onPieceClick" />
      </div>

      <!-- Right: Dice + controls -->
      <div class="col-3">
        <DiceRoller
          :dice="gameStore.dice"
          :can-roll="gameStore.isMyTurn && gameStore.phase === 'rolling'"
          @roll="rollDice"
        />
        <q-btn
          v-if="gameStore.isMyTurn && gameStore.phase === 'moving'"
          label="Pasar Turno"
          color="grey"
          class="full-width q-mt-md"
          @click="passTurn"
        />
      </div>
    </div>

    <!-- Game Over Dialog -->
    <q-dialog :model-value="!!gameStore.winner" persistent>
      <q-card>
        <q-card-section class="text-center">
          <div class="text-h4">Fin del Juego!</div>
          <div class="text-h5 q-mt-md">
            Ganador: {{ gameStore.winner }}
          </div>
        </q-card-section>
        <q-card-actions align="center">
          <q-btn label="Volver al Lobby" color="primary" @click="backToLobby" />
          <q-btn label="Ver Estadisticas" color="secondary" @click="goToStats" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from 'src/stores/gameStore'
import { useGame } from 'src/composables/useGame'
import BoardCanvas from 'src/components/BoardCanvas.vue'
import DiceRoller from 'src/components/DiceRoller.vue'
import PlayerInfo from 'src/components/PlayerInfo.vue'
import RecommendationPanel from 'src/components/RecommendationPanel.vue'

const router = useRouter()
const gameStore = useGameStore()
const { rollDice, movePiece, passTurn, requestRecommendation, setupListeners } = useGame()

onMounted(() => {
  setupListeners()
})

function onPieceClick({ piece_index }) {
  movePiece(piece_index)
}

function backToLobby() {
  gameStore.reset()
  router.push('/lobby')
}

function goToStats() {
  router.push('/stats')
}
</script>
```

- [ ] **Step 6: Commit**

```bash
git add client/src/components/ client/src/composables/useGame.js client/src/pages/GamePage.vue
git commit -m "feat: game page with board, dice, player info, and recommendation panel"
```

---

## Task 16: Stats Page

**Files:**
- Create: `client/src/pages/StatsPage.vue`

- [ ] **Step 1: Create client/src/pages/StatsPage.vue**

```vue
<template>
  <q-page class="q-pa-md">
    <div class="text-h4 text-center q-mb-lg">Estadisticas</div>

    <div class="row q-gutter-md justify-center">
      <!-- My stats -->
      <q-card style="min-width: 350px">
        <q-card-section>
          <div class="text-h6">Mis Estadisticas</div>
        </q-card-section>
        <q-card-section v-if="myStats">
          <div class="row q-gutter-md">
            <q-chip color="primary" text-color="white">
              Partidas: {{ myStats.total_games }}
            </q-chip>
            <q-chip color="positive" text-color="white">
              Victorias: {{ myStats.wins }}
            </q-chip>
            <q-chip color="amber" text-color="black">
              Probabilidad: {{ (myStats.win_probability * 100).toFixed(1) }}%
            </q-chip>
          </div>

          <div class="text-subtitle2 q-mt-md">Ultimas partidas</div>
          <q-list separator>
            <q-item v-for="game in myStats.recent_games" :key="game.game_id">
              <q-item-section>
                <q-item-label>Partida #{{ game.game_id }}</q-item-label>
                <q-item-label caption>{{ game.date }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-badge :color="game.won ? 'positive' : 'negative'">
                  {{ game.won ? 'Victoria' : 'Derrota' }}
                </q-badge>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>
      </q-card>

      <!-- Ranking -->
      <q-card style="min-width: 350px">
        <q-card-section>
          <div class="text-h6">Ranking Global</div>
        </q-card-section>
        <q-card-section>
          <q-list separator>
            <q-item v-for="(player, i) in ranking" :key="player.username">
              <q-item-section avatar>
                <q-avatar color="primary" text-color="white">
                  {{ i + 1 }}
                </q-avatar>
              </q-item-section>
              <q-item-section>
                <q-item-label>{{ player.username }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-badge color="amber" text-color="black">
                  {{ player.wins }} victorias
                </q-badge>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>
      </q-card>

      <!-- Search player -->
      <q-card style="min-width: 350px">
        <q-card-section>
          <div class="text-h6">Buscar Jugador</div>
          <q-input v-model="searchUsername" label="Nombre de usuario" outlined
            @keyup.enter="searchPlayer" class="q-mt-sm">
            <template v-slot:append>
              <q-btn icon="search" flat @click="searchPlayer" />
            </template>
          </q-input>
        </q-card-section>
        <q-card-section v-if="searchResult">
          <div>Partidas: {{ searchResult.total_games }}</div>
          <div>Victorias: {{ searchResult.wins }}</div>
          <div>Probabilidad de ganar: {{ (searchResult.win_probability * 100).toFixed(1) }}%</div>
        </q-card-section>
      </q-card>
    </div>

    <div class="text-center q-mt-lg">
      <q-btn label="Volver al Lobby" color="primary" @click="$router.push('/lobby')" />
    </div>
  </q-page>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { useUserStore } from 'src/stores/userStore'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'
const userStore = useUserStore()

const myStats = ref(null)
const ranking = ref([])
const searchUsername = ref('')
const searchResult = ref(null)

onMounted(async () => {
  const [statsRes, rankingRes] = await Promise.all([
    axios.get(`${API_URL}/stats`, {
      headers: { Authorization: `Bearer ${userStore.token}` },
    }),
    axios.get(`${API_URL}/ranking`),
  ])
  myStats.value = statsRes.data
  ranking.value = rankingRes.data
})

async function searchPlayer() {
  if (!searchUsername.value) return
  try {
    const { data } = await axios.get(`${API_URL}/stats/${searchUsername.value}`)
    searchResult.value = data
  } catch {
    searchResult.value = null
  }
}
</script>
```

- [ ] **Step 2: Commit**

```bash
git add client/src/pages/StatsPage.vue
git commit -m "feat: stats page with ranking, player search, and match history"
```

---

## Task 17: Dockerfile & Render Deploy Config

**Files:**
- Create: `server/Dockerfile`, `render.yaml`

- [ ] **Step 1: Create server/Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "-m", "server.app"]
```

- [ ] **Step 2: Create render.yaml**

```yaml
services:
  - type: web
    name: parques-server
    runtime: python
    buildCommand: cd server && pip install -r requirements.txt
    startCommand: cd server && python -m server.app
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: parques-db
          property: connectionString
      - key: SECRET_KEY
        generateValue: true
      - key: JWT_SECRET
        generateValue: true
      - key: CLAUDE_API_KEY
        sync: false

  - type: web
    name: parques-client
    runtime: static
    buildCommand: cd client && npm install && npx quasar build
    staticPublishPath: client/dist/spa
    headers:
      - path: /*
        name: Cache-Control
        value: no-cache
    envVars:
      - key: VITE_API_URL
        value: https://sd-parques.onrender.com/api
      - key: VITE_SOCKET_URL
        value: https://sd-parques.onrender.com

databases:
  - name: parques-db
    plan: free
    databaseName: parques
```

- [ ] **Step 3: Commit**

```bash
git add server/Dockerfile render.yaml
git commit -m "feat: Dockerfile and Render deploy configuration"
```

---

## Task 18: Capacitor Setup for Android APK

**Files:**
- Modify: `client/` (Capacitor init)

- [ ] **Step 1: Add Capacitor to Quasar project**

Run:
```bash
cd client
npx quasar mode add capacitor
```

- [ ] **Step 2: Configure Capacitor**

In `client/src-capacitor/capacitor.config.json`, set:
```json
{
  "appId": "com.parques.distribuido",
  "appName": "Parques Distribuido",
  "webDir": "www",
  "server": {
    "androidScheme": "https"
  }
}
```

- [ ] **Step 3: Build and test Android APK**

Run:
```bash
cd client
npx quasar build -m capacitor -T android
```

This generates the APK in `client/src-capacitor/android/app/build/outputs/apk/`.

- [ ] **Step 4: Commit**

```bash
git add client/
git commit -m "feat: Capacitor setup for Android APK build"
```

---

## Task 19: Integration Testing & Polish

- [ ] **Step 1: Start full stack locally**

```bash
docker-compose up -d db
cd server && python -m server.app &
cd client && npx quasar dev
```

- [ ] **Step 2: Test complete flow**

1. Open browser to http://localhost:9000 (Quasar dev server)
2. Register two users in different browser tabs
3. Both join lobby, select colors, host starts game
4. Play through: roll dice, move pieces, test captures
5. Request recommendation
6. Finish game and verify stats page

- [ ] **Step 3: Fix any issues found during testing**

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "fix: integration fixes from end-to-end testing"
```

---

## Summary

| Task | Component | Key Files |
|---|---|---|
| 1 | Scaffolding + DB | app.py, models/, docker-compose.yml |
| 2 | Auth | services/auth.py, routes/auth.py |
| 3 | Board Logic | game/board.py, game/constants.py |
| 4 | Game Engine | game/engine.py |
| 5 | Game Manager | game/manager.py |
| 6 | Socket Events | sockets/lobby.py, sockets/game_events.py |
| 7 | Berkeley Sync | services/berkeley.py, sockets/sync.py |
| 8 | Stats | services/stats.py, routes/stats.py |
| 9 | Recommendation | services/recommendation.py |
| 10 | Client Scaffold | Quasar project setup |
| 11 | Client Auth | LoginPage.vue, useAuth.js, userStore.js |
| 12 | Client Socket | useSocket.js, gameStore.js |
| 13 | Lobby Page | LobbyPage.vue |
| 14 | Board Component | BoardCanvas.vue |
| 15 | Game Page | GamePage.vue, DiceRoller, PlayerInfo |
| 16 | Stats Page | StatsPage.vue |
| 17 | Deploy Config | Dockerfile, render.yaml |
| 18 | Android APK | Capacitor setup |
| 19 | Integration Test | End-to-end flow testing |
