from flask import Blueprint, request, jsonify
from app.models import get_db
from app.services.bonus_service import BonusService
from app.utils.decorators import token_required  # ФИКС: Подключаем рабочий декоратор

bp = Blueprint('bonus', __name__)

@bp.route('/bonus/balance', methods=['GET'])
@token_required  # ФИКС: Автоматическая авторизация
def get_balance():
    user_id = request.user_id
    
    conn = get_db()
    user = conn.execute("SELECT bonus_points FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    
    if not user:
        return jsonify({"error": "Пользователь не найден"}), 404
        
    return jsonify({"bonus_points": user['bonus_points']}), 200

@bp.route('/bonus/daily', methods=['POST'])
@token_required  # ФИКС: Защита токеном
def claim_daily_bonus():
    user_id = request.user_id
    
    # Метод BonusService теперь защищен от крашей с NULL-датами
    result = BonusService.claim_daily_bonus(user_id)
    return jsonify(result), 200 if result['success'] else 400

@bp.route('/bonus/redeem', methods=['POST'])
@token_required  # ФИКС: Защита токеном
def redeem_bonus():
    user_id = request.user_id
    data = request.get_json() or {}
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
    
    if not user:
        conn.close()
        return jsonify({"error": "Пользователь не найден"}), 404
        
    if user['bonus_points'] < rewards[reward_id]['points']:
        conn.close()
        return jsonify({"error": "Недостаточно баллов"}), 400
    
    # Списание баллов и фиксация транзакции
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
@token_required  # ФИКС: Защита токеном
def get_transactions():
    user_id = request.user_id
    
    conn = get_db()
    rows = conn.execute(
        "SELECT amount, reason, created_at FROM bonus_transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT 20",
        (user_id,)
    ).fetchall()
    conn.close()
    
    transactions = [{"amount": r['amount'], "reason": r['reason'], "date": r['created_at']} for r in rows]
    return jsonify({"transactions": transactions}), 200
