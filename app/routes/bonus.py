from flask import Blueprint, request, jsonify
from app.models import get_db
from app.services.bonus_service import BonusService
from app.routes.chat import get_user_from_token
import datetime

bp = Blueprint('bonus', __name__)

@bp.route('/bonus/balance', methods=['GET'])
def get_balance():
    user_id = get_user_from_token()
    if not user_id:
        return jsonify({"error": "Требуется авторизация"}), 401
    
    conn = get_db()
    user = conn.execute("SELECT bonus_points FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    
    return jsonify({"bonus_points": user['bonus_points']}), 200

@bp.route('/bonus/daily', methods=['POST'])
def claim_daily_bonus():
    user_id = get_user_from_token()
    if not user_id:
        return jsonify({"error": "Требуется авторизация"}), 401
    
    result = BonusService.claim_daily_bonus(user_id)
    return jsonify(result), 200 if result['success'] else 400

@bp.route('/bonus/redeem', methods=['POST'])
def redeem_bonus():
    user_id = get_user_from_token()
    if not user_id:
        return jsonify({"error": "Требуется авторизация"}), 401
    
    data = request.get_json()
    reward_id = data.get('reward_id')
    
    rewards = {
        'avatar_frame': {'points': 50, 'description': 'Рамка для аватара'},
        'premium_character': {'points': 200, 'description': 'Эксклюзивный персонаж'},
        'discount_coupon': {'points': 500, 'description': 'Скидка 20% на экскурсию'}
    }
    
    if reward_id not in rewards:
        return jsonify({"error": "Такой награды не существует"}), 400
    
    conn = get_db()
    user = conn.execute("SELECT bonus_points FROM users WHERE id = ?", (user_id,)).fetchone()
    
    if user['bonus_points'] < rewards[reward_id]['points']:
        conn.close()
        return jsonify({"error": "Недостаточно баллов"}), 400
    
    conn.execute(
        "UPDATE users SET bonus_points = bonus_points - ? WHERE id = ?",
        (rewards[reward_id]['points'], user_id)
    )
    conn.execute(
        "INSERT INTO bonus_transactions (user_id, amount, reason) VALUES (?, ?, ?)",
        (user_id, -rewards[reward_id]['points'], f'Обмен на {rewards[reward_id]["description"]}')
    )
    conn.commit()
    conn.close()
    
    return jsonify({
        "success": True,
        "message": f"Вы обменяли {rewards[reward_id]['points']} баллов на {rewards[reward_id]['description']}",
        "reward": reward_id
    }), 200

@bp.route('/bonus/transactions', methods=['GET'])
def get_transactions():
    user_id = get_user_from_token()
    if not user_id:
        return jsonify({"error": "Требуется авторизация"}), 401
    
    conn = get_db()
    rows = conn.execute(
        "SELECT amount, reason, created_at FROM bonus_transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT 20",
        (user_id,)
    ).fetchall()
    conn.close()
    
    transactions = [{"amount": r['amount'], "reason": r['reason'], "date": r['created_at']} for r in rows]
    return jsonify({"transactions": transactions}), 200