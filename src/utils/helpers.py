"""
Вспомогательные функции для бота.
"""

from typing import Optional
from aiogram.types import User, Message


def get_user_display_name(user: User) -> str:
    """
    Возвращает отображаемое имя пользователя.
    Приоритет: username > first_name + last_name > "Anonymous"
    
    Args:
        user: Объект пользователя Telegram
    
    Returns:
        str: Отображаемое имя пользователя
    """
    if user.username:
        return f"@{user.username}"
    
    # Если нет username, пробуем получить имя и фамилию
    name_parts = []
    if user.first_name:
        name_parts.append(user.first_name)
    if user.last_name:
        name_parts.append(user.last_name)
    
    if name_parts:
        return " ".join(name_parts)
    
    # Если нет ни username, ни имени
    return "Anonymous"


def extract_custom_text(message: Message) -> Optional[str]:
    """
    Извлекает пользовательский текст из сообщения с командой /tea.
    Удаляет команду /tea из начала текста.
    
    Args:
        message: Объект сообщения
    
    Returns:
        Optional[str]: Текст без команды или None
    """
    # Проверяем caption (для медиа)
    text = message.caption if message.caption else message.text
    
    if not text:
        return None
    
    # Удаляем команду /tea из начала
    text = text.strip()
    if text.lower().startswith("/tea"):
        text = text[4:].strip()
    
    # Если после удаления команды остался текст, возвращаем его
    return text if text else None


def format_tea_caption(username: str, custom_text: Optional[str] = None) -> str:
    """
    Форматирует подпись для публикации в канале.
    
    Args:
        username: Имя пользователя
        custom_text: Дополнительный текст пользователя
    
    Returns:
        str: Отформатированная подпись
    """
    if custom_text:
        return f'Чай. "{custom_text}" by {username}'
    return f"Чай by {username}"


def get_message_type(message: Message) -> str:
    """
    Определяет тип сообщения.
    
    Args:
        message: Объект сообщения
    
    Returns:
        str: Тип сообщения (text, photo, video, video_note)
    """
    if message.photo:
        return "photo"
    elif message.video:
        return "video"
    elif message.video_note:
        return "video_note"
    else:
        return "text"

