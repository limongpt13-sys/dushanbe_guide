import re

def validate_email(email):
    """Проверяет корректность email"""
    if not email:
        return False, "Email не может быть пустым"
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(pattern, email):
        return True, "OK"
    return False, "Неверный формат email адреса"

def validate_password(password):
    """Проверяет сложность пароля"""
    if not password:
        return False, "Пароль не может быть пустым"
    if len(password) < 6:
        return False, "Пароль должен быть минимум 6 символов"
    if not any(c.isupper() for c in password):
        return False, "Пароль должен содержать хотя бы одну заглавную букву"
    if not any(c.isdigit() for c in password):
        return False, "Пароль должен содержать хотя бы одну цифру"
    return True, "OK"

def validate_username(username):
    """Проверяет логин (только латиница, цифры, подчёркивание)"""
    if not username:
        return False, "Логин не может быть пустым"
    if len(username) < 3:
        return False, "Логин должен быть минимум 3 символа"
    if len(username) > 30:
        return False, "Логин слишком длинный"
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Логин может содержать только латинские буквы, цифры и подчёркивание"
    return True, "OK"

def validate_full_name(name):
    """Проверяет ФИО (с поддержкой кириллицы и дефисов)"""
    if not name:
        return False, "Имя не может быть пустым"
    cleaned_name = name.strip()
    if len(cleaned_name) < 2:
        return False, "Имя должно быть минимум 2 символа"
    if not re.match(r'^[a-zA-Zа-яА-ЯёЁ\s\-]+$', cleaned_name):
        return False, "Имя может содержать только буквы, пробелы и дефис"
    return True, "OK"

def sanitize_input(text):
    """Очищает ввод от HTML тегов и ограничивает длину"""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    if len(text) > 1000:
        text = text[:1000]
    return text.strip()
