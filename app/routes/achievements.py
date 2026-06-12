from flask import Blueprint, request, jsonify
from app.utils.decorators import token_required
from app.services.achievement_service import AchievementService

bp = Blueprint('achievements', __name__)

@bp.route('/achievements', methods=['GET'])
@token_required
def get_achievements():
    """Получить все достижения с прогрессом пользователя"""
    user_id = request.user_id
    
    achievements = AchievementService.get_user_achievements_with_progress(user_id)
    
    # Подсчёт статистики
    unlocked_count = sum(1 for a in achievements if a['is_unlocked'])
    total_points = sum(a['points_reward'] for a in achievements if a['is_unlocked'])
    total_achievements = len(achievements)
    
    return jsonify({
        'achievements': achievements,
        'total_achievements': total_achievements,
        'unlocked_count': unlocked_count,
        'total_points_earned': total_points,
        'completion_percentage': (unlocked_count / total_achievements * 100) if total_achievements > 0 else 0
    }), 200