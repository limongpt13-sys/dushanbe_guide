import os
import base64
import hashlib
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)
else:
    client = None
    print("⚠️ OPENAI_API_KEY не задан")

# Простой кэш в памяти (замени на Redis при наличии)
_cache = {}

class AIService:
    @staticmethod
    def _get_cache_key(prompt, message, history):
        """Генерирует ключ для кэша"""
        content = f"{prompt}|{message}|{json.dumps(history)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    @staticmethod
    def chat_with_character(system_prompt, user_message, history=None):
        if not client:
            return "⚠️ Сервис AI временно недоступен. Попробуйте позже."
        
        cache_key = AIService._get_cache_key(system_prompt, user_message, history)
        
        # Проверяем кэш
        if cache_key in _cache:
            return _cache[cache_key]
        
        messages = [{"role": "system", "content": system_prompt}]
        
        if history:
            for msg in history[-10:]:  # Последние 10 сообщений
                role = "user" if msg['role'] == 'user' else "assistant"
                messages.append({"role": role, "content": msg['content']})
        
        messages.append({"role": "user", "content": user_message})
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )
            result = response.choices[0].message.content
            
            # Сохраняем в кэш (на 1 час)
            _cache[cache_key] = result
            return result
        except Exception as e:
            return f"❌ Ошибка AI: {str(e)}"
    
    @staticmethod
    def recognize_landmark(image_bytes):
        if not client:
            return "⚠️ Сервис распознавания временно недоступен"
        
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        
        prompt = """Ты — эксперт-экскурсовод по Душанбе и Таджикистану.
Определи достопримечательность на фото и дай интересную историческую справку.
Если объект не из Душанбе/Таджикистана — вежливо сообщи об этом.
Формат ответа: 📍 Название места\n📖 Историческая справка\n✨ Интересный факт"""
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                        ]
                    }
                ],
                max_tokens=600
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Ошибка распознавания: {str(e)}"