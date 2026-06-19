import asyncio
import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.contributions.models import ContributionSetting, MonthlyContribution
from apps.contributions.services import get_current_contribution, get_unpaid_users

logger = logging.getLogger(__name__)


async def _send_messages(token: str, messages: list[tuple[int, str]]) -> int:
    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    sent_count = 0
    try:
        for chat_id, text in messages:
            try:
                await bot.send_message(chat_id=chat_id, text=text)
                sent_count += 1
            except Exception:
                logger.exception("Telegram reminder failed for chat_id=%s", chat_id)
    finally:
        await bot.session.close()
    return sent_count


@shared_task
def send_monthly_reminders() -> int:
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN is empty; reminders skipped.")
        return 0

    today = timezone.localdate()
    contribution = get_current_contribution(today)
    if not contribution or contribution.due_date > today:
        return 0

    payment_details = contribution.payment_details or "To'lov kartasi admin tomonidan hali kiritilmagan."
    text = (
        "Bugun oylik badal kuni.\n"
        f"Summa: {contribution.amount} so'm\n"
        f"{payment_details}\n"
        "To'lagan bo'lsangiz /toladim buyrug'ini yuboring."
    )
    messages = [
        (user.telegram_id, text)
        for user in get_unpaid_users(contribution)
        if user.telegram_id
    ]
    if not messages:
        return 0

    return asyncio.run(_send_messages(settings.TELEGRAM_BOT_TOKEN, messages))


@shared_task
def create_monthly_contribution() -> int:
    today = timezone.localdate()
    month = today.replace(day=1)
    setting = ContributionSetting.objects.filter(is_active=True).order_by('-created_at').first()
    if not setting:
        return 0

    due_date = month.replace(day=setting.due_day)
    _, created = MonthlyContribution.objects.get_or_create(
        month=month,
        defaults={
            'amount': setting.amount,
            'due_date': due_date,
            'payment_card_number': setting.payment_card_number,
            'payment_card_holder': setting.payment_card_holder,
            'is_active': True,
        },
    )
    return int(created)
