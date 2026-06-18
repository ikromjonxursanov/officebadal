import asyncio
import fcntl
import os

from aiogram.exceptions import TelegramConflictError
from django.core.management.base import BaseCommand

from apps.bot.bot import run_bot


class Command(BaseCommand):
    help = 'Telegram botni ishga tushirish'

    def handle(self, *args, **options):
        lock_path = '/tmp/officbadal_runbot.lock'
        lock_file = open(lock_path, 'a+')

        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.stdout.write(
                self.style.ERROR(
                    'Bot allaqachon ishlayapti. Iltimos, boshqa nusxasini to\'xtating.'
                )
            )
            return

        self.stdout.write(self.style.SUCCESS('🤖 Telegram bot ishga tushmoqda...'))
        try:
            asyncio.run(run_bot())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Bot to\'xtatildi.'))
        except TelegramConflictError:
            self.stdout.write(
                self.style.ERROR(
                    'TelegramConflictError: boshqa bot nusxasi ishlayapti. '
                    'Iltimos, bitta nusxani faqat bitta terminalda ishga tushiring.'
                )
            )
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'Xatolik: {exc}'))
        finally:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            finally:
                lock_file.close()