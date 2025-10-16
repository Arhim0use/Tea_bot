"""
Вспомогательные функции для бота.
"""

from random import randint, choice
from typing import Optional
from aiogram.types import User, Message
import os


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

def get_random_teamoji() -> str:
    """
    Возвращает случайный эмодзи чая.
    """
    teamojies = ["🍵", "🫖", "🌱", "🍃", "🍯", "🍫", "🍪", " "]
    return teamojies[randint(0, len(teamojies) - 1)]

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
        return f'{get_random_teamoji()} {get_random_teamoji()} Чай. "{custom_text}"\nby {username}'
    return f"{get_random_teamoji()} {get_random_teamoji()} Чай {get_random_teamoji()} {get_random_teamoji()}\nby {username}"


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


def get_random_quotation() -> str:
    """
    Возвращает случайную цитату из файла quotation.txt.
    
    Returns:
        str: Случайная цитата
    """
    try:
        # Путь к файлу цитат относительно корня проекта
        quotation_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "quotation.txt")
        
        if not os.path.exists(quotation_file):
            return "Цитаты временно недоступны. 🍵"
        
        with open(quotation_file, 'r', encoding='utf-8') as f:
            quotations = [line.strip() for line in f.readlines() if line.strip()]
        
        if not quotations:
            return "Цитаты временно недоступны. 🍵"
        
        return choice(quotations)
    
    except Exception:
        return "Цитаты временно недоступны. 🍵"


def format_quote_caption(username: str, custom_text: Optional[str] = None) -> str:
    """
    Форматирует подпись для публикации цитаты в канале.
    
    Args:
        username: Имя пользователя
        custom_text: Дополнительный текст пользователя (игнорируется для цитат)
    
    Returns:
        str: Отформатированная подпись с цитатой
    """
    quotation = get_random_quotation()
    return f'{get_random_teamoji()} {get_random_teamoji()} Цитата {get_random_teamoji()} {get_random_teamoji()}\n\n{quotation}\n\nby {username}'

