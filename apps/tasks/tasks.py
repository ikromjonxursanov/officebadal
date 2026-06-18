import asyncio
from datetime import date

from aiogram import Bot
from celery import shared_task
from django.conf import settings

from apps.contributions.models import MonthlyContribution, Payment
from apps.duties.models import DutyAssignment
from apps.users.models import User


def _send_telegram_message(chat_id, text):
    token = settings.TELEGRAM_BOT_TOKEN
    if not token or not chat_id:
        return

    async def _send():
        bot = Bot(token=token)
        await bot.send_message(chat_id=chat_id, text=text)

    asyncio.run(_send())


@shared_task
def send_monthly_reminders():
    today = date.today()
    contribution = MonthlyContribution.objects.filter(
        month__year=today.year,
        month__month=today.month,
        is_active=True,
        due_date=today,
    ).first()

    if not contribution:
        return

    for user in User.objects.filter(is_active=True):
        if not user.telegram_id:
            continue

        has_paid = Payment.objects.filter(
            user=user,
            contribution=contribution,
            status=Payment.STATUS_APPROVED,
        ).exists()
        if has_paid:
            continue

        _send_telegram_message(
            user.telegram_id,
            (
                f"Bugun oylik badal kuni.\n"
                f"Oy: {contribution.month.strftime('%Y-%m')}\n"
                f"Summa: {contribution.amount} so'm"
            ),
        )


@shared_task
def send_duty_reminder():
    today = date.today()
    first_day = today.replace(day=1)
    assignment = DutyAssignment.objects.filter(
        month=first_day
    ).select_related('user').first()

    if not assignment:
        return

    if assignment.user.telegram_id:
        _send_telegram_message(
            assignment.user.telegram_id,
            f"Bu oy bozorlik navbati: {assignment.user.get_full_name() or assignment.user.username}"
        )

    group_chat_id = settings.TELEGRAM_GROUP_CHAT_ID
    if group_chat_id:
        _send_telegram_message(
            group_chat_id,
            (
                f"📅 Bu oy bozorlik navbati: "
                f"{assignment.user.get_full_name() or assignment.user.username}"
            )
        )
