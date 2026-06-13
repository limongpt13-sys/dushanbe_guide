from flask import Blueprint, request, jsonify
from app.models import get_db
from app.utils.decorators import token_required
import datetime
import jwt
import os

bp = Blueprint('leaderboard', __name__)

@bp.route('/leaderboard', methods=['GET'])
def get_leaderboard():
    """Получить таблицу лидеров"""
    period = request.args.get('period', 'week')  # day, week, month, all
    
    conn = get_db()
    
    if period == 'day':
        rows = conn.execute("""
            SELECT 
                u.id, 
                u.username, 
                u.full_name,
                COALESCE(SUM(b.amount), 0) as points
            FROM users u
            LEFT JOIN bonus_transactions b ON u.id = b.user_id 
                AND DATE(b.created_at) = DATE('now')
            GROUP BY u.id
            HAVING points > 0
            ORDER BY points DESC
            LIMIT 20
        """).fetchall()
        
    elif period == 'week':
        rows = conn.execute("""
            SELECT 
                u.id, 
                u.username, 
                u.full_name,
                COALESCE(SUM(b.amount), 0) as points
            FROM users u
            LEFT JOIN bonus_transactions b ON u.id = b.user_id 
                AND b.created_at >= DATE('now', '-7 days')
            GROUP BY u.id
            HAVING points > 0
            ORDER BY points DESC
            LIMIT 20
        """).fetchall()
        
    elif period == 'month':
        rows = conn.execute("""
            SELECT 
                u.id, 
                u.username, 
                u.full_name,
                COALESCE(SUM(b.amount), 0) as points
            FROM users u
            LEFT JOIN bonus_transactions b ON u.id = b.user_id 
                AND b.created_at >= DATE('now', '-30 days')
            GROUP BY u.id
            HAVING points > 0
            ORDER BY points DESC
            LIMIT 20
        """).fetchall()
        
    else:
        rows = conn.execute("""
            SELECT 
                id, 
                username, 
                full_name, 
                bonus_points as points
            FROM users
            ORDER BY bonus_points DESC
            LIMIT 20
        """).fetchall()
    
    conn.close()
    
    leaderboard = []
    for i, row in enumerate(rows):
        leaderboard.append({
            'rank': i + 1,
            'id': row['id'],
            'username': row['username'],
            'full_name': row['full_name'],
            'points': row['points']
        })
    
    return jsonify({
        'leaderboard': leaderboard,
        'period': period,
        'updated_at': datetime.datetime.now().isoformat()
    }), 200


@bp.route('/leaderboard/me', methods=['GET'])
@token_required
def get_my_rank():
    """Получить ранг текущего пользователя"""
    user_id = request.user_id
    
    conn = get_db()
    
    rank = conn.execute("""
        SELECT COUNT(*) + 1 as rank
        FROM users
        WHERE bonus_points > (SELECT bonus_points FROM users WHERE id = ?)
    """, (user_id,)).fetchone()
    
    user = conn.execute("""
        SELECT id, username, full_name, bonus_points as points
        FROM users WHERE id = ?
    """, (user_id,)).fetchone()
    
    conn.close()
    
    return jsonify({
        'rank': rank['rank'],
        'user': dict(user)
    }), 200


@bp.route('/leaderboard/top', methods=['GET'])
def get_top_three():
    """Получить топ-3 пользователей"""
    conn = get_db()
    
    rows = conn.execute("""
        SELECT 
            username, 
            full_name, 
            bonus_points as points
        FROM users
        ORDER BY bonus_points DESC
        LIMIT 3
    """).fetchall()
    
    conn.close()
    
    top = []
    for i, row in enumerate(rows):
        top.append({
            'rank': i + 1,
            'username': row['username'],
            'full_name': row['full_name'],
            'points': row['points']
        })
    
    return jsonify({'top_three': top}), 200