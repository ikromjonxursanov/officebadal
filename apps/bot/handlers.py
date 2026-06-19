import asyncio
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from asgiref.sync import sync_to_async
from django.conf import settings
from django.utils import timezone

from apps.bot.notifications import (
    PAYMENT_CONFIRM_CALLBACK,
    PAYMENT_REJECT_CALLBACK,
    notify_admin_about_payment,
    notify_user_payment_confirmed,
    notify_user_payment_rejected,
)
from apps.contributions.models import Payment
from apps.contributions.receipt_validation import only_digits, validate_payment_receipt
from apps.contributions.services import (
    confirm_payment_by_admin,
    find_user_by_telegram_id,
    get_current_contribution,
    get_payment_for_current_month,
    login_with_username,
    mark_current_month_paid,
    reject_payment_by_admin,
)

router = Router()

BTN_CARD = "💳 To'lov kartasini ko'rish"
BTN_PAID = "✅ To'lov qildim"
BTN_STATUS = "📊 To'lov holatimni ko'rish"
MENU_BUTTONS = {BTN_CARD, BTN_PAID, BTN_STATUS}
MENU_COMMANDS = {'/karta', '/toladim', '/status'}
ACTION_LIMIT_COUNT = 3
ACTION_LOCK_MINUTES = 3
ACTION_WARNING_SECONDS = 5
ACTION_LOCK_MESSAGE = (
    "Chekingiz tekshiruv jarayonida.\n"
    "Haddan tashqari ko'p urindingiz.\n"
    "Iltimos, 3 daqiqadan keyin qayta urinib ko'ring."
)
_user_action_limits = {}


class PaymentStates(StatesGroup):
    waiting_for_receipt = State()


def is_admin_user(telegram_id):
    return bool(settings.ADMIN_TELEGRAM_ID) and str(telegram_id) == str(settings.ADMIN_TELEGRAM_ID)


def is_limited_menu_action(message):
    text = (message.text or '').strip()
    if text in MENU_BUTTONS:
        return True
    return text.split(maxsplit=1)[0].lower() in MENU_COMMANDS if text.startswith('/') else False


def user_action_is_locked(telegram_id, now=None):
    now = now or timezone.now()
    state = _user_action_limits.get(telegram_id)
    if state and state.get('blocked_until') and now < state['blocked_until']:
        return True

    if not state or now - state['window_started'] > timedelta(minutes=ACTION_LOCK_MINUTES):
        _user_action_limits[telegram_id] = {
            'count': 1,
            'window_started': now,
            'blocked_until': None,
        }
        return False

    if state.get('blocked_until') and now >= state['blocked_until']:
        _user_action_limits[telegram_id] = {
            'count': 1,
            'window_started': now,
            'blocked_until': None,
        }
        return False

    state['count'] += 1
    if state['count'] > ACTION_LIMIT_COUNT:
        state['blocked_until'] = now + timedelta(minutes=ACTION_LOCK_MINUTES)
        return True

    return False


async def stop_if_user_action_locked(message):
    if not is_limited_menu_action(message):
        return False
    if not user_action_is_locked(message.from_user.id):
        return False

    await show_single_lock_warning(message)
    return True


async def show_single_lock_warning(message):
    await delete_message_safely(message.bot, message.chat.id, message.message_id)

    state = _user_action_limits.setdefault(message.from_user.id, {})
    if state.get('warning_message_id'):
        return

    warning = await message.answer(ACTION_LOCK_MESSAGE)
    state['warning_message_id'] = warning.message_id
    asyncio.create_task(delete_lock_warning_later(message.bot, message.chat.id, message.from_user.id, warning.message_id))


async def delete_lock_warning_later(bot, chat_id, telegram_id, message_id):
    await asyncio.sleep(ACTION_WARNING_SECONDS)
    await delete_message_safely(bot, chat_id, message_id)

    state = _user_action_limits.get(telegram_id)
    if state and state.get('warning_message_id') == message_id:
        state['warning_message_id'] = None


async def delete_message_safely(bot, chat_id, message_id):
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass


def format_payment_details(contribution):
    if not contribution.payment_details:
        return "To'lov kartasi admin tomonidan hali kiritilmagan."

    return contribution.payment_details


def username_keyboard(username):
    if not username:
        return None

    return types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text=f'@{username}')]],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder=f'@{username}',
    )


def main_menu_keyboard():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text=BTN_CARD)],
            [types.KeyboardButton(text=BTN_PAID)],
            [types.KeyboardButton(text=BTN_STATUS)],
        ],
        resize_keyboard=True,
    )


