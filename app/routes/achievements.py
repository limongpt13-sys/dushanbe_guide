from flask import Blueprint, jsonify, request
from app.models import get_db
from app.utils.decorators import token_required
from app.services.achievement_service import AchievementService

bp = Blueprint('achievements', __name__)

@bp.route('/achievements', methods=['GET'])
@token_required
def get_achievements():
    user_id = request.user_id
    
    # Синхронизируем перед отдачей
    AchievementService.check_and_update_achievements(user_id)
    
    conn = get_db()
    rows = conn.execute("""
        SELECT al.*, COALESCE(ua.progress, 0) as progress, COALESCE(ua.is_unlocked, 0) as is_unlocked
        FROM achievements_list al
        LEFT JOIN user_achievements ua ON al.id = ua.achievement_id AND ua.user_id = ?
    """, (user_id,)).fetchall()
    conn.close()
    
    achievements = []
    unlocked_count = 0
    total_points = 0
    
    for r in rows:
        is_unl = bool(r['is_unlocked'])
        if is_unl:
            unlocked_count += 1
            total_points += r['points_reward']
            
        achievements.append({
            'id': r['id'], 'title': r['title'], 'description': r['description'],
            'category': r['category'], 'icon': r['icon'], 'points_reward': r['points_reward'],
            'required_value': r['required_value'], 'progress': r['progress'], 'is_unlocked': is_unl
        })
        
    total_ach = len(achievements)
    return jsonify({
        'achievements': achievements,
        'total_achievements': total_ach,
        'unlocked_count': unlocked_count,
        'total_points_earned': total_points,
        'completion_percentage': (unlocked_count / total_ach * 100) if total_ach > 0 else 0
    }), 200
