from flask import Blueprint, request, jsonify
from app.services.ai_service import AIService
from app.services.bonus_service import BonusService
from app.routes.chat import get_user_from_token
from app.models import get_db
import base64

bp = Blueprint('recognize', __name__)

@bp.route('/recognize', methods=['POST'])
def recognize():
    user_id = get_user_from_token()
    
    if 'image' not in request.files:
        return jsonify({"error": "Файл изображения не найден"}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "Файл не выбран"}), 400
    
    # Проверка размера
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    
    if size > 5 * 1024 * 1024:  # 5MB
        return jsonify({"error": "Файл слишком большой (макс. 5MB)"}), 413
    
    try:
        image_bytes = file.read()
        result_text = AIService.recognize_landmark(image_bytes)
        
        # Если пользователь авторизован, сохраняем историю и начисляем бонус
        if user_id:
            conn = get_db()
            conn.execute(
                "INSERT INTO scan_history (user_id, image_data, result) VALUES (?, ?, ?)",
                (user_id, base64.b64encode(image_bytes).decode('utf-8'), result_text)
            )
            conn.commit()
            conn.close()
            
            # Начисляем 5 баллов за распознавание (макс 10 в день)
            BonusService.add_points(user_id, 5, 'scan_photo', max_per_day=10)
        
        return jsonify({"analysis": result_text}), 200
        
    except Exception as e:
        return jsonify({"error": f"Ошибка обработки: {str(e)}"}), 500

@bp.route('/recognize/history', methods=['GET'])
def get_scan_history():
    user_id = get_user_from_token()
    if not user_id:
        return jsonify({"error": "Требуется авторизация"}), 401
    
    conn = get_db()
    rows = conn.execute(
        "SELECT id, result, created_at FROM scan_history WHERE user_id = ? ORDER BY created_at DESC LIMIT 20",
        (user_id,)
    ).fetchall()
    conn.close()
    
    history = [{"id": r['id'], "result": r['result'], "date": r['created_at']} for r in rows]
    return jsonify({"history": history}), 200