async def get_active_user(message):
    user = await sync_to_async(find_user_by_telegram_id)(message.from_user.id)
    if not user:
        await message.answer("Avval /start orqali username bilan tizimga kiring.")
        return None
    return user


async def send_payment_card(message, state):
    user = await get_active_user(message)
    if not user:
        return

    contribution = await sync_to_async(get_current_contribution)()
    if not contribution:
        await message.answer("Hozirgi oy uchun badal hali sozlanmagan.")
        return

    payment = await sync_to_async(get_payment_for_current_month)(user)
    if payment and payment.status == Payment.Status.PENDING:
        await message.answer("Chekingiz admin tekshiruvida.", reply_markup=main_menu_keyboard())
        return
    if payment and payment.status == Payment.Status.CONFIRMED:
        await message.answer("Siz bu oy badalni to'lagansiz. Admin tasdiqlagan.", reply_markup=main_menu_keyboard())
        return

    await state.set_state(PaymentStates.waiting_for_receipt)
    await message.answer(
        "To'lov ma'lumotlari:\n\n"
        f"Karta raqami: {contribution.payment_card_number or '-'}\n"
        f"Karta egasi: {contribution.payment_card_holder or '-'}\n"
        f"To'lov summasi: {contribution.amount} so'm\n"
        f"To'lov kuni: {contribution.due_date}\n\n"
        "To'lov qilganingizdan keyin aynan shu to'lov chekini screenshot qilib yuboring.",
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("start"))
async def start_handler(message: types.Message):
    user = await sync_to_async(find_user_by_telegram_id)(message.from_user.id)
    if user:
        await message.answer(
            f"Siz @{user.username} sifatida tizimga kirgansiz.",
            reply_markup=main_menu_keyboard(),
        )
        return

    await message.answer(
        "Ro'yxatdan o'tish uchun Telegram username yuboring.\n"
        "Pastdagi tugmani bosing yoki username yozing.",
        reply_markup=username_keyboard(message.from_user.username),
    )


@router.message(Command("login"))
async def login_handler(message: types.Message):
    await message.answer(
        "Telegram username yuboring.\n"
        "Pastdagi tugmani bosing yoki username yozing.",
        reply_markup=username_keyboard(message.from_user.username),
    )


@router.message(Command("toladim"))
async def payment_handler(message: types.Message, state: FSMContext):
    if await stop_if_user_action_locked(message):
        return
    await send_payment_card(message, state)


@router.message(F.text == BTN_PAID)
async def payment_button_handler(message: types.Message, state: FSMContext):
    if await stop_if_user_action_locked(message):
        return
    await send_payment_card(message, state)


@router.message(Command("karta"))
async def card_handler(message: types.Message, state: FSMContext):
    if await stop_if_user_action_locked(message):
        return
    await send_payment_card(message, state)


@router.message(F.text == BTN_CARD)
async def card_button_handler(message: types.Message, state: FSMContext):
    if await stop_if_user_action_locked(message):
        return
    await send_payment_card(message, state)


@router.message(PaymentStates.waiting_for_receipt, F.photo)
async def payment_screenshot_handler(message: types.Message, state: FSMContext):
    user = await sync_to_async(find_user_by_telegram_id)(message.from_user.id)
    if not user:
        await message.answer("Avval /start orqali username bilan tizimga kiring.")
        return

    contribution = await sync_to_async(get_current_contribution)()
    if not contribution:
        await message.answer("Hozirgi oy uchun badal hali sozlanmagan.")
        return

    payment = await sync_to_async(get_payment_for_current_month)(user)
    if payment and payment.status == Payment.Status.PENDING:
        await message.answer("Chekingiz admin tekshiruvida.", reply_markup=main_menu_keyboard())
        await state.clear()
        return
    if payment and payment.status == Payment.Status.CONFIRMED:
        await message.answer("Siz bu oy badalni to'lagansiz. Yangi chek qabul qilinmaydi.", reply_markup=main_menu_keyboard())
        await state.clear()
        return

    relative_path = f"receipts/{contribution.month:%Y-%m}/{user.id}-{uuid4().hex}.jpg"
    receipt_path = Path(settings.MEDIA_ROOT) / relative_path
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    await message.bot.download(message.photo[-1], destination=receipt_path)

    expected_card_last4 = only_digits(contribution.payment_card_number)[-4:]
    validation = await sync_to_async(validate_payment_receipt)(
        receipt_path,
        contribution.amount,
        expected_card_last4,
    )

    manual_admin_review = validation.reason == 'AI/OCR tekshiruv sozlanmagan.'

    if not validation.is_valid and not manual_admin_review:
        receipt_path.unlink(missing_ok=True)
        await message.answer(
            "Bu rasm to'lov cheki sifatida qabul qilinmadi.\n"
            "Iltimos, aynan shu to'lovning chek screenshotini yuboring.",
            reply_markup=main_menu_keyboard(),
        )
        return

    result = await sync_to_async(mark_current_month_paid)(
        user,
        receipt_file_id=message.photo[-1].file_id,
        receipt_image=relative_path,
        receipt_ocr_text=validation.ocr_text or validation.reason,
        extracted_amount=validation.extracted_amount,
        extracted_date=validation.extracted_date,
        extracted_card_last4=validation.extracted_card_last4,
        transaction_id=validation.transaction_id,
    )
    await state.clear()

    if result:
        await sync_to_async(notify_admin_about_payment)(result.payment)
        await message.answer(
            "Chekingiz tekshiruv uchun adminga yuborildi.",
            reply_markup=main_menu_keyboard(),
        )
    else:
        receipt_path.unlink(missing_ok=True)
        await message.answer("Hozirgi oy uchun badal admin tomonidan sozlanmagan.", reply_markup=main_menu_keyboard())


