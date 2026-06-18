from dataclasses import dataclass
from datetime import date
import re

from django.db.models import QuerySet
from django.utils import timezone

from apps.contributions.models import MonthlyContribution, Payment
from apps.users.models import User


def normalize_telegram_username(username: str | None) -> str:
    return (username or '').strip().lstrip('@').lower()


def is_valid_telegram_username(username: str | None) -> bool:
    normalized = normalize_telegram_username(username)
    return bool(re.fullmatch(r'[a-z0-9_]{5,32}', normalized))


def current_month_start(today: date | None = None) -> date:
    today = today or timezone.localdate()
    return today.replace(day=1)


def get_current_contribution(today: date | None = None) -> MonthlyContribution | None:
    return MonthlyContribution.objects.filter(
        month=current_month_start(today),
        is_active=True,
    ).first()


def find_user_by_telegram_username(username: str | None) -> User | None:
    normalized = normalize_telegram_username(username)
    if not normalized:
        return None

    return User.objects.filter(
        username__iregex=rf'^@?{re.escape(normalized)}$',
        is_active=True,
    ).first()


def find_user_by_telegram_id(telegram_id: int | None) -> User | None:
    if not telegram_id:
        return None

    return User.objects.filter(telegram_id=telegram_id, is_active=True).first()


@dataclass(frozen=True)
class LoginResult:
    user: User
    created: bool
    relinked: bool


def login_with_username(*, username: str, telegram_id: int, first_name: str = '') -> LoginResult:
    normalized = normalize_telegram_username(username)
    if not is_valid_telegram_username(normalized):
        raise ValueError("Telegram username 5-32 ta belgi bo'lishi kerak: harf, raqam yoki _")

    linked_user = find_user_by_telegram_id(telegram_id)
    existing_user = find_user_by_telegram_username(normalized)

    if existing_user and existing_user.telegram_id and existing_user.telegram_id != telegram_id:
        raise ValueError("Bu username boshqa Telegram akkauntga ulangan.")

    if linked_user and existing_user and linked_user.id != existing_user.id:
        linked_user.telegram_id = None
        linked_user.save(update_fields=['telegram_id'])

    if existing_user:
        user = existing_user
        created = False
    elif linked_user:
        user = linked_user
        user.username = normalized
        created = False
    else:
        user = User(username=normalized)
        user.set_unusable_password()
        created = True

    user.telegram_id = telegram_id
    if first_name and not user.first_name:
        user.first_name = first_name[:150]
    user.save()

    return LoginResult(
        user=user,
        created=created,
        relinked=bool(linked_user and linked_user.id != user.id),
    )


def link_telegram_user(*, user: User, telegram_id: int, first_name: str = '') -> User:
    user.telegram_id = telegram_id
    if first_name and not user.first_name:
        user.first_name = first_name[:150]
    user.save(update_fields=['telegram_id', 'first_name'])
    return user


@dataclass(frozen=True)
class PaymentResult:
    payment: Payment
    created: bool
    resubmitted: bool = False


def submit_current_month_payment(
    user: User,
    receipt_file_id: str = '',
    receipt_image: str = '',
) -> PaymentResult | None:
    contribution = get_current_contribution()
    if not contribution:
        return None

    payment, created = Payment.objects.get_or_create(
        user=user,
        contribution=contribution,
        defaults={
            'amount': contribution.amount,
            'payment_method': 'Telegram',
            'note': 'Bot orqali belgilandi',
            'status': Payment.Status.PENDING,
            'receipt_file_id': receipt_file_id,
            'receipt_image': receipt_image,
        },
    )
    resubmitted = False
    if not created and payment.status == Payment.Status.REJECTED:
        payment.status = Payment.Status.PENDING
        payment.paid_at = timezone.now()
        payment.note = 'Bot orqali qayta yuborildi'
        payment.receipt_file_id = receipt_file_id
        payment.receipt_image = receipt_image
        payment.save(update_fields=['status', 'paid_at', 'note', 'receipt_file_id', 'receipt_image'])
        resubmitted = True

    return PaymentResult(payment=payment, created=created, resubmitted=resubmitted)


def mark_current_month_paid(
    user: User,
    receipt_file_id: str = '',
    receipt_image: str = '',
) -> PaymentResult | None:
    return submit_current_month_payment(
        user,
        receipt_file_id=receipt_file_id,
        receipt_image=receipt_image,
    )


def get_unpaid_users(contribution: MonthlyContribution) -> QuerySet[User]:
    return User.objects.filter(
        is_active=True,
        telegram_id__isnull=False,
    ).exclude(
        payments__contribution=contribution,
        payments__status__in=[Payment.Status.PENDING, Payment.Status.APPROVED],
    ).order_by('first_name', 'username')


def get_payment_for_current_month(user: User) -> Payment | None:
    contribution = get_current_contribution()
    if not contribution:
        return None

    return Payment.objects.filter(user=user, contribution=contribution).first()
