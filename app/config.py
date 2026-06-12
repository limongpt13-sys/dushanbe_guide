import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-key-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # ИСПРАВЛЕНО: разрешаем все источники для разработки
    CORS_ORIGINS = ["*"]  # Для продакшена замените на конкретные домены
    
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB
    RATELIMIT_REQUESTS = 100
    RATELIMIT_PERIOD = 60  # seconds