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
        """Создает таблицы forwards и bans если их нет."""
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
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    banned_by INTEGER NOT NULL,
                    banned_by_username TEXT NOT NULL,
                    reason TEXT,
                    ban_until TIMESTAMP NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    is_active BOOLEAN DEFAULT 1
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
    
    def get_last_forward_time(self, username: str) -> Optional[datetime]:
        """
        Возвращает время последней пересылки пользователя.
        
        Args:
            username: Имя пользователя
        
        Returns:
            Optional[datetime]: Время последней пересылки или None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT datetime FROM forwards WHERE username = ? ORDER BY datetime DESC LIMIT 1",
                (username,)
            )
            result = cursor.fetchone()
            return result["datetime"] if result else None
    
    def add_ban(
        self,
        user_id: int,
        username: str,
        banned_by: int,
        banned_by_username: str,
        hours: int,
        reason: Optional[str] = None
    ) -> int:
        """
        Добавляет бан пользователя.
        
        Args:
            user_id: ID пользователя
            username: Имя пользователя
            banned_by: ID администратора
            banned_by_username: Имя администратора
            hours: Количество часов бана
            reason: Причина бана
        
        Returns:
            int: ID созданной записи
        """
        tz = pytz.timezone(config.TIMEZONE)
        now = datetime.now(tz)
        ban_until = now + timedelta(hours=hours)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO bans (user_id, username, banned_by, banned_by_username, reason, ban_until, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, username, banned_by, banned_by_username, reason, ban_until, now))
            record_id = cursor.lastrowid
            logger.info(f"Added ban record: user={username}, hours={hours}, id={record_id}")
            return record_id
    
    def is_user_banned(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Проверяет, забанен ли пользователь.
        
        Args:
            user_id: ID пользователя
        
        Returns:
            Optional[Dict]: Информация о бане или None если не забанен
        """
        tz = pytz.timezone(config.TIMEZONE)
        now = datetime.now(tz)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM bans 
                WHERE user_id = ? AND is_active = 1 AND ban_until > ?
                ORDER BY created_at DESC LIMIT 1
            """, (user_id, now))
            result = cursor.fetchone()
            return dict(result) if result else None
    
    def remove_ban(self, user_id: int) -> int:
        """
        Удаляет активный бан пользователя.
        
        Args:
            user_id: ID пользователя
        
        Returns:
            int: Количество удалённых записей
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE bans SET is_active = 0 WHERE user_id = ? AND is_active = 1",
                (user_id,)
            )
            updated = cursor.rowcount
            logger.info(f"Removed ban for user_id={user_id}, updated={updated}")
            return updated


# Создаем глобальный экземпляр репозитория
db_repo = ForwardsRepository(config.DB_PATH)

