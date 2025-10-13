"""
Модуль для работы с базой данных SQLite.
Реализует паттерн Repository для работы с пересылками.
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import pytz
from src.config import config
from src.logger import logger


class ForwardsRepository:
    """Репозиторий для работы с таблицей пересылок."""
    
    def __init__(self, db_path: str):
        """
        Инициализирует репозиторий.
        
        Args:
            db_path: Путь к файлу базы данных
        """
        self.db_path = db_path
        self._init_db()
    
    @contextmanager
    def _get_connection(self):
        """
        Контекстный менеджер для работы с подключением к БД.
        
        Yields:
            sqlite3.Connection: Подключение к базе данных
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def _init_db(self) -> None:
        """Создает таблицу forwards если её нет."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS forwards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    datetime TIMESTAMP NOT NULL
                )
            """)
            logger.info("Database initialized successfully")
    
    def add_forward(
        self, 
        username: str, 
        message_type: str, 
        dt: Optional[datetime] = None
    ) -> int:
        """
        Добавляет новую запись о пересылке.
        
        Args:
            username: Имя пользователя
            message_type: Тип сообщения (text, photo, video, video_note)
            dt: Время пересылки (если None, используется текущее время)
        
        Returns:
            int: ID созданной записи
        """
        if dt is None:
            # Используем текущее время в указанной временной зоне
            tz = pytz.timezone(config.TIMEZONE)
            dt = datetime.now(tz)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO forwards (username, message_type, datetime) VALUES (?, ?, ?)",
                (username, message_type, dt)
            )
            record_id = cursor.lastrowid
            logger.info(f"Added forward record: user={username}, type={message_type}, id={record_id}")
            return record_id
    
    def get_today_count(self) -> int:
        """
        Возвращает количество пересылок с 04:00 текущих суток.
        
        Returns:
            int: Количество пересылок
        """
        tz = pytz.timezone(config.TIMEZONE)
        now = datetime.now(tz)
        
        # Определяем начало текущих "суток" (с 04:00)
        today_reset = now.replace(hour=config.RESET_HOUR, minute=0, second=0, microsecond=0)
        
        # Если текущее время раньше 04:00, берём вчерашние 04:00
        if now.hour < config.RESET_HOUR:
            today_reset -= timedelta(days=1)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) as count FROM forwards WHERE datetime >= ?",
                (today_reset,)
            )
            result = cursor.fetchone()
            count = result["count"] if result else 0
            return count
    
    def reset_today(self) -> int:
        """
        Удаляет все записи за текущие сутки (с 04:00).
        Используется для команды /reset.
        
        Returns:
            int: Количество удалённых записей
        """
        tz = pytz.timezone(config.TIMEZONE)
        now = datetime.now(tz)
        
        today_reset = now.replace(hour=config.RESET_HOUR, minute=0, second=0, microsecond=0)
        if now.hour < config.RESET_HOUR:
            today_reset -= timedelta(days=1)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM forwards WHERE datetime >= ?",
                (today_reset,)
            )
            deleted = cursor.rowcount
            logger.info(f"Reset today's forwards: {deleted} records deleted")
            return deleted
    
    def get_all_forwards(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Возвращает список всех пересылок (для отладки).
        
        Args:
            limit: Максимальное количество записей
        
        Returns:
            List[Dict]: Список пересылок
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM forwards ORDER BY datetime DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]


# Создаем глобальный экземпляр репозитория
db_repo = ForwardsRepository(config.DB_PATH)

