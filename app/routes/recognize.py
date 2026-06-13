from flask import Blueprint, request, jsonify, current_app
from app.models import get_db
from app.utils.decorators import token_required, rate_limit  # Наш рабочий фикс авторизации
from app.services.ai_service import AIService
from app.services.bonus_service import BonusService
from app.services.achievement_service import AchievementService

# ФИКС: Создаем объект Blueprint, чтобы Flask видел этот роут
bp = Blueprint('recognize', __name__)

@bp.route('/recognize', methods=['POST'])
@token_required  # Извлекает user_id из JWT токена автоматически
@rate_limit(limit=5, period=60)  # Защита от спама: макс 5 фото в минуту
def recognize_place():
    user_id = request.user_id
    
    # Проверяем, прикрепил ли пользователь файл изображения
    if 'image' not in request.files:
        return jsonify({"error": "Файл изображения отсутствует в запросе"}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "Файл не выбран"}), 400
        
    try:
        # Читаем байты картинки для передачи в OpenAI
        image_bytes = file.read()
        
        # Вызываем наш оптимизированный ИИ-сервис (с кэшированием)
        ai_result = AIService.recognize_landmark(image_bytes)
        
        # Сохраняем успешное сканирование в историю
        conn = get_db()
        conn.execute("""
            INSERT INTO scan_history (user_id, result) 
            VALUES (?, ?)
        """, (user_id, ai_result))
        conn.commit()
        
        # Начисляем 5 баллов за распознавание (максимум 10 баллов в день)
        BonusService.add_points(user_id, 5, 'scan_photo', max_per_day=10)
        
        # Триггерим фоновую проверку ачивок (например, "Первое сканирование")
        new_achievements = AchievementService.check_and_update_achievements(user_id)
        
        # Вытягиваем свежий баланс для мгновенного обновления плашки на фронтенде
        user_data = conn.execute("SELECT bonus_points FROM users WHERE id = ?", (user_id,)).fetchone()
        current_balance = user_data['bonus_points'] if user_data else 0
        conn.close()
        
        return jsonify({
            "success": True,
            "result": ai_result,
            "current_balance": current_balance,  # Передаем на фронт
            "new_achievements": new_achievements  # Список открытых ачивок
        }), 200
        
    except Exception as e:
        print(f"🛑 Ошибка в роуте распознавания: {str(e)}")
        return jsonify({"error": "Не удалось обработать изображение"}), 500
