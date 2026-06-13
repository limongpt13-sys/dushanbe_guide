from flask import Blueprint, request, jsonify, current_app
from app.models import get_db
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from app.utils.validators import validate_email, validate_password, validate_username, validate_full_name, sanitize_input

bp = Blueprint('auth', __name__)

@bp.route('/register', methods=['POST', 'OPTIONS'])
def register():
    if request.method == 'OPTIONS': return '', 200
    data = request.get_json()
    
    if not all(k in data for k in ('full_name', 'email', 'username', 'password')):
        return jsonify({"error": "Заполни все поля!"}), 400
        
    full_name = sanitize_input(data['full_name'])
    email = sanitize_input(data['email'])
    username = sanitize_input(data['username'])
    password = data['password']
    
    for val_func, val_data in [(validate_full_name, full_name), (validate_email, email), (validate_username, username), (validate_password, password)]:
        is_ok, msg = val_func(val_data)
        if not is_ok: return jsonify({"error": msg}), 400
        
    conn = get_db()
    if conn.execute("SELECT id FROM users WHERE email = ? OR username = ?", (email, username)).fetchone():
        conn.close()
        return jsonify({"error": "Пользователь с таким Email или Логином уже существует"}), 400
        
    hashed_pw = generate_password_hash(password)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (username, email, password, full_name, bonus_points) VALUES (?, ?, ?, ?, 0)",
        (username, email, hashed_pw, full_name)
    )
    user_id = cursor.lastrowid
    
    # Сразу создаем запись для бонусов во избежание NULL-крашей
    cursor.execute("INSERT INTO daily_bonus (user_id, last_claim_date, streak) VALUES (?, NULL, 0)", (user_id,))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "message": "Регистрация успешна!"}), 201

@bp.route('/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS': return '', 200
    data = request.get_json()
    
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (data.get('username'),)).fetchone()
    conn.close()
    
    if user and check_password_hash(user['password'], data.get('password')):
        secret = current_app.config.get('JWT_SECRET_KEY') or 'dev-jwt-key-secure-2026'
        token = jwt.encode({
            'user_id': user['id'],
            'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)
        }, secret, algorithm='HS256')
        
        return jsonify({
            "token": token,
            "user": {
                "id": user['id'],
                "username": user['username'],
                "full_name": user['full_name'],
                "bonus_points": user['bonus_points']
            }
        }), 200
    return jsonify({"error": "Неверный логин или пароль"}), 401
