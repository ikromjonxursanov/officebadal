import asyncio
from html import escape
import logging
from pathlib import Path

from aiogram import Bot, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from django.conf import settings

logger = logging.getLogger(__name__)


PAYMENT_CONFIRM_CALLBACK = 'payment_confirm'
PAYMENT_REJECT_CALLBACK = 'payment_reject'


async def _send_telegram_message(chat_id, text, reply_markup=None):
    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    try:
        await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
    finally:
        await bot.session.close()


async def _send_telegram_photo(chat_id, photo_path, caption, reply_markup=None):
    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    try:
        await bot.send_photo(
            chat_id=chat_id,
            photo=types.FSInputFile(photo_path),
            caption=caption,
            reply_markup=reply_markup,
        )
    finally:
        await bot.session.close()


def send_telegram_message(chat_id, text, reply_markup=None):
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning('TELEGRAM_BOT_TOKEN is empty; notification skipped.')
        return False

    if not chat_id:
        logger.warning('Telegram chat_id is empty; notification skipped.')
        return False

    try:
        asyncio.run(_send_telegram_message(chat_id, text, reply_markup=reply_markup))
    except Exception:
        logger.exception('Telegram notification failed for chat_id=%s', chat_id)
        return False

    return True


def send_telegram_photo(chat_id, photo_path, caption, reply_markup=None):
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning('TELEGRAM_BOT_TOKEN is empty; photo notification skipped.')
        return False

    if not chat_id:
        logger.warning('Telegram chat_id is empty; photo notification skipped.')
        return False

    try:
        asyncio.run(_send_telegram_photo(chat_id, photo_path, caption, reply_markup=reply_markup))
    except Exception:
        logger.exception('Telegram photo notification failed for chat_id=%s', chat_id)
        return False

    return True


def _format_amount(amount):
    amount = int(amount) if amount == amount.to_integral_value() else amount
    return f"{amount:,}".replace(',', ' ')


def _build_admin_payment_caption(payment):
    user_name = escape(payment.user.get_full_name() or payment.user.username or '-')
    telegram_username = escape(payment.user.username or '-')

    return (
        "🧾 Yangi to'lov cheki\n\n"
        f"👤 User: {user_name}\n"
        f"🔗 Telegram: @{telegram_username}\n"
        f"💰 Summa: {_format_amount(payment.amount)} so'm\n"
        f"📅 Oy: {payment.contribution.month:%Y-%m}\n"
        f"📌 Status: {escape(payment.status)}\n\n"
        "Chekni ko'rib, pastdagi tugma orqali tasdiqlang yoki rad eting."
    )


def _admin_payment_keyboard(payment):
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text='✅ Tasdiqlash',
                    callback_data=f'{PAYMENT_CONFIRM_CALLBACK}:{payment.pk}',
                ),
                types.InlineKeyboardButton(
                    text='⚠️ Rad etish',
                    callback_data=f'{PAYMENT_REJECT_CALLBACK}:{payment.pk}',
                ),
            ],
        ],
    )


def _get_receipt_image_path(payment):
    if not payment.receipt_image:
        return None

    try:
        path = Path(payment.receipt_image.path)
    except (NotImplementedError, ValueError):
        path = Path(settings.MEDIA_ROOT) / payment.receipt_image.name

    if not path.exists():
        logger.warning('Receipt image not found for payment_id=%s path=%s', payment.pk, path)
        return None

    return path


def notify_admin_about_payment(payment):
    if not settings.ADMIN_TELEGRAM_ID:
        logger.warning('ADMIN_TELEGRAM_ID is empty; admin notification skipped.')
        return False

    caption = _build_admin_payment_caption(payment)
    reply_markup = _admin_payment_keyboard(payment)
    receipt_path = _get_receipt_image_path(payment)
    if receipt_path:
        return send_telegram_photo(settings.ADMIN_TELEGRAM_ID, receipt_path, caption, reply_markup=reply_markup)

    return send_telegram_message(settings.ADMIN_TELEGRAM_ID, caption, reply_markup=reply_markup)


def notify_user_payment_confirmed(payment):
    return send_telegram_message(
        payment.user.telegram_id,
        "To'lovingiz tasdiqlandi.",
    )


def notify_user_payment_rejected(payment):
    reason = payment.reject_reason or "Sabab ko'rsatilmagan"
    return send_telegram_message(
        payment.user.telegram_id,
        f"To'lovingiz rad etildi. Sabab: {reason}",
    )
