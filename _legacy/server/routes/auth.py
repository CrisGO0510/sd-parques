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
