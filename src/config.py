"""
Модуль конфигурации бота.
Загружает переменные окружения из .env файла.
"""

import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()


class Config:
    """Класс для хранения конфигурации бота."""
    
    # Токен бота
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    
    # ID группы и канала
    GROUP_ID: int = int(os.getenv("GROUP_ID", "0"))
    CHANNEL_ID: int = int(os.getenv("CHANNEL_ID", "0"))
    
    # Администраторы (список ID через запятую)
    ADMINS: List[int] = [
        int(admin_id.strip()) 
        for admin_id in os.getenv("ADMINS", "").split(",") 
        if admin_id.strip()
    ]
    
    # Лимиты и настройки времени
    DAILY_LIMIT: int = int(os.getenv("DAILY_LIMIT", "5"))
    RESET_HOUR: int = int(os.getenv("RESET_HOUR", "4"))
    TIMEZONE: str = os.getenv("TIMEZONE", "Europe/Moscow")
    
    # Пути к файлам
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/teabot.log")
    DB_PATH: str = os.getenv("DB_PATH", "data/forwards.db")
    
    @classmethod
    def validate(cls) -> bool:
        """
        Проверяет, что все обязательные параметры заданы.
        
        Returns:
            bool: True если конфигурация валидна, иначе False
        """
        if not cls.BOT_TOKEN:
            print("❌ Ошибка: BOT_TOKEN не задан в .env")
            return False
        
        if cls.GROUP_ID == 0:
            print("❌ Ошибка: GROUP_ID не задан в .env")
            return False
        
        if cls.CHANNEL_ID == 0:
            print("❌ Ошибка: CHANNEL_ID не задан в .env")
            return False
        
        # Создаем директории если их нет
        Path(cls.LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
        Path(cls.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        
        return True


# Экспортируем экземпляр конфигурации
config = Config()

