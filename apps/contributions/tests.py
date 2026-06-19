from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.contributions.models import MonthlyContribution, Payment
from apps.contributions.receipt_validation import validate_ocr_text
from apps.contributions.services import (
    find_user_by_telegram_username,
    get_current_contribution,
    get_unpaid_users,
    find_user_by_telegram_id,
    login_with_username,
    submit_current_month_payment,
)
from apps.users.models import User


class ContributionServiceTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.month_start = self.today.replace(day=1)
        self.user = User.objects.create_user(
            username='ali_1',
            password='test-pass',
            first_name='Ali',
        )
        self.contribution = MonthlyContribution.objects.create(
            month=self.month_start,
            amount=Decimal('50000.00'),
            due_date=self.month_start,
        )

    def test_find_user_by_telegram_username_accepts_at_prefix(self):
        self.assertEqual(find_user_by_telegram_username('@Ali_1'), self.user)

    def test_login_with_username_creates_user_and_saves_chat_id(self):
        result = login_with_username(
            username='@vali_123',
            telegram_id=12345,
            first_name='Vali',
        )

        self.assertTrue(result.created)
        self.assertEqual(result.user.username, 'vali_123')
        self.assertEqual(result.user.telegram_id, 12345)
        self.assertEqual(find_user_by_telegram_id(12345), result.user)

    def test_login_with_username_links_existing_user(self):
        result = login_with_username(
            username='@Ali_1',
            telegram_id=12345,
            first_name='Ali Valiyev',
        )
        self.user.refresh_from_db()

        self.assertFalse(result.created)
        self.assertEqual(self.user.telegram_id, 12345)

    def test_submit_current_month_payment_creates_pending_payment_once(self):
        first = submit_current_month_payment(
            self.user,
            receipt_file_id='photo-file-id',
            receipt_image='receipts/test.jpg',
            receipt_ocr_text="Muvaffaqiyatli to'lov 50000",
        )
        second = submit_current_month_payment(
            self.user,
            receipt_file_id='photo-file-id',
            receipt_image='receipts/test.jpg',
            receipt_ocr_text="Muvaffaqiyatli to'lov 50000",
        )

        self.assertTrue(first.created)
        self.assertFalse(second.created)
        self.assertEqual(first.payment.amount, self.contribution.amount)
        self.assertEqual(first.payment.status, Payment.Status.PENDING)
        self.assertEqual(first.payment.receipt_file_id, 'photo-file-id')
        self.assertEqual(first.payment.receipt_image.name, 'receipts/test.jpg')
        self.assertEqual(first.payment.receipt_ocr_text, "Muvaffaqiyatli to'lov 50000")
        self.assertEqual(first.payment.paid_month, self.contribution.month)
        self.assertEqual(self.contribution.payments.count(), 1)

    def test_rejected_payment_can_be_resubmitted(self):
        result = submit_current_month_payment(
            self.user,
            receipt_file_id='old-photo',
            receipt_image='receipts/old.jpg',
            receipt_ocr_text='old ocr',
        )
        result.payment.status = Payment.Status.REJECTED
        result.payment.save(update_fields=['status'])

        second = submit_current_month_payment(
            self.user,
            receipt_file_id='new-photo',
            receipt_image='receipts/new.jpg',
            receipt_ocr_text='new ocr',
        )

        self.assertFalse(second.created)
        self.assertTrue(second.resubmitted)
        self.assertEqual(second.payment.status, Payment.Status.PENDING)
        self.assertEqual(second.payment.receipt_file_id, 'new-photo')
        self.assertEqual(second.payment.receipt_image.name, 'receipts/new.jpg')
        self.assertEqual(second.payment.receipt_ocr_text, 'new ocr')

    def test_get_current_contribution_uses_month_start(self):
        contribution = get_current_contribution(self.today)

        self.assertEqual(contribution, self.contribution)

    def test_get_unpaid_users_excludes_paid_users(self):
        unpaid_user = User.objects.create_user(username='vali', password='test-pass')
        unpaid_user.telegram_id = 54321
        unpaid_user.save(update_fields=['telegram_id'])
        login_with_username(username='ali_1', telegram_id=12345)
        payment = submit_current_month_payment(self.user).payment
        payment.status = Payment.Status.CONFIRMED
        payment.save(update_fields=['status'])

        self.assertEqual(list(get_unpaid_users(self.contribution)), [unpaid_user])

    def test_validate_ocr_text_accepts_matching_receipt(self):
        today = timezone.localdate()
        ocr_text = (
            "Muvaffaqiyatli to'lov\n"
            "To'lov summasi: 50000 so'm\n"
            "Qabul qiluvchining kartasi: 9860 24** **** 5846\n"
            f"Sana: {today:%d.%m.%Y}"
        )

        result = validate_ocr_text(ocr_text, Decimal('50000.00'), '5846')

        self.assertTrue(result.is_valid)

    def test_validate_ocr_text_rejects_wrong_amount(self):
        today = timezone.localdate()
        ocr_text = (
            "Muvaffaqiyatli to'lov\n"
            "To'lov summasi: 72000 so'm\n"
            "Qabul qiluvchining kartasi: 9860 24** **** 5846\n"
            f"Sana: {today:%d.%m.%Y}"
        )

        result = validate_ocr_text(ocr_text, Decimal('50000.00'), '5846')

        self.assertFalse(result.is_valid)
        self.assertEqual(result.reason, "To'lov summasi mos kelmadi.")
