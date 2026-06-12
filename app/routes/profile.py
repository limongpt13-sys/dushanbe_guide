from flask import Blueprint, request, jsonify
from app.models import get_db
from app.routes.chat import get_user_from_token
from app.services.achievement_service import AchievementService
import base64

bp = Blueprint('profile', __name__)

@bp.route('/profile', methods=['GET'])
def get_profile():
    user_id = get_user_from_token()
    if not user_id:
        return jsonify({"error": "Требуется авторизация"}), 401
    
    conn = get_db()
    user = conn.execute("""
        SELECT id, full_name, email, username, avatar_path, bonus_points, created_at
        FROM users WHERE id = ?
    """, (user_id,)).fetchone()
    
    stats = conn.execute("""
        SELECT 
            COUNT(DISTINCT CASE WHEN sender = 'user' THEN id END) as total_messages,
            COUNT(DISTINCT DATE(timestamp)) as active_days
        FROM chat_history WHERE user_id = ?
    """, (user_id,)).fetchone()
    
    scans = conn.execute("SELECT COUNT(*) as total_scans FROM scan_history WHERE user_id = ?", (user_id,)).fetchone()
    
    # Получаем количество разблокированных достижений
    achievements = AchievementService.get_user_achievements_with_progress(user_id)
    unlocked_achievements = sum(1 for a in achievements if a['is_unlocked'])
    
    conn.close()
    
    return jsonify({
        "user": dict(user),
        "statistics": {
            "total_messages": stats['total_messages'] or 0,
            "total_scans": scans['total_scans'] or 0,
            "active_days": stats['active_days'] or 0,
            "unlocked_achievements": unlocked_achievements,
            "total_achievements": len(achievements)
        }
    }), 200

@bp.route('/profile/avatar', methods=['POST'])
def update_avatar():
    user_id = get_user_from_token()
    if not user_id:
        return jsonify({"error": "Требуется авторизация"}), 401
    
    data = request.get_json()
    avatar_base64 = data.get('avatar')
    
    if not avatar_base64:
        return jsonify({"error": "Изображение не предоставлено"}), 400
    
    conn = get_db()
    conn.execute(
        "UPDATE users SET avatar_path = ? WHERE id = ?",
        (avatar_base64[:500], user_id)
    )
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Аватар обновлён"}), 200

@bp.route('/profile/characters', methods=['GET'])
def get_unlocked_characters():
    user_id = get_user_from_token()
    if not user_id:
        return jsonify({"error": "Требуется авторизация"}), 401
    
    conn = get_db()
    characters = conn.execute("SELECT * FROM characters").fetchall()
    conn.close()
    
    return jsonify({"characters": [dict(c) for c in characters]}), 200