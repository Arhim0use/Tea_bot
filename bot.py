"""
Точка входа приложения TeaBot v3.0.
Инициализация и запуск бота.
"""

import asyncio
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.config import config
from src.logger import logger
from src.handlers import router


async def main() -> None:
    """
    Главная функция для запуска бота.
    """
    # Валидация конфигурации
    if not config.validate():
        logger.error("Configuration validation failed. Please check your .env file.")
        sys.exit(1)
    
    logger.info("Starting TeaBot v3.0...")
    logger.info(f"Group ID: {config.GROUP_ID}")
    logger.info(f"Channel ID: {config.CHANNEL_ID}")
    logger.info(f"Daily limit: {config.DAILY_LIMIT}")
    logger.info(f"Admins: {len(config.ADMINS)}")
    
    # Создаем бота и диспетчер
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher()
    
    # Регистрируем роутер с обработчиками
    dp.include_router(router)
    
    try:
        # Запускаем polling
        logger.info("Bot started successfully! Polling...")
        await dp.start_polling(bot, allowed_updates=["message"])
    except Exception as e:
        logger.error(f"Error during polling: {e}")
    finally:
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (KeyboardInterrupt)")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
