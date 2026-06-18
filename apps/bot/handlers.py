from pathlib import Path
from uuid import uuid4

from aiogram import F, Router, types
from aiogram.filters import Command
from asgiref.sync import sync_to_async
from django.conf import settings

from apps.contributions.models import Payment
from apps.contributions.services import (
    find_user_by_telegram_id,
    get_current_contribution,
    get_payment_for_current_month,
    login_with_username,
    mark_current_month_paid,
)

router = Router()


def format_payment_details(contribution):
    if not contribution.payment_details:
        return "To'lov kartasi admin tomonidan hali kiritilmagan."

    return contribution.payment_details


def only_digits(value):
    return ''.join(char for char in str(value or '') if char.isdigit())


def receipt_caption_is_valid(contribution, caption):
    caption_digits = only_digits(caption)
    amount_digits = only_digits(int(contribution.amount))
    card_digits = only_digits(contribution.payment_card_number)
    card_last4 = card_digits[-4:] if len(card_digits) >= 4 else ''

    return bool(
        caption_digits
        and (
            amount_digits in caption_digits
            or (card_last4 and card_last4 in caption_digits)
        )
    )


RECEIPT_INSTRUCTION = (
    "MUHIM!\n"
    "TO'LOV CHEKINI RASM QILIB YUBORING.\n\n"
    "Chek rasmini caption bilan yuboring.\n"
    "Captionda summa yoki karta oxirgi 4 raqami bo'lsin.\n\n"
    "Chek yubormasangiz /toladim qabul qilinmaydi."
)


@router.message(Command("start"))
async def start_handler(message: types.Message):
    user = await sync_to_async(find_user_by_telegram_id)(message.from_user.id)
    if user:
        await message.answer(
            f"Siz @{user.username} sifatida tizimga kirgansiz.\n\n"
            "Buyruqlar:\n"
            "/karta - To'lov kartasini ko'rish\n"
            "/toladim - To'lov qilganimni adminga yuborish\n"
            "/status - Holatni ko'rish"
        )
        return

    await message.answer(
        "Tizimga kirish uchun Telegram username yuboring.\n"
        "Masalan: ali_valiyev yoki @ali_valiyev"
    )


@router.message(Command("login"))
async def login_handler(message: types.Message):
    await message.answer(
        "Telegram username yuboring.\n"
        "Masalan: ali_valiyev yoki @ali_valiyev"
    )


@router.message(Command("toladim"))
async def payment_handler(message: types.Message):
    user = await sync_to_async(find_user_by_telegram_id)(message.from_user.id)
    if not user:
        await message.answer("Avval /start orqali username bilan tizimga kiring.")
        return

    contribution = await sync_to_async(get_current_contribution)()
    if not contribution:
        await message.answer("Hozirgi oy uchun badal admin tomonidan sozlanmagan.")
        return

    payment = await sync_to_async(get_payment_for_current_month)(user)
    if payment and payment.status == Payment.Status.PENDING:
        await message.answer("To'lov arizangiz admin tasdiqlashini kutmoqda.")
        return
    if payment and payment.status == Payment.Status.APPROVED:
        await message.answer("Siz bu oy badalni to'lagansiz. Admin tasdiqlagan.")
        return

    if user.payment_card_seen_month != contribution.month:
        await message.answer(
            "Avval quyidagi kartaga to'lov qiling:\n\n"
            f"Badal: {contribution.amount} so'm\n"
            f"To'lov kuni: {contribution.due_date}\n\n"
            f"{format_payment_details(contribution)}\n\n"
            f"{RECEIPT_INSTRUCTION}\n\n"
            "Chek yuborgandan keyin /toladim bosing."
        )
        user.payment_card_seen_month = contribution.month
        await sync_to_async(user.save)(update_fields=['payment_card_seen_month'])
        return

    if (
        user.payment_screenshot_month != contribution.month
        or not user.payment_screenshot_file_id
    ):
        await message.answer(
            "To'lov cheki yuborilmagan.\n"
            f"{RECEIPT_INSTRUCTION}\n\n"
            "Chek yuborgandan keyin /toladim bosing."
        )
        return

    result = await sync_to_async(mark_current_month_paid)(
        user,
        receipt_file_id=user.payment_screenshot_file_id,
        receipt_image=user.payment_screenshot_path,
    )
    user.payment_card_seen_month = None
    user.payment_screenshot_month = None
    user.payment_screenshot_file_id = ''
    user.payment_screenshot_path = ''
    await sync_to_async(user.save)(
        update_fields=[
            'payment_card_seen_month',
            'payment_screenshot_month',
            'payment_screenshot_file_id',
            'payment_screenshot_path',
        ]
    )

    if result.created:
        await message.answer(
            f"{result.payment.amount} so'm to'lov arizasi yuborildi.\n"
            "Admin tasdiqlagandan keyin to'langan hisoblanadi."
        )
    elif result.resubmitted:
        await message.answer(
            "To'lov arizasi qayta yuborildi.\n"
            "Admin tasdiqlashi kutilmoqda."
        )
    elif result.payment.status == Payment.Status.PENDING:
        await message.answer("To'lov arizangiz admin tasdiqlashini kutmoqda.")
    elif result.payment.status == Payment.Status.APPROVED:
        await message.answer("Siz bu oy badalni to'lagansiz. Admin tasdiqlagan.")
    else:
        await message.answer("To'lov arizangiz rad etilgan. Qayta yuborish uchun /toladim bosing.")


