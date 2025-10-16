"""
Обработчики команд и сообщений бота.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.exceptions import TelegramAPIError
from datetime import datetime, timedelta
import pytz

from src.config import config
from src.logger import logger
from src.database.repository import db_repo
from src.utils.helpers import (
    get_user_display_name,
    extract_custom_text,
    format_tea_caption,
    format_quote_caption,
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
    
    # Определяем доступность команд
    stats_access = "всем" if not config.STATS_ADMIN_ONLY else "администраторам"
    reset_access = "всем" if not config.RESET_ADMIN_ONLY else "администраторам"
    ban_access = "всем" if not config.BAN_ADMIN_ONLY else "администраторам"
    unban_access = "всем" if not config.UNBAN_ADMIN_ONLY else "администраторам"
    
    help_text = f"""
🍵 <b>TeaBot v3.0 - Справка</b>

<b>Доступные команды:</b>

/{config.MAIN_COMMAND} - Опубликовать анонс в канале
  • Просто /{config.MAIN_COMMAND} - стандартный анонс
  • /{config.MAIN_COMMAND} с фото - фото с подписью
  • /{config.MAIN_COMMAND} текст с фото - фото с кастомным текстом

/quot - Опубликовать случайную цитату в канале
  • Просто /quot - текстовая цитата
  • /quot с фото - фото с цитатой в подписи
  • Работает аналогично /{config.MAIN_COMMAND}

/help - Показать это сообщение
/stats - Показать статистику пересылок и топ-3 за месяц (доступно {stats_access})
/reset - Сбросить счётчик пересылок (доступно {reset_access})
/ban - Забанить пользователя (доступно {ban_access})
  • Формат: /ban @username hours [reason]
  • Пример: /ban @user123 24 Спам
/unban - Разбанить пользователя (доступно {unban_access})
  • Формат: /unban @username или ответ на сообщение

<b>Лимиты:</b>
• {config.DAILY_LIMIT} пересылок в сутки (для всех команд)
• Сброс в {config.RESET_HOUR}:00 МСК
• Timeout между анонсами: {config.TIMEOUT_MINUTES} минут
    """
    
    await message.answer(help_text.strip(), parse_mode="HTML")
    logger.info(f"Help command used by {get_user_display_name(message.from_user)}")


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    """
    Обработчик команды /stats.
    Показывает статистику пересылок.
    """
    if not is_correct_chat(message):
        return
    
    # Проверяем права доступа
    if config.STATS_ADMIN_ONLY and not is_admin(message.from_user.id):
        await message.answer("❌ Эта команда доступна только администраторам.")
        logger.warning(f"Unauthorized stats attempt by {get_user_display_name(message.from_user)}")
        return
    
    today_count = db_repo.get_today_count()
    remaining = max(0, config.DAILY_LIMIT - today_count)
    
    # Получаем время последней пересылки (глобально)
    last_forward_time = db_repo.get_last_forward_time()
    timeout_info = ""
    
    if last_forward_time:
        tz = pytz.timezone(config.TIMEZONE)
        if isinstance(last_forward_time, str):
            last_forward_time = datetime.fromisoformat(last_forward_time).replace(tzinfo=tz)
        elif last_forward_time.tzinfo is None:
            last_forward_time = last_forward_time.replace(tzinfo=tz)
        
        now = datetime.now(tz)
        time_since_last = now - last_forward_time
        timeout_duration = timedelta(minutes=config.TIMEOUT_MINUTES)
        
        if time_since_last < timeout_duration:
            remaining_time = timeout_duration - time_since_last
            minutes = int(remaining_time.total_seconds() // 60)
            seconds = int(remaining_time.total_seconds() % 60)
            timeout_info = f"\n⏳ До следующего анонса: {minutes}м {seconds}с"
        else:
            timeout_info = "\n✅ Анонс можно отправить сейчас"
    else:
        timeout_info = "\n✅ Анонс можно отправить сейчас"
    
    # Получаем топ-3 пользователей за месяц
    monthly_top = db_repo.get_monthly_top_users(3)
    top_users_text = ""
    
    if monthly_top:
        top_users_text = "\n\n🏆 <b>Топ-3 за месяц:</b>"
        medals = ["🥇", "🥈", "🥉"]
        for i, user in enumerate(monthly_top):
            medal = medals[i] if i < len(medals) else "🏅"
            top_users_text += f"\n{medal} {user['username']}: {user['count']} раз"
    else:
        top_users_text = "\n\n🏆 <b>Топ-3 за месяц:</b>\nПока нет данных"
    
    stats_text = f"""
