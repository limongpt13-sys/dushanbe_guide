import os
import base64
import hashlib
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

_chat_cache = {}
_scan_cache = {}

class AIService:
    @staticmethod
    def _get_chat_cache_key(prompt, message, history):
        normalized = []
        if history:
            for msg in history:
                normalized.append({
                    "role": msg.get("role", msg.get("sender", "user")),
                    "content": msg.get("content", msg.get("message", ""))
                })
        content = f"{prompt}|{message}|{json.dumps(normalized, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    @staticmethod
    def _get_scan_cache_key(image_bytes):
        return hashlib.md5(image_bytes).hexdigest()

    @staticmethod
    def chat_with_character(system_prompt, user_message, history=None):
        if not client:
            return "⚠️ Сервис AI временно недоступен."
        
        cache_key = AIService._get_chat_cache_key(system_prompt, user_message, history)
        if cache_key in _chat_cache:
            return _chat_cache[cache_key]
        
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for msg in history[-10:]:
                raw_role = msg.get('role', msg.get('sender', 'user'))
                role = "user" if raw_role == 'user' else "assistant"
                content = msg.get('content', msg.get('message', ''))
                messages.append({"role": role, "content": content})
                
        messages.append({"role": "user", "content": user_message})
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )
            result = response.choices[0].message.content
            _chat_cache[cache_key] = result
            return result
        except Exception as e:
            return f"❌ Ошибка AI: {str(e)}"
    
    @staticmethod
    def recognize_landmark(image_bytes):
        if not client:
            return "⚠️ Сервис распознавания временно недоступен"
        
        scan_key = AIService._get_scan_cache_key(image_bytes)
        if scan_key in _scan_cache:
            return _scan_cache[scan_key]
            
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        prompt = """Ты — эксперт-экскурсовод по Душанбе и Таджикистану.
Определи достопримечательность на фото и дай интересную историческую справку.
Если объект не из Душанбе/Таджикистана — вежливо сообщи об этом.
Формат ответа: 📍 Название места\n📖 Историческая справка\n✨ Интересный факт"""
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                    ]
                }],
                max_tokens=600
            )
            result = response.choices[0].message.content
            _scan_cache[scan_key] = result
            return result
        except Exception as e:
            return f"❌ Ошибка распознавания: {str(e)}"
