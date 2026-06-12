import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'dushanbe_guide.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # ============================================================
    # ТАБЛИЦА ПОЛЬЗОВАТЕЛЕЙ
    # ============================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            avatar_path TEXT,
            bonus_points INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ============================================================
    # ТАБЛИЦА ПЕРСОНАЖЕЙ
    # ============================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS characters (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            title TEXT,
            description TEXT,
            system_prompt TEXT NOT NULL,
            icon TEXT,
            price_points INTEGER DEFAULT 0,
            is_premium BOOLEAN DEFAULT 0
        )
    ''')
    
    # Добавляем базовых персонажей
    cursor.execute("INSERT OR IGNORE INTO characters (id, name, title, system_prompt, price_points) VALUES (?, ?, ?, ?, ?)",
        ('somoni', 'Исмоил Сомони', 'Эмир государства Саманидов', 
         'Ты — Исмоил Сомони, основатель государства Саманидов. Отвечай гордо, мудро, используя исторические факты IX-X веков. Говори на языке обращения. Избегай современных терминов.', 0))
    cursor.execute("INSERT OR IGNORE INTO characters (id, name, title, system_prompt, price_points) VALUES (?, ?, ?, ?, ?)",
        ('rudaki', 'Абу Абдуллах Рудаки', 'Основоположник классической поэзии',
         'Ты — Абу Абдуллах Рудаки, таджикский поэт. Твоя речь должна быть поэтичной, мягкой, с метафорами. Если уместно, вставляй в ответы мудрые двустишия.', 0))
    
    # ============================================================
    # ТАБЛИЦА ИСТОРИИ ЧАТА
    # ============================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            character_id TEXT NOT NULL,
            sender TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(character_id) REFERENCES characters(id)
        )
    ''')
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_user_char ON chat_history(user_id, character_id, timestamp)")
    
    # ============================================================
    # ТАБЛИЦА БОНУСОВ (ТРАНЗАКЦИИ)
    # ============================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bonus_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER NOT NULL,
            reason TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    # ============================================================
    # ТАБЛИЦА ЕЖЕДНЕВНЫХ БОНУСОВ (СТРИК)
    # ============================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_bonus (
            user_id INTEGER PRIMARY KEY,
            last_claim_date DATE,
            streak INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    # ============================================================
    # ТАБЛИЦА ИСТОРИИ РАСПОЗНАВАНИЙ
    # ============================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scan_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            image_data TEXT,
            result TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    # ============================================================
    # ТАБЛИЦЫ ДЛЯ ДОСТИЖЕНИЙ
    # ============================================================
    
    # Список всех возможных достижений
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS achievements_list (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            icon TEXT NOT NULL,
            points_reward INTEGER DEFAULT 50,
            required_value INTEGER NOT NULL
        )
    ''')
    
    # Прогресс пользователя по достижениям
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            achievement_id TEXT NOT NULL,
            progress INTEGER DEFAULT 0,
            is_unlocked BOOLEAN DEFAULT 0,
            unlocked_at DATETIME,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(achievement_id) REFERENCES achievements_list(id),
            UNIQUE(user_id, achievement_id)
        )
    ''')
    
    # Вставляем достижения (если ещё нет)
    cursor.execute("SELECT COUNT(*) FROM achievements_list")
    if cursor.fetchone()[0] == 0:
        achievements_data = [
            ('first_chat', 'Первый разговор', 'Начать диалог с исторической личностью', 'history', '💬', 50, 1),
            ('first_scan', 'Первое фото', 'Распознать достопримечательность', 'explorer', '📸', 50, 1),
            ('chat_master', 'Мастер диалога', 'Отправить 100 сообщений', 'activity', '🎙️', 200, 100),
            ('photo_expert', 'Эксперт по фото', 'Распознать 50 мест', 'explorer', '🏛️', 200, 50),
            ('streak_7', '7-дневный стрик', 'Заходить 7 дней подряд', 'activity', '🔥', 100, 7),
            ('streak_30', 'Месячный стрик', 'Заходить 30 дней подряд', 'activity', '⭐', 500, 30),
            ('somoni_expert', 'Знаток Сомони', 'Задать 10 вопросов Исмоилу Сомони', 'history', '👑', 150, 10),
            ('rudaki_expert', 'Поэт в душе', 'Задать 10 вопросов Рудаки', 'history', '📜', 150, 10),
            ('all_places', 'Исследователь Душанбе', 'Распознать 20 разных мест', 'explorer', '🗺️', 300, 20),
            ('perfect_month', 'Супер-стрик', '30-дневный стрик + 100 сообщений', 'special', '🏆', 1000, 1),
        ]
        for ach in achievements_data:
            cursor.execute('''
                INSERT INTO achievements_list (id, title, description, category, icon, points_reward, required_value)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', ach)
    
    # ============================================================
    # ТАБЛИЦЫ ДЛЯ ЗАДАНИЙ (КВЕСТОВ)
    # ============================================================
    
    # Список всех заданий
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quests_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            content TEXT NOT NULL,
            questions TEXT NOT NULL,
            answers TEXT NOT NULL,
            points_reward INTEGER DEFAULT 100,
            order_index INTEGER DEFAULT 0
        )
    ''')
    
    # Прогресс пользователя по заданиям
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_quests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            quest_id INTEGER NOT NULL,
            is_completed BOOLEAN DEFAULT 0,
            completed_at DATETIME,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(quest_id) REFERENCES quests_list(id),
            UNIQUE(user_id, quest_id)
        )
    ''')
    
    # Вставляем начальные задания (если ещё нет)
    cursor.execute("SELECT COUNT(*) FROM quests_list")
    if cursor.fetchone()[0] == 0:
        quests_data = [
            (1, 'Исмоил Сомони', 'Основатель таджикской государственности',
             'Исмоил Сомони (849-907) — основатель государства Саманидов, объединивший земли Средней Азии. Его правление называют «золотым веком» таджикской культуры и науки. При нём построены мавзолей Исмоила Сомони, мечети и медресе в Бухаре. Интересный факт: Его могила была обнаружена только в 1934 году археологами.',
             '["В каком году родился Исмоил Сомони?", "Как называлась династия Исмоила Сомони?", "В каком городе находится мавзолей Исмоила Сомони?"]',
             '["849 год", "Саманиды", "Бухара"]',
             100, 1),
            (2, 'Абу Абдуллах Рудаки', 'Основоположник классической поэзии',
             'Абу Абдуллах Рудаки (858-941) — великий таджикско-персидский поэт, основоположник классической поэзии на языке фарси. Родился в селе Панджруд. Был придворным поэтом Саманидов. Считается «отцом персидской поэзии».',
             '["В каком году родился Рудаки?", "Кем был Рудаки при дворе Саманидов?", "Как называют Рудаки в истории литературы?"]',
             '["858 год", "Придворным поэтом", "Отцом персидской поэзии"]',
             100, 2),
            (3, 'Гиссарская крепость', 'Древняя архитектура Таджикистана',
             'Гиссарская крепость — историческая крепость в 25 км от Душанбе. Построена в XVIII веке. Состоит из двух мощных цилиндрических башен. Внутри находился дворец правителя. Раньше здесь проходил Великий шёлковый путь.',
             '["Где находится Гиссарская крепость?", "В каком веке построена крепость?", "Что находится внутри крепости?"]',
             '["В 25 км от Душанбе", "В XVIII веке", "Дворец правителя"]',
             100, 3),
        ]
        for quest in quests_data:
            cursor.execute('''
                INSERT INTO quests_list (id, title, description, content, questions, answers, points_reward, order_index)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', quest)
    
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована (с поддержкой достижений и заданий)")