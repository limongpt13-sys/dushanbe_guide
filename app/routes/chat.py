from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import get_db
from app.services.ai_service import AIService
from app.services.bonus_service import BonusService
from app.services.achievement_service import AchievementService
import jwt
import os

bp = Blueprint('chat', __name__)

def get_user_from_token():
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None
    
    try:
        token = auth_header.split(' ')[1]
        payload = jwt.decode(token, os.getenv('JWT_SECRET_KEY'), algorithms=['HS256'])
        return payload['user_id']
    except:
        return None

@bp.route('/chat', methods=['POST'])
def chat():
    user_id = get_user_from_token()
    data = request.get_json()
    
    if not data or 'character_id' not in data or 'message' not in data:
        return jsonify({"error": "Переданы не все поля"}), 400
    
    character_id = data['character_id']
    user_message = data['message']
    
    conn = get_db()
    
    # Проверяем персонажа
    character = conn.execute("SELECT * FROM characters WHERE id = ?", (character_id,)).fetchone()
    if not character:
        conn.close()
        return jsonify({"error": "Персонаж не найден"}), 404
    
    # Получаем историю для контекста
    history_messages = []
    if user_id:
        rows = conn.execute(
            "SELECT sender, message FROM chat_history WHERE user_id = ? AND character_id = ? ORDER BY timestamp DESC LIMIT 10",
            (user_id, character_id)
        ).fetchall()
        history_messages = [{"role": r['sender'], "content": r['message']} for r in reversed(rows)]
        
        # Сохраняем сообщение пользователя
        conn.execute(
            "INSERT INTO chat_history (user_id, character_id, sender, message) VALUES (?, ?, ?, ?)",
            (user_id, character_id, 'user', user_message)
        )
        conn.commit()
    
    # Ответ AI
    ai_response = AIService.chat_with_character(character['system_prompt'], user_message, history_messages)
    
    if user_id:
        conn.execute(
            "INSERT INTO chat_history (user_id, character_id, sender, message) VALUES (?, ?, ?, ?)",
            (user_id, character_id, 'assistant', ai_response)
        )
        conn.commit()
        
        # НАЧИСЛЯЕМ БАЛЛЫ ЗА СООБЩЕНИЕ
        BonusService.add_points(user_id, 1, 'chat_message', max_per_day=20)
        
        # ПРОВЕРЯЕМ ДОСТИЖЕНИЯ
        conn_ach = get_db()
        AchievementService.check_and_unlock(user_id, conn_ach)
        conn_ach.commit()
        conn_ach.close()
    
    conn.close()
    
    return jsonify({
        "character_id": character_id,
        "response": ai_response
    }), 200

@bp.route('/chat/history/<character_id>', methods=['GET'])
def get_chat_history(character_id):
    user_id = get_user_from_token()
    if not user_id:
        return jsonify({"error": "Требуется авторизация"}), 401
    
    conn = get_db()
    rows = conn.execute(
        "SELECT sender, message, timestamp FROM chat_history WHERE user_id = ? AND character_id = ? ORDER BY timestamp ASC LIMIT 50",
        (user_id, character_id)
    ).fetchall()
    conn.close()
    
    history = [{"sender": r['sender'], "message": r['message'], "timestamp": r['timestamp']} for r in rows]
    return jsonify({"history": history}), 200