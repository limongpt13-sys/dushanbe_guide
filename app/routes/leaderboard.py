from flask import Blueprint, jsonify, request
from app.models import get_db
from app.utils.decorators import token_required

bp = Blueprint('leaderboard', __name__)

@bp.route('/leaderboard', methods=['GET'])
@token_required
def get_leaderboard():
    user_id = request.user_id
    conn = get_db()
    
    # Получаем ТОП-10 пользователей по баллам
    top_users = conn.execute("""
        SELECT id, username, full_name, bonus_points 
        FROM users 
        ORDER BY bonus_points DESC LIMIT 10
    """).fetchall()
    
    # Вычисляем место текущего пользователя в системе
    user_rank_row = conn.execute("""
        SELECT COUNT(*) + 1 as rank FROM users 
        WHERE bonus_points > (SELECT bonus_points FROM users WHERE id = ?)
    """, (user_id,)).fetchone()
    
    user_rank = user_rank_row['rank'] if user_rank_row else 0
    conn.close()
    
    leaderboard_list = []
    for index, u in enumerate(top_users):
        leaderboard_list.append({
            "rank": index + 1,
            "username": u['username'],
            "full_name": u['full_name'],
            "bonus_points": u['bonus_points'],
            "is_current_user": u['id'] == user_id
        })
        
    return jsonify({
        "leaderboard": leaderboard_list,
        "user_current_rank": user_rank
    }), 200
