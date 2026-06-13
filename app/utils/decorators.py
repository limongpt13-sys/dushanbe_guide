from functools import wraps
from flask import request, jsonify, current_app
import jwt
import datetime

def token_required(f):
    """Декоратор для проверки JWT токена"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({"error": "Токен отсутствует"}), 401
        
        try:
            token = auth_header.split(' ')[1] if ' ' in auth_header else auth_header
            secret = current_app.config.get('JWT_SECRET_KEY') or 'dev-jwt-key-secure-2026'
            
            payload = jwt.decode(token, secret, algorithms=['HS256'])
            request.user_id = payload['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Токен истёк, авторизуйтесь заново"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Недействительный токен"}), 401
        except Exception as e:
            print(f"🛑 Auth error: {str(e)}")
            return jsonify({"error": "Ошибка авторизации"}), 401
        
        return f(*args, **kwargs)
    return decorated

def rate_limit(limit=100, period=60):
    """Безопасный ограничитель запросов (Memory Leak Safe)"""
    requests_store = {}
    
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user_id = getattr(request, 'user_id', request.remote_addr or 'anonymous')
            now = datetime.datetime.now(datetime.timezone.utc).timestamp()
            
            # Очистка памяти от неактивных пользователей
            expired_keys = []
            for uid, timestamps in requests_store.items():
                valid_timestamps = [t for t in timestamps if now - t < period]
                if not valid_timestamps:
                    expired_keys.append(uid)
                else:
                    requests_store[uid] = valid_timestamps
            
            for key in expired_keys:
                requests_store.pop(key, None)
            
            if user_id not in requests_store:
                requests_store[user_id] = []
            
            if len(requests_store[user_id]) >= limit:
                return jsonify({"error": f"Слишком много запросов. Лимит: {limit} за {period} сек"}), 429
            
            requests_store[user_id].append(now)
            return f(*args, **kwargs)
        return decorated
    return decorator