📊 <b>Статистика пересылок</b>

Сегодня отправлено: {today_count}/{config.DAILY_LIMIT}
Осталось: {remaining}{timeout_info}{top_users_text}
    """
    
    await message.answer(stats_text.strip(), parse_mode="HTML")
    logger.info(f"Stats viewed by {get_user_display_name(message.from_user)}")


@router.message(Command("reset"))
async def cmd_reset(message: Message) -> None:
    """
    Обработчик команды /reset.
    Сбрасывает счётчик пересылок.
    """
    if not is_correct_chat(message):
        return
    
    # Проверяем права доступа
    if config.RESET_ADMIN_ONLY and not is_admin(message.from_user.id):
        await message.answer("❌ Эта команда доступна только администраторам.")
        logger.warning(f"Unauthorized reset attempt by {get_user_display_name(message.from_user)}")
        return
    
    deleted = db_repo.reset_today()
    await message.answer(f"✅ Счётчик сброшен. Удалено записей: {deleted}")
    logger.info(f"Forwards reset by admin {get_user_display_name(message.from_user)}, deleted: {deleted}")


@router.message(Command("ban"))
async def cmd_ban(message: Message) -> None:
    """
    Обработчик команды /ban.
    Банит пользователя на указанное количество часов.
    Формат: /ban @username hours [reason]
    """
    if not is_correct_chat(message):
        return
    
    # Проверяем права доступа
    if config.BAN_ADMIN_ONLY and not is_admin(message.from_user.id):
        await message.answer("❌ Эта команда доступна только администраторам.")
        logger.warning(f"Unauthorized ban attempt by {get_user_display_name(message.from_user)}")
        return
    
    # Парсим аргументы команды
    args = message.text.split()[1:]  # Убираем /ban
    
    if len(args) < 2:
        await message.answer(
            "❌ Неверный формат команды.\n"
            "Используйте: /ban @username hours [reason]\n"
            "Пример: /ban @user123 24 Спам"
        )
        return
    
    # Извлекаем username (убираем @ если есть)
    target_username = args[0].lstrip('@')
    
    # Проверяем количество часов
    try:
        hours = int(args[1])
        if hours <= 0:
            raise ValueError("Hours must be positive")
    except ValueError:
        await message.answer("❌ Количество часов должно быть положительным числом.")
        return
    
    # Извлекаем причину (если есть)
    reason = " ".join(args[2:]) if len(args) > 2 else None
    
    # Получаем информацию о пользователе из сообщения
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user = message.reply_to_message.from_user
        target_user_id = target_user.id
        target_display_name = get_user_display_name(target_user)
    else:
        # Если не ответ на сообщение, пытаемся найти пользователя по username
        # В реальном боте здесь нужно было бы использовать API Telegram для поиска пользователя
        await message.answer("❌ Пожалуйста, ответьте на сообщение пользователя, которого хотите забанить.")
        return
    
    # Проверяем, что не баним админа
    if target_user_id in config.ADMINS:
        await message.answer("❌ Нельзя забанить администратора.")
        return
    
    # Добавляем бан в базу данных
    admin_name = get_user_display_name(message.from_user)
    ban_id = db_repo.add_ban(
        user_id=target_user_id,
        username=target_display_name,
        banned_by=message.from_user.id,
        banned_by_username=admin_name,
        hours=hours,
        reason=reason
    )
    
    # Формируем сообщение о бане
    ban_text = f"🔨 <b>Пользователь забанен</b>\n\n"
    ban_text += f"👤 Пользователь: {target_display_name}\n"
    ban_text += f"⏰ Срок: {hours} часов\n"
    ban_text += f"👮 Администратор: {admin_name}\n"
    if reason:
        ban_text += f"📝 Причина: {reason}\n"
    
    await message.answer(ban_text.strip(), parse_mode="HTML")
    logger.info(f"User {target_display_name} banned by {admin_name} for {hours} hours, reason: {reason}")


@router.message(Command("unban"))
async def cmd_unban(message: Message) -> None:
    """
    Обработчик команды /unban.
    Снимает бан с пользователя.
    Формат: /unban @username или ответ на сообщение пользователя
    """
    if not is_correct_chat(message):
        return
    
    # Проверяем права доступа
    if config.UNBAN_ADMIN_ONLY and not is_admin(message.from_user.id):
        await message.answer("❌ Эта команда доступна только администраторам.")
        logger.warning(f"Unauthorized unban attempt by {get_user_display_name(message.from_user)}")
        return
    
    # Получаем информацию о пользователе из сообщения
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user = message.reply_to_message.from_user
        target_user_id = target_user.id
        target_display_name = get_user_display_name(target_user)
    else:
        # Если не ответ на сообщение, пытаемся найти пользователя по username
        args = message.text.split()[1:]  # Убираем /unban
        
        if len(args) < 1:
            await message.answer(
                "❌ Неверный формат команды.\n"
                "Используйте: /unban @username\n"
                "Или ответьте на сообщение пользователя командой /unban"
            )
            return
        
        # Извлекаем username (убираем @ если есть)
        target_username = args[0].lstrip('@')
        await message.answer("❌ Пожалуйста, ответьте на сообщение пользователя, которого хотите разбанить.")
        return
    
    # Проверяем, забанен ли пользователь
    ban_info = db_repo.is_user_banned(target_user_id)
    if not ban_info:
        await message.answer(f"ℹ️ Пользователь {target_display_name} не забанен.")
        return
    
    # Снимаем бан
    removed_count = db_repo.remove_ban(target_user_id)
    
    if removed_count > 0:
        admin_name = get_user_display_name(message.from_user)
        
        unban_text = f"✅ <b>Пользователь разбанен</b>\n\n"
        unban_text += f"👤 Пользователь: {target_display_name}\n"
        unban_text += f"👮 Администратор: {admin_name}"
        
        await message.answer(unban_text.strip(), parse_mode="HTML")
        logger.info(f"User {target_display_name} unbanned by {admin_name}")
    else:
        await message.answer(f"❌ Ошибка при снятии бана с пользователя {target_display_name}.")


@router.message(Command(config.MAIN_COMMAND))
async def cmd_tea(message: Message) -> None:
    """
    Обработчик команды /tea.
    Публикует сообщение в канале с учётом лимитов, timeout и банов.
    """
    if not is_correct_chat(message):
        return
    
    user_id = message.from_user.id
    username = get_user_display_name(message.from_user)
    
    # Проверяем, не забанен ли пользователь
    ban_info = db_repo.is_user_banned(user_id)
    if ban_info:
        tz = pytz.timezone(config.TIMEZONE)
        ban_until = datetime.fromisoformat(ban_info['ban_until']).replace(tzinfo=tz)
        now = datetime.now(tz)
        remaining_time = ban_until - now
        
        hours = int(remaining_time.total_seconds() // 3600)
        minutes = int((remaining_time.total_seconds() % 3600) // 60)
        
        ban_text = f"🚫 <b>Вы забанены!</b>\n\n"
        ban_text += f"⏰ Осталось: {hours}ч {minutes}м\n"
        if ban_info.get('reason'):
            ban_text += f"📝 Причина: {ban_info['reason']}\n"
        ban_text += f"👮 Забанил: {ban_info['banned_by_username']}"
        
        await message.answer(ban_text.strip(), parse_mode="HTML")
        logger.warning(f"Banned user {username} tried to use /tea")
        return
    
    # Проверяем timeout между анонсами (глобально для всех пользователей)
    last_forward_time = db_repo.get_last_forward_time()
    if last_forward_time:
        tz = pytz.timezone(config.TIMEZONE)
        if isinstance(last_forward_time, str):
            last_forward_time = datetime.fromisoformat(last_forward_time).replace(tzinfo=tz)
        elif last_forward_time.tzinfo is None:
            last_forward_time = last_forward_time.replace(tzinfo=tz)
        
        now = datetime.now(tz)
        time_since_last = now - last_forward_time
        timeout_duration = timedelta(minutes=config.TIMEOUT_MINUTES)
        
        if time_since_last < timeout_duration:
            remaining_time = timeout_duration - time_since_last
            minutes = int(remaining_time.total_seconds() // 60)
            seconds = int(remaining_time.total_seconds() % 60)
            
            await message.answer(
                f"⏳ Слишком рано! Следующий анонс через {minutes}м {seconds}с",
                parse_mode="HTML"
            )
            logger.warning(f"Global timeout violation by {username}, {minutes}m {seconds}s remaining")
            return
    
    # Проверяем лимит
    today_count = db_repo.get_today_count()
    if today_count >= config.DAILY_LIMIT:
        await message.answer("⏰ Следующий анонс завтра!")
        logger.warning(f"Limit reached for {username}")
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


@router.message(Command("quot"))
async def cmd_quot(message: Message) -> None:
    """
    Обработчик команды /quot.
    Публикует случайную цитату в канале с учётом лимитов, timeout и банов.
    Работает аналогично команде /tea, но вместо "Чай" отправляет случайную цитату.
    """
    if not is_correct_chat(message):
        return
    
    user_id = message.from_user.id
    username = get_user_display_name(message.from_user)
    
    # Проверяем, не забанен ли пользователь
    ban_info = db_repo.is_user_banned(user_id)
    if ban_info:
        tz = pytz.timezone(config.TIMEZONE)
        ban_until = datetime.fromisoformat(ban_info['ban_until']).replace(tzinfo=tz)
        now = datetime.now(tz)
        remaining_time = ban_until - now
        
        hours = int(remaining_time.total_seconds() // 3600)
        minutes = int((remaining_time.total_seconds() % 3600) // 60)
        
        ban_text = f"🚫 <b>Вы забанены!</b>\n\n"
        ban_text += f"⏰ Осталось: {hours}ч {minutes}м\n"
        if ban_info.get('reason'):
            ban_text += f"📝 Причина: {ban_info['reason']}\n"
        ban_text += f"👮 Забанил: {ban_info['banned_by_username']}"
        
        await message.answer(ban_text.strip(), parse_mode="HTML")
        logger.warning(f"Banned user {username} tried to use /quot")
        return
    
    # Проверяем timeout между анонсами (глобально для всех пользователей)
    last_forward_time = db_repo.get_last_forward_time()
    if last_forward_time:
        tz = pytz.timezone(config.TIMEZONE)
        if isinstance(last_forward_time, str):
            last_forward_time = datetime.fromisoformat(last_forward_time).replace(tzinfo=tz)
        elif last_forward_time.tzinfo is None:
            last_forward_time = last_forward_time.replace(tzinfo=tz)
        
        now = datetime.now(tz)
        time_since_last = now - last_forward_time
        timeout_duration = timedelta(minutes=config.TIMEOUT_MINUTES)
        
        if time_since_last < timeout_duration:
            remaining_time = timeout_duration - time_since_last
            minutes = int(remaining_time.total_seconds() // 60)
            seconds = int(remaining_time.total_seconds() % 60)
            
            await message.answer(
                f"⏳ Слишком рано! Следующий анонс через {minutes}м {seconds}с",
                parse_mode="HTML"
            )
            logger.warning(f"Global timeout violation by {username}, {minutes}m {seconds}s remaining")
            return
    
    # Проверяем лимит
    today_count = db_repo.get_today_count()
    if today_count >= config.DAILY_LIMIT:
        await message.answer("⏰ Следующий анонс завтра!")
        logger.warning(f"Limit reached for {username}")
        return
    
    # Получаем информацию о пользователе
    username = get_user_display_name(message.from_user)
    message_type = get_message_type(message)
    
    # Формируем подпись с цитатой
    caption = format_quote_caption(username)
    
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
        
        logger.info(f"Sent {message_type} quote by {username}")
        
    except TelegramAPIError as e:
        await message.answer("❌ Ошибка при отправке сообщения в канал.")
        logger.error(f"Failed to send message to channel: {e}")
    except Exception as e:
        await message.answer("❌ Произошла непредвиденная ошибка.")
        logger.error(f"Unexpected error in quot command: {e}")

