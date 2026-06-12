from functools import wraps
from flask import request, jsonify
import jwt
import os
from datetime import datetime

def token_required(f):
    """Декоратор для проверки JWT токена"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({"error": "Токен отсутствует"}), 401
        
        try:
            token = auth_header.split(' ')[1]
            payload = jwt.decode(token, os.getenv('JWT_SECRET_KEY'), algorithms=['HS256'])
            request.user_id = payload['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Токен истёк"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Недействительный токен"}), 401
        except Exception:
            return jsonify({"error": "Ошибка авторизации"}), 401
        
        return f(*args, **kwargs)
    return decorated

def rate_limit(limit=100, period=60):
    """Декоратор для ограничения запросов (простая версия)"""
    requests = {}
    
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user_id = getattr(request, 'user_id', 'anonymous')
            now = datetime.now().timestamp()
            
            if user_id not in requests:
                requests[user_id] = []
            
            # Очищаем старые запросы
            requests[user_id] = [t for t in requests[user_id] if now - t < period]
            
            if len(requests[user_id]) >= limit:
                return jsonify({"error": f"Слишком много запросов. Лимит: {limit} за {period} сек"}), 429
            
            requests[user_id].append(now)
            return f(*args, **kwargs)
        return decorated
    return decorator