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
    
    def get_last_forward_time(self, username: str = None) -> Optional[datetime]:
        """
        Возвращает время последней пересылки (глобально или для конкретного пользователя).
        
        Args:
            username: Имя пользователя (если None, возвращает последнюю пересылку любого пользователя)
        
        Returns:
            Optional[datetime]: Время последней пересылки или None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if username:
                cursor.execute(
                    "SELECT datetime FROM forwards WHERE username = ? ORDER BY datetime DESC LIMIT 1",
                    (username,)
                )
            else:
                cursor.execute(
                    "SELECT datetime FROM forwards ORDER BY datetime DESC LIMIT 1"
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
    
    def get_monthly_top_users(self, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Возвращает топ пользователей за текущий месяц по количеству пересылок.
        
        Args:
            limit: Количество пользователей в топе
        
        Returns:
            List[Dict]: Список пользователей с количеством пересылок
        """
        tz = pytz.timezone(config.TIMEZONE)
        now = datetime.now(tz)
        
        # Определяем начало текущего месяца
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT username, COUNT(*) as count 
                FROM forwards 
                WHERE datetime >= ? 
                GROUP BY username 
                ORDER BY count DESC 
                LIMIT ?
            """, (month_start, limit))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_stats_by_month(self, month_number: int, year: Optional[int] = None) -> Dict[str, Any]:
        """
        Возвращает статистику за указанный месяц.
        
        Args:
            month_number: Номер месяца (1-12)
            year: Год (если None, используется текущий год)
        
        Returns:
            Dict: Статистика с полями start_date, end_date, total_count, users
        """
        tz = pytz.timezone(config.TIMEZONE)
        now = datetime.now(tz)
        
        if year is None:
            year = now.year
        
        # Определяем начало и конец месяца
        month_start = datetime(year, month_number, 1, 0, 0, 0, tzinfo=tz)
        if month_number == 12:
            month_end = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=tz)
        else:
            month_end = datetime(year, month_number + 1, 1, 0, 0, 0, tzinfo=tz)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT username, COUNT(*) as count 
                FROM forwards 
                WHERE datetime >= ? AND datetime < ?
                GROUP BY username 
                ORDER BY count DESC
            """, (month_start, month_end))
            rows = cursor.fetchall()
            
            cursor.execute("""
                SELECT COUNT(*) as total 
                FROM forwards 
                WHERE datetime >= ? AND datetime < ?
            """, (month_start, month_end))
            total_result = cursor.fetchone()
            total_count = total_result["total"] if total_result else 0
        
        return {
            "start_date": month_start,
            "end_date": month_end,
            "total_count": total_count,
            "users": [dict(row) for row in rows]
        }
    
    def get_stats_by_year(self, year: Optional[int] = None) -> Dict[str, Any]:
        """
        Возвращает статистику за указанный год.
        
        Args:
            year: Год (если None, используется текущий год)
        
        Returns:
            Dict: Статистика с полями start_date, end_date, total_count, users, monthly_stats
        """
        tz = pytz.timezone(config.TIMEZONE)
        now = datetime.now(tz)
        
        if year is None:
            year = now.year
        
        year_start = datetime(year, 1, 1, 0, 0, 0, tzinfo=tz)
        year_end = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=tz)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT username, COUNT(*) as count 
                FROM forwards 
                WHERE datetime >= ? AND datetime < ?
                GROUP BY username 
                ORDER BY count DESC
            """, (year_start, year_end))
            rows = cursor.fetchall()
            
            cursor.execute("""
                SELECT COUNT(*) as total 
                FROM forwards 
                WHERE datetime >= ? AND datetime < ?
            """, (year_start, year_end))
            total_result = cursor.fetchone()
            total_count = total_result["total"] if total_result else 0
            
            # Статистика по месяцам
            cursor.execute("""
                SELECT 
                    CAST(strftime('%m', datetime) AS INTEGER) as month,
                    COUNT(*) as count
                FROM forwards 
                WHERE datetime >= ? AND datetime < ?
                GROUP BY month
                ORDER BY month
            """, (year_start, year_end))
            monthly_rows = cursor.fetchall()
        
        return {
            "start_date": year_start,
            "end_date": year_end,
            "total_count": total_count,
            "users": [dict(row) for row in rows],
            "monthly_stats": [dict(row) for row in monthly_rows]
        }
    
    def get_stats_all_time(self) -> Dict[str, Any]:
        """
        Возвращает статистику за все время.
        
        Returns:
            Dict: Статистика с полями total_count, users, yearly_stats
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT username, COUNT(*) as count 
                FROM forwards 
                GROUP BY username 
                ORDER BY count DESC
            """)
            rows = cursor.fetchall()
            
            cursor.execute("SELECT COUNT(*) as total FROM forwards")
            total_result = cursor.fetchone()
            total_count = total_result["total"] if total_result else 0
            
            # Статистика по годам
            cursor.execute("""
                SELECT 
                    CAST(strftime('%Y', datetime) AS INTEGER) as year,
                    COUNT(*) as count
                FROM forwards 
                GROUP BY year
                ORDER BY year
            """)
            yearly_rows = cursor.fetchall()
        
        return {
            "total_count": total_count,
            "users": [dict(row) for row in rows],
            "yearly_stats": [dict(row) for row in yearly_rows]
        }
    
    def get_stats_by_hours(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """
        Возвращает статистику активности по часам за период.
        
        Args:
            start_date: Начало периода
            end_date: Конец периода
        
        Returns:
            List[Dict]: Список с полями hour (0-23) и count
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    CAST(strftime('%H', datetime) AS INTEGER) as hour,
                    COUNT(*) as count
                FROM forwards 
                WHERE datetime >= ? AND datetime < ?
                GROUP BY hour
                ORDER BY hour
            """, (start_date, end_date))
            rows = cursor.fetchall()
        
        # Заполняем пропущенные часы нулями
        result = {row["hour"]: row["count"] for row in rows}
        return [{"hour": h, "count": result.get(h, 0)} for h in range(24)]
    
    def get_stats_by_weekdays(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """
        Возвращает статистику активности по дням недели за период.
        
        Args:
            start_date: Начало периода
            end_date: Конец периода
        
        Returns:
            List[Dict]: Список с полями weekday (0-6, где 0=понедельник) и count
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # SQLite: 0=воскресенье, но мы хотим 0=понедельник
            cursor.execute("""
                SELECT 
                    CASE CAST(strftime('%w', datetime) AS INTEGER)
                        WHEN 0 THEN 6
                        ELSE CAST(strftime('%w', datetime) AS INTEGER) - 1
                    END as weekday,
                    COUNT(*) as count
                FROM forwards 
                WHERE datetime >= ? AND datetime < ?
                GROUP BY weekday
                ORDER BY weekday
            """, (start_date, end_date))
            rows = cursor.fetchall()
        
        # Заполняем пропущенные дни нулями
        result = {row["weekday"]: row["count"] for row in rows}
        return [{"weekday": d, "count": result.get(d, 0)} for d in range(7)]
    
    def get_stats_by_days(self, month_number: int, year: int) -> List[Dict[str, Any]]:
        """
        Возвращает статистику активности по дням месяца.
        
        Args:
            month_number: Номер месяца (1-12)
            year: Год
        
        Returns:
            List[Dict]: Список с полями day и count
        """
        tz = pytz.timezone(config.TIMEZONE)
        month_start = datetime(year, month_number, 1, 0, 0, 0, tzinfo=tz)
        if month_number == 12:
            month_end = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=tz)
        else:
            month_end = datetime(year, month_number + 1, 1, 0, 0, 0, tzinfo=tz)
        
        # Определяем количество дней в месяце
        days_in_month = (month_end - month_start).days
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    CAST(strftime('%d', datetime) AS INTEGER) as day,
                    COUNT(*) as count
                FROM forwards 
                WHERE datetime >= ? AND datetime < ?
                GROUP BY day
                ORDER BY day
            """, (month_start, month_end))
            rows = cursor.fetchall()
        
        # Заполняем пропущенные дни нулями
        result = {row["day"]: row["count"] for row in rows}
        return [{"day": d, "count": result.get(d, 0)} for d in range(1, days_in_month + 1)]
    
    def get_all_users_in_period(self, start_date: datetime, end_date: datetime) -> List[str]:
        """
        Возвращает список всех уникальных пользователей за период.
        
        Args:
            start_date: Начало периода
            end_date: Конец периода
        
        Returns:
            List[str]: Список уникальных username
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT username 
                FROM forwards 
                WHERE datetime >= ? AND datetime < ?
                ORDER BY username
            """, (start_date, end_date))
            rows = cursor.fetchall()
            return [row["username"] for row in rows]
    
    def get_users_stats_in_period(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """
        Возвращает статистику пользователей за период с количеством вызовов.
        
        Args:
            start_date: Начало периода
            end_date: Конец периода
        
        Returns:
            List[Dict]: Список словарей с полями username и count, отсортированный по count DESC
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT username, COUNT(*) as count 
                FROM forwards 
                WHERE datetime >= ? AND datetime < ?
                GROUP BY username 
                ORDER BY count DESC
            """, (start_date, end_date))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]


# Создаем глобальный экземпляр репозитория
db_repo = ForwardsRepository(config.DB_PATH)