@router.message(F.photo)
async def photo_without_payment_state_handler(message: types.Message):
    await message.answer(
        "Avval To'lov qilish tugmasini bosing.",
        reply_markup=main_menu_keyboard(),
    )


@router.callback_query(F.data.startswith(f'{PAYMENT_CONFIRM_CALLBACK}:'))
async def admin_confirm_payment_handler(callback: types.CallbackQuery):
    if not is_admin_user(callback.from_user.id):
        await callback.answer("Bu amal faqat admin uchun.", show_alert=True)
        return

    payment_id = int(callback.data.split(':', 1)[1])
    payment = await sync_to_async(confirm_payment_by_admin)(payment_id)
    if not payment:
        await callback.answer("Payment topilmadi.", show_alert=True)
        return

    await sync_to_async(notify_user_payment_confirmed)(payment)
    await callback.answer("To'lov tasdiqlandi.")
    if callback.message:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(f"✅ To'lov tasdiqlandi: @{payment.user.username}")


@router.callback_query(F.data.startswith(f'{PAYMENT_REJECT_CALLBACK}:'))
async def admin_reject_payment_handler(callback: types.CallbackQuery):
    if not is_admin_user(callback.from_user.id):
        await callback.answer("Bu amal faqat admin uchun.", show_alert=True)
        return

    payment_id = int(callback.data.split(':', 1)[1])
    payment = await sync_to_async(reject_payment_by_admin)(payment_id)
    if not payment:
        await callback.answer("Payment topilmadi.", show_alert=True)
        return

    await sync_to_async(notify_user_payment_rejected)(payment)
    await callback.answer("To'lov rad etildi.")
    if callback.message:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(f"⚠️ To'lov rad etildi: @{payment.user.username}")


@router.message(Command("status"))
async def status_handler(message: types.Message):
    if await stop_if_user_action_locked(message):
        return

    user = await sync_to_async(find_user_by_telegram_id)(message.from_user.id)
    if not user:
        await message.answer("Avval /start orqali username bilan tizimga kiring.")
        return

    contribution = await sync_to_async(get_current_contribution)()
    if not contribution:
        await message.answer("Hozirgi oy uchun badal hali sozlanmagan.")
        return

    payment = await sync_to_async(get_payment_for_current_month)(user)
    if payment and payment.status == Payment.Status.CONFIRMED:
        await message.answer(
            "Joriy oy holati: to'langan.\n"
            f"Summa: {payment.amount} so'm\n"
            f"Sana: {payment.paid_date}",
            reply_markup=main_menu_keyboard(),
        )
    elif payment and payment.status == Payment.Status.PENDING:
        await message.answer(
            "Joriy oy holati: tekshiruvda.\n"
            "To'lov hali tasdiqlanmagan.\n"
            "Admin javobini kuting.",
            reply_markup=main_menu_keyboard(),
        )
    elif payment and payment.status == Payment.Status.REJECTED:
        await message.answer(
            "Joriy oy holati: to'lov arizasi rad etilgan.\n"
            "Qayta yuborish uchun To'lov qildim tugmasini bosing.",
            reply_markup=main_menu_keyboard(),
        )
    else:
        await message.answer(
            "Joriy oy holati: to'lanmagan.\n"
            f"Badal: {contribution.amount} so'm\n"
            f"To'lov kuni: {contribution.due_date}\n\n"
            f"{format_payment_details(contribution)}",
            reply_markup=main_menu_keyboard(),
        )


@router.message(F.text == BTN_STATUS)
async def status_button_handler(message: types.Message):
    await status_handler(message)


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
        f"{action}: @{result.user.username}",
        reply_markup=main_menu_keyboard(),
    )
