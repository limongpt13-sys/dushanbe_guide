from flask import Blueprint, request, jsonify
from app.models import get_db
from app.utils.decorators import token_required
from app.services.ai_service import AIService
from app.services.bonus_service import BonusService
from app.services.achievement_service import AchievementService

bp = Blueprint('chat', __name__)

# Простые системные промпты для персонажей
CHARACTERS = {
    'somoni': "Ты — Исмоил Сомони, эмир государства Саманидов. Говори величественно, мудро, используй исторические факты X века.",
    'rudaki': "Ты — Абу Абдуллах Рудаки, основоположник таджикской классической поэзии. Твои ответы философичны, поэтичны и изящны."
}

@bp.route('/chat', methods=['POST'])
@token_required
def send_message():
    user_id = request.user_id # Автоматически досталось из токена!
    data = request.get_json()
    
    character_id = data.get('character_id')
    user_message = data.get('message', '').strip()
    
    if character_id not in CHARACTERS:
        return jsonify({"error": "Персонаж не найден"}), 404
    if not user_message:
        return jsonify({"error": "Сообщение не может быть пустым"}), 400
        
    conn = get_db()
    
    # Загружаем последние 10 сообщений контекста для ИИ
    rows = conn.execute("""
        SELECT sender, message FROM chat_history 
        WHERE user_id = ? AND character_id = ? 
        ORDER BY id DESC LIMIT 10
    """, (user_id, character_id)).fetchall()
    
    # Разворачиваем историю в правильном хронологическом порядке
    history = [{"role": r['sender'], "content": r['message']} for r in reversed(rows)]
    
    # Запрос к OpenAI gpt-4o-mini
    ai_response = AIService.chat_with_character(CHARACTERS[character_id], user_message, history)
    
    # Сохраняем переписку в базу данных
    conn.execute("""
        INSERT INTO chat_history (user_id, character_id, sender, message) 
        VALUES (?, ?, 'user', ?)
    """, (user_id, character_id, user_message))
    
    conn.execute("""
        INSERT INTO chat_history (user_id, character_id, sender, message) 
        VALUES (?, ?, 'assistant', ?)
    """, (user_id, character_id, ai_response))
    conn.commit()
    
    # Начисляем 1 балл за сообщение (максимум 20 баллов в день)
    BonusService.add_points(user_id, 1, 'chat_message', max_per_day=20)
    
    # Мгновенно проверяем, не открыл ли пользователь ачивки 'somoni_expert' или 'rudaki_expert'
    new_achievements = AchievementService.check_and_update_achievements(user_id)
    
    # Получаем актуальный баланс
    user_data = conn.execute("SELECT bonus_points FROM users WHERE id = ?", (user_id,)).fetchone()
    current_balance = user_data['bonus_points'] if user_data else 0
    conn.close()
    
    return jsonify({
        "response": ai_response,
        "current_balance": current_balance, # Фронтенд сразу видит изменения
        "new_achievements": new_achievements # Массив строк с новыми ачивками
    }), 200
