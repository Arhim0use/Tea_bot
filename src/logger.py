"""
Модуль для настройки логирования.
Обеспечивает запись логов в файл и вывод в консоль.
"""

import logging
import sys
from pathlib import Path
from src.config import config


def setup_logger() -> logging.Logger:
    """
    Настраивает и возвращает логгер для бота.
    
    Returns:
        logging.Logger: Настроенный логгер
    """
    # Создаем логгер
    logger = logging.getLogger("TeaBot")
    logger.setLevel(logging.INFO)
    
    # Если логирование отключено, возвращаем логгер без хендлеров
    if not config.ENABLE_LOGGING:
        # Добавляем NullHandler чтобы избежать ошибок
        logger.addHandler(logging.NullHandler())
        return logger
    
    # Создаем директорию для логов если её нет
    log_path = Path(config.LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Форматтер для логов
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Хендлер для записи в файл
    file_handler = logging.FileHandler(
        config.LOG_FILE,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # Хендлер для вывода в консоль
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Добавляем хендлеры к логгеру
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


# Создаем глобальный экземпляр логгера
logger = setup_logger()

