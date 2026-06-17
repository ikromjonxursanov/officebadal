# apps/bot/handlers.py
from aiogram import Router, types
from aiogram.filters import Command
from asgiref.sync import sync_to_async

# To'g'ri import (chunki apps/ ichida)
from apps.users.models import User

router = Router()

@router.message(Command("start"))
async def start_handler(message: types.Message):
    telegram_id = message.from_user.id
    full_name = message.from_user.full_name

    user, created = await sync_to_async(User.objects.get_or_create)(
        telegram_id=telegram_id,
        defaults={
            'username': f"tg_{telegram_id}",
            'first_name': full_name[:30],  # Django limit
        }
    )

    if created:
        await message.answer("✅ Siz tizimda ro‘yxatdan o‘tdingiz!")
    else:
        await message.answer(f"✅ Xush kelibsiz, {full_name}!")