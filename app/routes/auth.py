from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
import os
from app.models import get_db

bp = Blueprint('auth', __name__)

def generate_tokens(user_id):
    """Генерирует access и refresh токены"""
    access_token = jwt.encode(
        {'user_id': user_id, 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=15)},
        os.getenv('JWT_SECRET_KEY', 'dev-secret-key'),
        algorithm='HS256'
    )
    refresh_token = jwt.encode(
        {'user_id': user_id, 'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)},
        os.getenv('JWT_SECRET_KEY', 'dev-secret-key'),
        algorithm='HS256'
    )
    return access_token, refresh_token

@bp.route('/register', methods=['POST', 'OPTIONS'])
def register():
    # Обработка preflight запроса
    if request.method == 'OPTIONS':
        return '', 200
    
    data = request.get_json()
    
    # Валидация
    if not all(k in data for k in ('full_name', 'email', 'username', 'password')):
        return jsonify({"error": "Заполните все поля"}), 400
    
    if len(data['password']) < 6:
        return jsonify({"error": "Пароль должен быть минимум 6 символов"}), 400
    
    if '@' not in data['email'] or '.' not in data['email']:
        return jsonify({"error": "Неверный формат email"}), 400
    
    full_name = data['full_name']
    email = data['email']
    username = data['username']
    hashed_password = generate_password_hash(data['password'])
    
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (full_name, email, username, password, bonus_points) VALUES (?, ?, ?, ?, ?)",
            (full_name, email, username, hashed_password, 50)
        )
        conn.commit()
        user_id = cursor.lastrowid
        
        # Записываем бонус за регистрацию
        cursor.execute(
            "INSERT INTO bonus_transactions (user_id, amount, reason) VALUES (?, ?, ?)",
            (user_id, 50, 'Регистрация')
        )
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Регистрация успешна! Вы получили 50 бонусов", "user_id": user_id}), 201
    except Exception as e:
        conn.close()
        if "UNIQUE" in str(e):
            return jsonify({"error": "Пользователь с таким email или логином уже существует"}), 400
        return jsonify({"error": str(e)}), 500

@bp.route('/login', methods=['POST', 'OPTIONS'])
def login():
    # Обработка preflight запроса
    if request.method == 'OPTIONS':
        return '', 200
    
    data = request.get_json()
    
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"error": "Введите логин и пароль"}), 400
    
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (data['username'],)).fetchone()
    conn.close()
    
    if user and check_password_hash(user['password'], data['password']):
        access_token, refresh_token = generate_tokens(user['id'])
        return jsonify({
            "message": "Успешный вход",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user['id'],
                "full_name": user['full_name'],
                "email": user['email'],
                "username": user['username'],
                "bonus_points": user['bonus_points']
            }
        }), 200
    else:
        return jsonify({"error": "Неверный логин или пароль"}), 401

@bp.route('/refresh', methods=['POST', 'OPTIONS'])
def refresh():
    """Обновление access токена по refresh токену"""
    if request.method == 'OPTIONS':
        return '', 200
    
    data = request.get_json()
    refresh_token = data.get('refresh_token')
    
    if not refresh_token:
        return jsonify({"error": "Refresh token отсутствует"}), 401
    
    try:
        payload = jwt.decode(refresh_token, os.getenv('JWT_SECRET_KEY', 'dev-secret-key'), algorithms=['HS256'])
        user_id = payload['user_id']
        new_access_token, _ = generate_tokens(user_id)
        return jsonify({"access_token": new_access_token}), 200
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Refresh token истёк, войдите заново"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Недействительный refresh token"}), 401