@router.message(Command("karta"))
async def card_handler(message: types.Message):
    user = await sync_to_async(find_user_by_telegram_id)(message.from_user.id)
    if not user:
        await message.answer("Avval /start orqali username bilan tizimga kiring.")
        return

    contribution = await sync_to_async(get_current_contribution)()
    if not contribution:
        await message.answer("Hozirgi oy uchun badal hali sozlanmagan.")
        return

    await message.answer(
        f"Badal: {contribution.amount} so'm\n"
        f"To'lov kuni: {contribution.due_date}\n\n"
        f"{format_payment_details(contribution)}\n\n"
        f"{RECEIPT_INSTRUCTION}"
    )
    user.payment_card_seen_month = contribution.month
    await sync_to_async(user.save)(update_fields=['payment_card_seen_month'])


@router.message(F.photo)
async def payment_screenshot_handler(message: types.Message):
    user = await sync_to_async(find_user_by_telegram_id)(message.from_user.id)
    if not user:
        await message.answer("Avval /start orqali username bilan tizimga kiring.")
        return

    contribution = await sync_to_async(get_current_contribution)()
    if not contribution:
        await message.answer("Hozirgi oy uchun badal hali sozlanmagan.")
        return

    if user.payment_card_seen_month != contribution.month:
        await message.answer("Avval /karta orqali to'lov kartasini ko'ring.")
        return

    if not receipt_caption_is_valid(contribution, message.caption):
        await message.answer(
            "Bu rasm to'lov cheki sifatida qabul qilinmadi.\n"
            f"{RECEIPT_INSTRUCTION}"
        )
        return

    relative_path = f"receipts/{contribution.month:%Y-%m}/{user.id}-{uuid4().hex}.jpg"
    receipt_path = Path(settings.MEDIA_ROOT) / relative_path
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    await message.bot.download(message.photo[-1], destination=receipt_path)

    user.payment_screenshot_month = contribution.month
    user.payment_screenshot_file_id = message.photo[-1].file_id
    user.payment_screenshot_path = relative_path
    await sync_to_async(user.save)(
        update_fields=[
            'payment_screenshot_month',
            'payment_screenshot_file_id',
            'payment_screenshot_path',
        ]
    )
    await message.answer("To'lov cheki qabul qilindi. Endi /toladim bosing.")


@router.message(Command("status"))
async def status_handler(message: types.Message):
    user = await sync_to_async(find_user_by_telegram_id)(message.from_user.id)
    if not user:
        await message.answer("Avval /start orqali username bilan tizimga kiring.")
        return

    contribution = await sync_to_async(get_current_contribution)()
    if not contribution:
        await message.answer("Hozirgi oy uchun badal hali sozlanmagan.")
        return

    payment = await sync_to_async(get_payment_for_current_month)(user)
    if payment and payment.status == Payment.Status.APPROVED:
        await message.answer(
            "Joriy oy holati: to'langan.\n"
            f"Summa: {payment.amount} so'm\n"
            f"Sana: {payment.paid_date}"
        )
    elif payment and payment.status == Payment.Status.PENDING:
        await message.answer(
            "Joriy oy holati: admin tasdiqlashi kutilmoqda.\n"
            f"Summa: {payment.amount} so'm\n"
            f"Yuborilgan sana: {payment.paid_date}"
        )
    elif payment and payment.status == Payment.Status.REJECTED:
        await message.answer(
            "Joriy oy holati: to'lov arizasi rad etilgan.\n"
            "Qayta yuborish uchun /toladim bosing."
        )
    else:
        await message.answer(
            "Joriy oy holati: to'lanmagan.\n"
            f"Badal: {contribution.amount} so'm\n"
            f"To'lov kuni: {contribution.due_date}\n\n"
            f"{format_payment_details(contribution)}"
        )


@router.message()
async def username_login_handler(message: types.Message):
    text = (message.text or '').strip()
    if not text:
        return

    if text.startswith('/'):
        await message.answer("Noma'lum buyruq. /start, /login, /toladim yoki /status dan foydalaning.")
        return

    try:
        result = await sync_to_async(login_with_username)(
            username=text,
            telegram_id=message.from_user.id,
            first_name=message.from_user.full_name,
        )
    except ValueError as exc:
        await message.answer(str(exc))
        return

    action = "Ro'yxatdan o'tdingiz" if result.created else "Tizimga kirdingiz"
    await message.answer(
        f"{action}: @{result.user.username}\n\n"
        "Buyruqlar:\n"
        "/karta - To'lov kartasini ko'rish\n"
        "/toladim - To'lov qilganimni adminga yuborish\n"
        "/status - Holatni ko'rish"
    )
