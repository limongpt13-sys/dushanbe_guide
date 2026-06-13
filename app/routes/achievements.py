from flask import Blueprint, request, jsonify
from app.models import get_db
from app.utils.decorators import token_required
from app.services.achievement_service import AchievementService
import datetime

bp = Blueprint('achievements', __name__)

@bp.route('/achievements', methods=['GET'])
@token_required
def get_achievements():
    """Получить все достижения с прогрессом пользователя"""
    user_id = request.user_id
    conn = get_db()
    
    # Сначала обновляем все достижения (чтобы прогресс был актуальным)
    AchievementService.check_and_unlock(user_id, conn)
    conn.commit()
    
    # Получаем статистику пользователя для отображения
    msg_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM chat_history WHERE user_id = ? AND sender = 'user'",
        (user_id,)
    ).fetchone()['cnt']
    
    scan_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM scan_history WHERE user_id = ?",
        (user_id,)
    ).fetchone()['cnt']
    
    unique_places = conn.execute(
        "SELECT COUNT(DISTINCT result) as cnt FROM scan_history WHERE user_id = ?",
        (user_id,)
    ).fetchone()['cnt']
    
    streak_row = conn.execute(
        "SELECT COALESCE(streak, 0) as streak FROM daily_bonus WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    streak = streak_row['streak'] if streak_row else 0
    
    somoni_msg = conn.execute(
        "SELECT COUNT(*) as cnt FROM chat_history WHERE user_id = ? AND character_id = 'somoni' AND sender = 'user'",
        (user_id,)
    ).fetchone()['cnt']
    
    rudaki_msg = conn.execute(
        "SELECT COUNT(*) as cnt FROM chat_history WHERE user_id = ? AND character_id = 'rudaki' AND sender = 'user'",
        (user_id,)
    ).fetchone()['cnt']
    
    perfect_month = 1 if (streak >= 30 and msg_count >= 100) else 0
    
    # Получаем все достижения с прогрессом из user_achievements
    user_achievements = {}
    user_rows = conn.execute(
        "SELECT achievement_id, progress, is_unlocked FROM user_achievements WHERE user_id = ?",
        (user_id,)
    ).fetchall()
    for row in user_rows:
        user_achievements[row['achievement_id']] = {
            'progress': row['progress'],
            'is_unlocked': row['is_unlocked']
        }
    
    all_achievements = conn.execute("SELECT * FROM achievements_list").fetchall()
    
    achievements = []
    for ach in all_achievements:
        ach_id = ach['id']
        required = ach['required_value']
        
        # Берём прогресс из user_achievements, если есть
        if ach_id in user_achievements:
            progress = user_achievements[ach_id]['progress']
            is_unlocked = user_achievements[ach_id]['is_unlocked']
        else:
            # Вычисляем прогресс на лету (на случай, если записи нет)
            if ach_id == 'first_chat':
                progress = min(msg_count, required)
                is_unlocked = msg_count >= required
            elif ach_id == 'first_scan':
                progress = min(scan_count, required)
                is_unlocked = scan_count >= required
            elif ach_id == 'chat_master':
                progress = min(msg_count, required)
                is_unlocked = msg_count >= required
            elif ach_id == 'photo_expert':
                progress = min(scan_count, required)
                is_unlocked = scan_count >= required
            elif ach_id == 'streak_7':
                progress = min(streak, required)
                is_unlocked = streak >= required
            elif ach_id == 'streak_30':
                progress = min(streak, required)
                is_unlocked = streak >= required
            elif ach_id == 'somoni_expert':
                progress = min(somoni_msg, required)
                is_unlocked = somoni_msg >= required
            elif ach_id == 'rudaki_expert':
                progress = min(rudaki_msg, required)
                is_unlocked = rudaki_msg >= required
            elif ach_id == 'all_places':
                progress = min(unique_places, required)
                is_unlocked = unique_places >= required
            elif ach_id == 'perfect_month':
                progress = perfect_month
                is_unlocked = perfect_month == 1
            else:
                progress = 0
                is_unlocked = False
        
        achievements.append({
            'id': ach_id,
            'title': ach['title'],
            'description': ach['description'],
            'category': ach['category'],
            'icon': ach['icon'],
            'points_reward': ach['points_reward'],
            'required_value': required,
            'progress': progress,
            'is_unlocked': is_unlocked,
        })
    
    conn.close()
    
    # Подсчёт общей статистики
    total_achievements = len(achievements)
    unlocked_count = sum(1 for a in achievements if a['is_unlocked'])
    total_points = sum(a['points_reward'] for a in achievements if a['is_unlocked'])
    
    return jsonify({
        'achievements': achievements,
        'total_achievements': total_achievements,
        'unlocked_count': unlocked_count,
        'total_points_earned': total_points,
        'completion_percentage': (unlocked_count / total_achievements * 100) if total_achievements > 0 else 0
    }), 200