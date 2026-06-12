from app.models import get_db
import datetime

class BonusService:
    @staticmethod
    def add_points(user_id, points, reason, max_per_day=None):
        """Начисляет баллы пользователю с проверкой лимита по КОЛИЧЕСТВУ операций"""
        conn = get_db()
        
        if max_per_day:
            today = datetime.date.today()
            # Считаем КОЛИЧЕСТВО операций, а не сумму
            today_count = conn.execute("""
                SELECT COUNT(*) as cnt
                FROM bonus_transactions
                WHERE user_id = ? AND reason = ? AND DATE(created_at) = ?
            """, (user_id, reason, today)).fetchone()
            
            if today_count['cnt'] >= max_per_day:
                conn.close()
                return False
        
        # Начисляем баллы
        conn.execute(
            "UPDATE users SET bonus_points = bonus_points + ? WHERE id = ?",
            (points, user_id)
        )
        conn.execute(
            "INSERT INTO bonus_transactions (user_id, amount, reason) VALUES (?, ?, ?)",
            (user_id, points, reason)
        )
        conn.commit()
        conn.close()
        
        # АВТОМАТИЧЕСКАЯ ПРОВЕРКА ДОСТИЖЕНИЙ
        from app.services.achievement_service import AchievementService
        AchievementService.check_and_update_achievements(user_id)
        
        return True
    
    @staticmethod
    def claim_daily_bonus(user_id):
        """Ежедневный бонус с учётом стрейка + проверка достижений"""
        conn = get_db()
        today = datetime.date.today()
        
        # Проверяем, получал ли бонус сегодня
        last_bonus = conn.execute(
            "SELECT last_claim_date, streak FROM daily_bonus WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        
        if last_bonus:
            last_date = datetime.datetime.strptime(last_bonus['last_claim_date'], '%Y-%m-%d').date()
            if last_date == today:
                conn.close()
                return {"success": False, "error": "Сегодня вы уже получили бонус"}
            
            # Обновляем стрейк
            if last_date == today - datetime.timedelta(days=1):
                streak = last_bonus['streak'] + 1
            else:
                streak = 1
        else:
            streak = 1
        
        # Бонус увеличивается со стрейком (макс 50)
        bonus_amount = 10 + (streak // 7) * 5
        bonus_amount = min(bonus_amount, 50)
        
        # Сохраняем стрейк
        conn.execute(
            "INSERT OR REPLACE INTO daily_bonus (user_id, last_claim_date, streak) VALUES (?, ?, ?)",
            (user_id, today, streak)
        )
        
        # Начисляем баллы
        conn.execute(
            "UPDATE users SET bonus_points = bonus_points + ? WHERE id = ?",
            (bonus_amount, user_id)
        )
        conn.execute(
            "INSERT INTO bonus_transactions (user_id, amount, reason) VALUES (?, ?, ?)",
            (user_id, bonus_amount, f'Ежедневный бонус (стрик: {streak} дней)')
        )
        conn.commit()
        conn.close()
        
        # АВТОМАТИЧЕСКАЯ ПРОВЕРКА ДОСТИЖЕНИЙ (streak_7, streak_30, perfect_month)
        from app.services.achievement_service import AchievementService
        AchievementService.check_and_update_achievements(user_id)
        
        return {
            "success": True,
            "bonus": bonus_amount,
            "streak": streak,
            "message": f"Вы получили {bonus_amount} баллов! Стрик: {streak} дней"
        }
    
    @staticmethod
    def get_user_points(user_id):
        """Получить текущие баллы пользователя"""
        conn = get_db()
        result = conn.execute(
            "SELECT bonus_points FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        conn.close()
        return result['bonus_points'] if result else 0