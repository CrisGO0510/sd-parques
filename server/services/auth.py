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
