import re

def validate_email(email):
    """Проверяет корректность email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Проверяет сложность пароля"""
    if len(password) < 6:
        return False, "Пароль должен быть минимум 6 символов"
    if not any(c.isupper() for c in password):
        return False, "Пароль должен содержать хотя бы одну заглавную букву"
    if not any(c.isdigit() for c in password):
        return False, "Пароль должен содержать хотя бы одну цифру"
    return True, "OK"

def validate_username(username):
    """Проверяет логин (только буквы, цифры, подчёркивание)"""
    if len(username) < 3:
        return False, "Логин должен быть минимум 3 символа"
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Логин может содержать только буквы, цифры и подчёркивание"
    return True, "OK"

def validate_full_name(name):
    """Проверяет ФИО"""
    if len(name) < 2:
        return False, "Имя должно быть минимум 2 символа"
    return True, "OK"

def sanitize_input(text):
    """Очищает ввод от потенциально опасных символов"""
    # Удаляем HTML теги
    text = re.sub(r'<[^>]+>', '', text)
    # Ограничиваем длину
    if len(text) > 1000:
        text = text[:1000]
    return text.strip()