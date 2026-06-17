# bot/management/commands/runbot.py
from django.core.management.base import BaseCommand
from bot.bot import run_bot
import asyncio

class Command(BaseCommand):
    help = 'Telegram botni ishga tushirish'

    def handle(self, *args, **options):
        asyncio.run(run_bot())