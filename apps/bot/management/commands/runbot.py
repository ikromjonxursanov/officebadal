# apps/bot/management/commands/runbot.py
from django.core.management.base import BaseCommand
import asyncio
from apps.bot.bot import run_bot


class Command(BaseCommand):
    help = 'Telegram botni ishga tushirish'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🤖 Telegram bot ishga tushmoqda...'))
        try:
            asyncio.run(run_bot())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Bot to‘xtatildi.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Xatolik: {e}'))