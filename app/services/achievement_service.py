import datetime
from app.models import get_db

class AchievementService:
    @staticmethod
    def _get_or_create_user_achievement(user_id, achievement_id, conn):
        """Получает запись о достижении или создаёт новую"""
        row = conn.execute(
            "SELECT * FROM user_achievements WHERE user_id = ? AND achievement_id = ?",
            (user_id, achievement_id)
        ).fetchone()
        if not row:
            conn.execute(
                "INSERT INTO user_achievements (user_id, achievement_id, progress, is_unlocked) VALUES (?, ?, ?, ?)",
                (user_id, achievement_id, 0, 0)
            )
            return {'progress': 0, 'is_unlocked': 0}
        return row
    
    @staticmethod
    def check_and_unlock(user_id, conn):
        """Проверяет все достижения и разблокирует при выполнении условий"""
        
        # 1. Получаем статистику пользователя
        stats = {}
        stats['msg_count'] = conn.execute(
            "SELECT COUNT(*) as cnt FROM chat_history WHERE user_id = ? AND sender = 'user'",
            (user_id,)
        ).fetchone()['cnt']
        
        stats['scan_count'] = conn.execute(
            "SELECT COUNT(*) as cnt FROM scan_history WHERE user_id = ?",
            (user_id,)
        ).fetchone()['cnt']
        
        stats['unique_places'] = conn.execute(
            "SELECT COUNT(DISTINCT result) as cnt FROM scan_history WHERE user_id = ?",
            (user_id,)
        ).fetchone()['cnt']
        
        streak_row = conn.execute(
            "SELECT COALESCE(streak, 0) as streak FROM daily_bonus WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        stats['streak'] = streak_row['streak'] if streak_row else 0
        
        stats['somoni_msg'] = conn.execute(
            "SELECT COUNT(*) as cnt FROM chat_history WHERE user_id = ? AND character_id = 'somoni' AND sender = 'user'",
            (user_id,)
        ).fetchone()['cnt']
        
        stats['rudaki_msg'] = conn.execute(
            "SELECT COUNT(*) as cnt FROM chat_history WHERE user_id = ? AND character_id = 'rudaki' AND sender = 'user'",
            (user_id,)
        ).fetchone()['cnt']
        
        stats['perfect_month'] = 1 if (stats['streak'] >= 30 and stats['msg_count'] >= 100) else 0
        
        # 2. Получаем все достижения из списка
        achievements = conn.execute("SELECT * FROM achievements_list").fetchall()
        
        # 3. Проверяем каждое достижение
        for ach in achievements:
            ach_id = ach['id']
            required = ach['required_value']
            
            # Определяем текущее значение
            if ach_id == 'first_chat':
                current = stats['msg_count']
            elif ach_id == 'first_scan':
                current = stats['scan_count']
            elif ach_id == 'chat_master':
                current = stats['msg_count']
            elif ach_id == 'photo_expert':
                current = stats['scan_count']
            elif ach_id == 'streak_7':
                current = stats['streak']
            elif ach_id == 'streak_30':
                current = stats['streak']
            elif ach_id == 'somoni_expert':
                current = stats['somoni_msg']
            elif ach_id == 'rudaki_expert':
                current = stats['rudaki_msg']
            elif ach_id == 'all_places':
                current = stats['unique_places']
            elif ach_id == 'perfect_month':
                current = stats['perfect_month']
            else:
                current = 0
            
            progress = min(current, required)
            is_unlocked = current >= required
            
            user_ach = AchievementService._get_or_create_user_achievement(user_id, ach_id, conn)
            
            # 4. Если достижение только что разблокировано — начисляем баллы
            if not user_ach['is_unlocked'] and is_unlocked:
                conn.execute(
                    "UPDATE users SET bonus_points = bonus_points + ? WHERE id = ?",
                    (ach['points_reward'], user_id)
                )
                conn.execute(
                    "INSERT INTO bonus_transactions (user_id, amount, reason) VALUES (?, ?, ?)",
                    (user_id, ach['points_reward'], f'Достижение: {ach["title"]}')
                )
                conn.execute(
                    "UPDATE user_achievements SET progress = ?, is_unlocked = ?, unlocked_at = ? "
                    "WHERE user_id = ? AND achievement_id = ?",
                    (progress, 1, datetime.datetime.now(), user_id, ach_id)
                )
            # 5. Если прогресс изменился — обновляем
            elif user_ach['progress'] < progress:
                conn.execute(
                    "UPDATE user_achievements SET progress = ? WHERE user_id = ? AND achievement_id = ?",
                    (progress, user_id, ach_id)
                )