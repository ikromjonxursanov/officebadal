# apps/bot/bot.py

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramConflictError
from django.conf import settings
from .handlers import router

logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=settings.TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()
dp.include_router(router)


async def run_bot():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except TelegramConflictError:
        logging.error(
            'Telegram polling conflict detected. Make sure only one bot instance is running.'
        )
        raise
    finally:
        await bot.session.close()