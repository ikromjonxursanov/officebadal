from datetime import date

from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from asgiref.sync import sync_to_async

from apps.contributions.models import MonthlyContribution, Payment
from apps.users.models import User

router = Router()


class UsernameStates(StatesGroup):
    waiting_for_username = State()


def _normalize_username(value: str) -> str:
    value = value.strip()
    if value.startswith('@'):
        value = value[1:]
    return value


def _build_menu() -> types.ReplyKeyboardMarkup:
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [
                types.KeyboardButton(text='Mening statusim'),
                types.KeyboardButton(text='To\'lov qilganlar'),
            ],
            [
                types.KeyboardButton(text='To\'lov qilmaganlar'),
            ],
        ],
        resize_keyboard=True,
    )


async def _get_current_contribution():
    today = date.today()
    first_day = today.replace(day=1)
    return await sync_to_async(
        lambda: MonthlyContribution.objects.filter(
            month=first_day,
            is_active=True,
        ).first()
    )()


async def _get_user_by_telegram(telegram_id: int):
    return await sync_to_async(
        lambda: User.objects.filter(telegram_id=telegram_id).first()
    )()


async def _get_user_by_username(username: str):
    return await sync_to_async(
        lambda: User.objects.filter(username=username).first()
    )()


async def _get_user_payment_status(user, contribution):
    return await sync_to_async(
        lambda: Payment.objects.filter(
            user=user,
            contribution=contribution,
            status=Payment.STATUS_APPROVED,
        ).exists()
    )()


@router.message(CommandStart())
async def start_handler(
    message: types.Message,
    state: FSMContext,
):
    await state.set_state(UsernameStates.waiting_for_username)
    await message.answer(
        'Iltimos, login uchun username yuboring.',
        reply_markup=types.ReplyKeyboardRemove(),
    )


@router.message(UsernameStates.waiting_for_username)
async def login_handler(
    message: types.Message,
    state: FSMContext,
):
    username = _normalize_username(message.text or '')

    if not username:
        await message.answer('Iltimos, username ni to\'g\'ri yuboring.')
        return

    user = await _get_user_by_username(username)
    if not user:
        await message.answer(
            'Bunday username topilmadi. Admin bilan bog\'laning.'
        )
        return

    await sync_to_async(
        lambda: User.objects.filter(pk=user.pk).update(
            telegram_id=message.from_user.id,
        )
    )()
    await state.clear()
    await message.answer(
        f'Login muvaffaqiyatli bo\'ldi, {user.get_full_name() or username}.',
        reply_markup=_build_menu(),
    )


@router.message(lambda message: message.text == 'Mening statusim')
async def my_status_handler(message: types.Message):
    user = await _get_user_by_telegram(message.from_user.id)
    if not user:
        await message.answer(
            'Iltimos, avval /start buyrug\'i orqali login qiling.'
        )
        return

    contribution = await _get_current_contribution()
    if not contribution:
        await message.answer('Hozirgi oy uchun badal sozlanmagan.')
        return

    paid = await _get_user_payment_status(user, contribution)
    text = (
        'Siz bu oy uchun to\'lov qilgansiz.'
        if paid
        else 'Siz bu oy uchun hali to\'lov qilmagansiz.'
    )
    await message.answer(text, reply_markup=_build_menu())


@router.message(lambda message: message.text == 'To\'lov qilganlar')
async def paid_users_handler(message: types.Message):
    contribution = await _get_current_contribution()
    if not contribution:
        await message.answer('Hozirgi oy uchun badal sozlanmagan.')
        return

    payments = await sync_to_async(
        lambda: list(
            Payment.objects.filter(
                contribution=contribution,
                status=Payment.STATUS_APPROVED,
            )
            .select_related('user')
            .order_by('-paid_at')
        )
    )()

    if not payments:
        await message.answer(
            'Hozircha bu oy uchun to\'lov qilganlar yo\'q.',
            reply_markup=_build_menu(),
        )
        return

    lines = [
        f"{p.user.get_full_name() or p.user.username} — {p.amount} so'm — {p.paid_at.strftime('%d.%m.%Y')}"
        for p in payments
    ]
    await message.answer(
        '\n'.join(lines),
        reply_markup=_build_menu(),
    )


@router.message(lambda message: message.text == 'To\'lov qilmaganlar')
async def unpaid_users_handler(message: types.Message):
    contribution = await _get_current_contribution()
    if not contribution:
        await message.answer('Hozirgi oy uchun badal sozlanmagan.')
        return

    paid_user_ids = await sync_to_async(
        lambda: list(
            Payment.objects.filter(
                contribution=contribution,
                status=Payment.STATUS_APPROVED,
            ).values_list('user_id', flat=True)
        )
    )()

    users = await sync_to_async(
        lambda: list(
            User.objects.filter(
                is_active=True,
            ).exclude(id__in=paid_user_ids)
            .order_by('first_name', 'last_name')
        )
    )()

    if not users:
        await message.answer(
            'Barcha foydalanuvchilar bu oy uchun to\'lov qilgan.',
            reply_markup=_build_menu(),
        )
        return

    lines = [
        user.get_full_name() or user.username or f'User {user.telegram_id}'
        for user in users
    ]
    await message.answer(
        '\n'.join(lines),
        reply_markup=_build_menu(),
    )
