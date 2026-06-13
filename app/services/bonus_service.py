from app.models import get_db
import datetime

class BonusService:
    @staticmethod
    def add_points(user_id, points, reason, max_per_day=None):
        conn = get_db()
        if max_per_day:
            today_str = datetime.date.today().isoformat()
            today_points = conn.execute("""
                SELECT COALESCE(SUM(amount), 0) as total
                FROM bonus_transactions
                WHERE user_id = ? AND reason = ? AND DATE(created_at) = DATE(?)
            """, (user_id, reason, today_str)).fetchone()
            
            if today_points['total'] >= max_per_day:
                conn.close()
                return False
        
        conn.execute("UPDATE users SET bonus_points = bonus_points + ? WHERE id = ?", (points, user_id))
        conn.execute("INSERT INTO bonus_transactions (user_id, amount, reason) VALUES (?, ?, ?)", (user_id, points, reason))
        conn.commit()
        conn.close()
        return True
    
    @staticmethod
    def claim_daily_bonus(user_id):
        conn = get_db()
        today = datetime.date.today()
        today_str = today.isoformat()
        
        last_bonus = conn.execute("SELECT last_claim_date, streak FROM daily_bonus WHERE user_id = ?", (user_id,)).fetchone()
        streak = 1
        
        if last_bonus and last_bonus['last_claim_date']:
            try:
                last_date = datetime.datetime.strptime(last_bonus['last_claim_date'], '%Y-%m-%d').date()
                if last_date == today:
                    conn.close()
                    return {"success": False, "error": "Сегодня вы уже получили бонус"}
                
                streak = last_bonus['streak'] + 1 if last_date == today - datetime.timedelta(days=1) else 1
            except (ValueError, TypeError):
                streak = 1
        
        bonus_amount = min(10 + (streak // 7) * 5, 50)
        
        conn.execute("""
            INSERT INTO daily_bonus (user_id, last_claim_date, streak) VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET last_claim_date = EXCLUDED.last_claim_date, streak = EXCLUDED.streak
        """, (user_id, today_str, streak))
        
        conn.execute("UPDATE users SET bonus_points = bonus_points + ? WHERE id = ?", (bonus_amount, user_id))
        conn.execute("INSERT INTO bonus_transactions (user_id, amount, reason) VALUES (?, ?, ?)", (user_id, bonus_amount, f'Ежедневный бонус (стрик: {streak} дней)'))
        conn.commit()
        conn.close()
        
        from app.services.achievement_service import AchievementService
        AchievementService.check_and_update_achievements(user_id)
        
        return {"success": True, "bonus": bonus_amount, "streak": streak, "message": f"Вы получили {bonus_amount} баллов! Стрик: {streak} дней"}
