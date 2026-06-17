## apps/bot/handlers.py
from aiogram import Router, types
from aiogram.filters import Command
from asgiref.sync import sync_to_async
from datetime import date

from apps.users.models import User
from apps.contributions.models import MonthlyContribution, Payment
from apps.duties.models import DutyAssignment, DutyCycle

router = Router()

@router.message(Command("start"))
async def start_handler(message: types.Message):
    telegram_id = message.from_user.id
    full_name = message.from_user.full_name

    user, created = await sync_to_async(User.objects.get_or_create)(
        telegram_id=telegram_id,
        defaults={'first_name': full_name[:30], 'username': f"tg_{telegram_id}"}
    )

    await message.answer(
        f"✅ Xush kelibsiz, {full_name}!\n\n"
        "Buyruqlar:\n"
        "/toladim - Bugungi badalni to'laganimni belgilash\n"
        "/navbat - Joriy navbatni ko'rish\n"
        "/status - Holatni ko'rish"
    )


@router.message(Command("toladim"))
async def payment_handler(message: types.Message):
    telegram_id = message.from_user.id

    # Hozirgi oyning badalini topish
    today = date.today()
    first_day = today.replace(day=1)

    contribution = await sync_to_async(lambda: MonthlyContribution.objects.filter(
        month=first_day, is_active=True
    ).first())()

    if not contribution:
        await message.answer("❌ Hozirgi oy uchun badal sozlanmagan.")
        return

    user = await sync_to_async(User.objects.get)(telegram_id=telegram_id)

    # To'lovni saqlash
    payment, created = await sync_to_async(Payment.objects.get_or_create)(
        user=user,
        contribution=contribution,
        defaults={'amount': contribution.amount}
    )

    if created:
        await message.answer(f"✅ {contribution.amount} so'm to'lov qayd etildi. Rahmat!")
    else:
        await message.answer("✅ Siz allaqachon bu oy badalni to'lagansiz.")


@router.message(Command("navbat"))
async def duty_handler(message: types.Message):
    today = date.today()
    first_day = today.replace(day=1)

    assignment = await sync_to_async(lambda: DutyAssignment.objects.filter(
        month=first_day
    ).select_related('user').first())()

    if assignment:
        await message.answer(f"📅 Bu oy bozorlik navbati: <b>{assignment.user.first_name}</b>")
    else:
        await message.answer("Navbatchilik hali sozlanmagan.")


@router.message(Command("status"))
async def status_handler(message: types.Message):
    await message.answer("🔄 Holat tekshirilmoqda... (hozircha oddiy javob)")