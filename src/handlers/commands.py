"""
Обработчики команд и сообщений бота.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.exceptions import TelegramAPIError

from src.config import config
from src.logger import logger
from src.database.repository import db_repo
from src.utils.helpers import (
    get_user_display_name,
    extract_custom_text,
    format_tea_caption,
    get_message_type
)

# Создаем роутер для обработчиков
router = Router()


def is_admin(user_id: int) -> bool:
    """
    Проверяет, является ли пользователь администратором.
    
    Args:
        user_id: ID пользователя
    
    Returns:
        bool: True если пользователь админ
    """
    return user_id in config.ADMINS


def is_correct_chat(message: Message) -> bool:
    """
    Проверяет, что сообщение из нужной группы.
    
    Args:
        message: Объект сообщения
    
    Returns:
        bool: True если сообщение из правильного чата
    """
    return message.chat.id == config.GROUP_ID


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """
    Обработчик команды /help.
    Показывает список доступных команд.
    """
    if not is_correct_chat(message):
        return
    
    help_text = """
🍵 <b>TeaBot v3.0 - Справка</b>

<b>Доступные команды:</b>

/tea - Опубликовать анонс в канале
  • Просто /tea - стандартный анонс
  • /tea с фото - фото с подписью
  • /tea текст с фото - фото с кастомным текстом

/help - Показать это сообщение

<b>Команды для администраторов:</b>
/stats - Показать статистику пересылок за сегодня
/reset - Сбросить счётчик пересылок

<b>Лимиты:</b>
• {limit} пересылок в сутки
• Сброс в {reset_hour}:00 МСК
    """.format(limit=config.DAILY_LIMIT, reset_hour=config.RESET_HOUR)
    
    await message.answer(help_text.strip(), parse_mode="HTML")
    logger.info(f"Help command used by {get_user_display_name(message.from_user)}")


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    """
    Обработчик команды /stats.
    Показывает статистику пересылок (только для админов).
    """
    if not is_correct_chat(message):
        return
    
    if not is_admin(message.from_user.id):
        await message.answer("❌ Эта команда доступна только администраторам.")
        logger.warning(f"Unauthorized stats attempt by {get_user_display_name(message.from_user)}")
        return
    
    today_count = db_repo.get_today_count()
    remaining = max(0, config.DAILY_LIMIT - today_count)
    
    stats_text = f"""
📊 <b>Статистика пересылок</b>

Сегодня отправлено: {today_count}/{config.DAILY_LIMIT}
Осталось: {remaining}
    """
    
    await message.answer(stats_text.strip(), parse_mode="HTML")
    logger.info(f"Stats viewed by admin {get_user_display_name(message.from_user)}")


@router.message(Command("reset"))
async def cmd_reset(message: Message) -> None:
    """
    Обработчик команды /reset.
    Сбрасывает счётчик пересылок (только для админов).
    """
    if not is_correct_chat(message):
        return
    
    if not is_admin(message.from_user.id):
        await message.answer("❌ Эта команда доступна только администраторам.")
        logger.warning(f"Unauthorized reset attempt by {get_user_display_name(message.from_user)}")
        return
    
    deleted = db_repo.reset_today()
    await message.answer(f"✅ Счётчик сброшен. Удалено записей: {deleted}")
    logger.info(f"Forwards reset by admin {get_user_display_name(message.from_user)}, deleted: {deleted}")


@router.message(Command("tea"))
async def cmd_tea(message: Message) -> None:
    """
    Обработчик команды /tea.
    Публикует сообщение в канале с учётом лимитов.
    """
    if not is_correct_chat(message):
        return
    
    # Проверяем лимит
    today_count = db_repo.get_today_count()
    if today_count >= config.DAILY_LIMIT:
        await message.answer("⏰ Следующий анонс завтра!")
        logger.warning(f"Limit reached for {get_user_display_name(message.from_user)}")
        return
    
    # Получаем информацию о пользователе
    username = get_user_display_name(message.from_user)
    custom_text = extract_custom_text(message)
    message_type = get_message_type(message)
    
    # Формируем подпись
    caption = format_tea_caption(username, custom_text)
    
    try:
        # Отправляем в канал в зависимости от типа сообщения
        if message.photo:
            # Берём фото с наибольшим разрешением
            photo = message.photo[-1]
            await message.bot.send_photo(
                chat_id=config.CHANNEL_ID,
                photo=photo.file_id,
                caption=caption
            )
        elif message.video:
            await message.bot.send_video(
                chat_id=config.CHANNEL_ID,
                video=message.video.file_id,
                caption=caption
            )
        elif message.video_note:
            # Видео-заметки не поддерживают caption
            await message.bot.send_video_note(
                chat_id=config.CHANNEL_ID,
                video_note=message.video_note.file_id
            )
            # Отправляем caption отдельным сообщением
            await message.bot.send_message(
                chat_id=config.CHANNEL_ID,
                text=caption
            )
        else:
            # Текстовое сообщение
            await message.bot.send_message(
                chat_id=config.CHANNEL_ID,
                text=caption
            )
        
        # Записываем в БД
        db_repo.add_forward(username, message_type)
        
        # Обновляем счётчик
        remaining = config.DAILY_LIMIT - today_count - 1
        await message.answer(f"✅ Отправлено! Осталось {remaining} пересылок.")
        
        logger.info(f"Sent {message_type} tea by {username}")
        
    except TelegramAPIError as e:
        await message.answer("❌ Ошибка при отправке сообщения в канал.")
        logger.error(f"Failed to send message to channel: {e}")
    except Exception as e:
        await message.answer("❌ Произошла непредвиденная ошибка.")
        logger.error(f"Unexpected error in tea command: {e}")

