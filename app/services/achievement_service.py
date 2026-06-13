import datetime
from app.models import get_db

class AchievementService:
    @staticmethod
    def check_and_update_achievements(user_id):
        """Проверяет все ачивки и начисляет супер-бонусы в реальном времени"""
        conn = get_db()
        cursor = conn.cursor()
        
        msg_count = cursor.execute("SELECT COUNT(*) FROM chat_history WHERE user_id = ? AND sender = 'user'", (user_id,)).fetchone()[0]
        scan_count = cursor.execute("SELECT COUNT(*) FROM scan_history WHERE user_id = ?", (user_id,)).fetchone()[0]
        unique_places = cursor.execute("SELECT COUNT(DISTINCT result) FROM scan_history WHERE user_id = ?", (user_id,)).fetchone()[0]
        
        streak_row = cursor.execute("SELECT COALESCE(streak, 0) FROM daily_bonus WHERE user_id = ?", (user_id,)).fetchone()
        streak = streak_row[0] if streak_row else 0
        
        somoni_msg = cursor.execute("SELECT COUNT(*) FROM chat_history WHERE user_id = ? AND character_id = 'somoni' AND sender = 'user'", (user_id,)).fetchone()[0]
        rudaki_msg = cursor.execute("SELECT COUNT(*) FROM chat_history WHERE user_id = ? AND character_id = 'rudaki' AND sender = 'user'", (user_id,)).fetchone()[0]
        
        perfect_month = 1 if (streak >= 30 and msg_count >= 100) else 0
        
        unlocked = {}
        unlocked_rows = cursor.execute("SELECT achievement_id, progress, is_unlocked FROM user_achievements WHERE user_id = ?", (user_id,)).fetchall()
        for row in unlocked_rows:
            unlocked[row['achievement_id']] = {'progress': row['progress'], 'is_unlocked': row['is_unlocked']}
            
        all_achievements = cursor.execute("SELECT * FROM achievements_list").fetchall()
        newly_unlocked = []
        
        for ach in all_achievements:
            ach_id = ach['id']
            required = ach['required_value']
            
            if ach_id in ['first_chat', 'chat_master']: progress = min(msg_count, required)
            elif ach_id in ['first_scan', 'photo_expert']: progress = min(scan_count, required)
            elif ach_id in ['streak_7', 'streak_30']: progress = min(streak, required)
            elif ach_id == 'somoni_expert': progress = min(somoni_msg, required)
            elif ach_id == 'rudaki_expert': progress = min(rudaki_msg, required)
            elif ach_id == 'all_places': progress = min(unique_places, required)
            elif ach_id == 'perfect_month': progress = 1 if perfect_month else 0
            else: progress = 0
                
            is_unlocked = progress >= required if ach_id != 'perfect_month' else perfect_month == 1
            
            if ach_id in unlocked:
                if not unlocked[ach_id]['is_unlocked'] and is_unlocked:
                    cursor.execute("UPDATE users SET bonus_points = bonus_points + ? WHERE id = ?", (ach['points_reward'], user_id))
                    cursor.execute("INSERT INTO bonus_transactions (user_id, amount, reason) VALUES (?, ?, ?)", (user_id, ach['points_reward'], f'Достижение: {ach["title"]}'))
                    cursor.execute("UPDATE user_achievements SET progress = ?, is_unlocked = 1, unlocked_at = ? WHERE user_id = ? AND achievement_id = ?", (progress, datetime.datetime.now(), user_id, ach_id))
                    newly_unlocked.append(ach['title'])
                else:
                    cursor.execute("UPDATE user_achievements SET progress = ? WHERE user_id = ? AND achievement_id = ?", (progress, user_id, ach_id))
            else:
                cursor.execute("INSERT INTO user_achievements (user_id, achievement_id, progress, is_unlocked, unlocked_at) VALUES (?, ?, ?, ?, ?)", (user_id, ach_id, progress, 1 if is_unlocked else 0, datetime.datetime.now() if is_unlocked else None))
                if is_unlocked:
                    cursor.execute("UPDATE users SET bonus_points = bonus_points + ? WHERE id = ?", (ach['points_reward'], user_id))
                    cursor.execute("INSERT INTO bonus_transactions (user_id, amount, reason) VALUES (?, ?, ?)", (user_id, ach['points_reward'], f'Достижение: {ach["title"]}'))
                    newly_unlocked.append(ach['title'])
                    
        conn.commit()
        conn.close()
        return newly_unlocked
