from flask import Blueprint, request, jsonify
from app.models import get_db
from app.utils.decorators import token_required  # ФИКС: Используем рабочий декоратор
from app.services.achievement_service import AchievementService
import base64

bp = Blueprint('profile', __name__)

@bp.route('/profile', methods=['GET'])
@token_required  # ФИКС: Защищаем роут проверки токена
def get_profile():
    user_id = request.user_id  # Автоматически получаем чистый ID пользователя
    
    conn = get_db()
    user = conn.execute("""
        SELECT id, full_name, email, username, avatar_path, bonus_points, created_at
        FROM users WHERE id = ?
    """, (user_id,)).fetchone()
    
    if not user:
        conn.close()
        return jsonify({"error": "Пользователь не найден"}), 404
    
    # Собираем статистику сообщений и активных дней
    stats = conn.execute("""
        SELECT 
            COUNT(DISTINCT CASE WHEN sender = 'user' THEN id END) as total_messages,
            COUNT(DISTINCT DATE(created_at)) as active_days
        FROM chat_history WHERE user_id = ?
    """, (user_id,)).fetchone()
    
    scans = conn.execute("SELECT COUNT(*) as total_scans FROM scan_history WHERE user_id = ?", (user_id,)).fetchone()
    
    # ФИКС: Синхронизируем и запрашиваем список достижений через наш рабочий AchievementService
    AchievementService.check_and_update_achievements(user_id)
    
    rows = conn.execute("""
        SELECT al.points_reward, COALESCE(ua.is_unlocked, 0) as is_unlocked
        FROM achievements_list al
        LEFT JOIN user_achievements ua ON al.id = ua.achievement_id AND ua.user_id = ?
    """, (user_id,)).fetchall()
    
    conn.close()
    
    unlocked_achievements = sum(1 for r in rows if r['is_unlocked'])
    
    return jsonify({
        "success": True,
        "user": {
            "id": user['id'],
            "full_name": user['full_name'],
            "email": user['email'],
            "username": user['username'],
            "avatar_path": user['avatar_path'],
            "bonus_points": user['bonus_points'],
            "created_at": user['created_at']
        },
        "statistics": {
            "total_messages": stats['total_messages'] or 0,
            "total_scans": scans['total_scans'] or 0,
            "active_days": stats['active_days'] or 0,
            "unlocked_achievements": unlocked_achievements,
            "total_achievements": len(rows) if rows else 0
        }
    }), 200

@bp.route('/profile/avatar', methods=['POST'])
@token_required  # ФИКС: Защищаем роут
def update_avatar():
    user_id = request.user_id
    data = request.get_json() or {}
    avatar_base64 = data.get('avatar')
    
    if not avatar_base64:
        return jsonify({"error": "Изображение не предоставлено"}), 400
    
    conn = get_db()
    conn.execute(
        "UPDATE users SET avatar_path = ? WHERE id = ?",
        (avatar_base64, user_id)
    )
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "message": "Аватар успешно обновлён"}), 200

@bp.route('/profile/characters', methods=['GET'])
@token_required  # ФИКС: Защищаем роут
def get_unlocked_characters():
    user_id = request.user_id
    
    conn = get_db()
    characters = conn.execute("SELECT * FROM characters").fetchall()
    conn.close()
    
    return jsonify({
        "success": True,
        "characters": [dict(c) for c in characters]
    }), 200
