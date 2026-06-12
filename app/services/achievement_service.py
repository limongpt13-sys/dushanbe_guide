from app.models import get_db
import datetime

class AchievementService:
    @staticmethod
    def check_and_update_achievements(user_id):
        """Проверяет все достижения, начисляет награды и обновляет прогресс"""
        conn = get_db()
        
        # ===== СБОР СТАТИСТИКИ ПОЛЬЗОВАТЕЛЯ =====
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
        
        # ===== ПОЛУЧАЕМ ВСЕ ДОСТИЖЕНИЯ =====
        all_achievements = conn.execute("SELECT * FROM achievements_list").fetchall()
        
        for ach in all_achievements:
            ach_id = ach['id']
            required = ach['required_value']
            
            # Определяем текущее значение прогресса
            if ach_id == 'first_chat':
                value = msg_count
            elif ach_id == 'first_scan':
                value = scan_count
            elif ach_id == 'chat_master':
                value = msg_count
            elif ach_id == 'photo_expert':
                value = scan_count
            elif ach_id == 'streak_7':
                value = streak
            elif ach_id == 'streak_30':
                value = streak
            elif ach_id == 'somoni_expert':
                value = somoni_msg
            elif ach_id == 'rudaki_expert':
                value = rudaki_msg
            elif ach_id == 'all_places':
                value = unique_places
            elif ach_id == 'perfect_month':
                value = perfect_month
                required = 1
            else:
                continue
            
            progress = min(value, required)
            is_unlocked = value >= required
            
            # Проверяем существующую запись
            existing = conn.execute(
                "SELECT is_unlocked FROM user_achievements WHERE user_id = ? AND achievement_id = ?",
                (user_id, ach_id)
            ).fetchone()
            
            if existing:
                # Если достижение НЕ было разблокировано, а сейчас разблокировалось
                if not existing['is_unlocked'] and is_unlocked:
                    # Начисляем баллы за достижение
                    conn.execute(
                        "UPDATE users SET bonus_points = bonus_points + ? WHERE id = ?",
                        (ach['points_reward'], user_id)
                    )
                    conn.execute(
                        "INSERT INTO bonus_transactions (user_id, amount, reason) VALUES (?, ?, ?)",
                        (user_id, ach['points_reward'], f'Достижение: {ach["title"]}')
                    )
                    conn.execute(
                        "UPDATE user_achievements SET progress = ?, is_unlocked = ?, unlocked_at = ? WHERE user_id = ? AND achievement_id = ?",
                        (progress, 1, datetime.datetime.now(), user_id, ach_id)
                    )
                else:
                    # Просто обновляем прогресс
                    conn.execute(
                        "UPDATE user_achievements SET progress = ? WHERE user_id = ? AND achievement_id = ?",
                        (progress, user_id, ach_id)
                    )
            else:
                # Создаём запись о достижении
                conn.execute(
                    "INSERT INTO user_achievements (user_id, achievement_id, progress, is_unlocked) VALUES (?, ?, ?, ?)",
                    (user_id, ach_id, progress, 1 if is_unlocked else 0)
                )
                # Если сразу разблокировано (например, first_chat = 1), начисляем баллы
                if is_unlocked:
                    conn.execute(
                        "UPDATE users SET bonus_points = bonus_points + ? WHERE id = ?",
                        (ach['points_reward'], user_id)
                    )
                    conn.execute(
                        "INSERT INTO bonus_transactions (user_id, amount, reason) VALUES (?, ?, ?)",
                        (user_id, ach['points_reward'], f'Достижение: {ach["title"]}')
                    )
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_user_achievements_with_progress(user_id):
        """Возвращает все достижения с прогрессом пользователя (для API)"""
        conn = get_db()
        
        # Сначала обновляем все достижения (чтобы данные были свежими)
        AchievementService.check_and_update_achievements(user_id)
        
        # Получаем достижения с прогрессом
        rows = conn.execute("""
            SELECT 
                al.id, al.title, al.description, al.category, al.icon, 
                al.points_reward, al.required_value,
                COALESCE(ua.progress, 0) as progress,
                COALESCE(ua.is_unlocked, 0) as is_unlocked,
                ua.unlocked_at
            FROM achievements_list al
            LEFT JOIN user_achievements ua ON al.id = ua.achievement_id AND ua.user_id = ?
            ORDER BY al.id
        """, (user_id,)).fetchall()
        
        conn.close()
        
        achievements = []
        for row in rows:
            achievements.append({
                'id': row['id'],
                'title': row['title'],
                'description': row['description'],
                'category': row['category'],
                'icon': row['icon'],
                'points_reward': row['points_reward'],
                'required_value': row['required_value'],
                'progress': row['progress'],
                'is_unlocked': bool(row['is_unlocked']),
                'unlocked_at': row['unlocked_at']
            })
        
        return achievements