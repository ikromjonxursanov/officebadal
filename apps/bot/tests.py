from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.bot.handlers import _user_action_limits, user_action_is_locked
from apps.bot.notifications import notify_admin_about_payment
from apps.contributions.models import MonthlyContribution, Payment
from apps.users.models import User


class MenuActionLimitTests(TestCase):
    def setUp(self):
        _user_action_limits.clear()

    def test_user_is_locked_after_more_than_three_actions_for_three_minutes(self):
        telegram_id = 777
        now = timezone.now()

        self.assertFalse(user_action_is_locked(telegram_id, now=now))
        self.assertFalse(user_action_is_locked(telegram_id, now=now))
        self.assertFalse(user_action_is_locked(telegram_id, now=now))
        self.assertTrue(user_action_is_locked(telegram_id, now=now))
        self.assertTrue(user_action_is_locked(telegram_id, now=now + timedelta(minutes=2)))
        self.assertFalse(user_action_is_locked(telegram_id, now=now + timedelta(minutes=3, seconds=1)))


class AdminNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='ali',
            password='test-pass',
            first_name='Ali',
            telegram_id=12345,
        )
        self.contribution = MonthlyContribution.objects.create(
            month=date(2026, 6, 1),
            amount=Decimal('50000.00'),
            due_date=date(2026, 6, 5),
        )

    @override_settings(ADMIN_TELEGRAM_ID='777', TELEGRAM_BOT_TOKEN='token')
    def test_admin_notification_sends_receipt_photo_when_image_exists(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            receipt_path = Path(media_root) / 'receipts/test.jpg'
            receipt_path.parent.mkdir(parents=True, exist_ok=True)
            with open(receipt_path, 'wb') as receipt_file:
                receipt_file.write(b'fake image')

            payment = Payment.objects.create(
                user=self.user,
                contribution=self.contribution,
                amount=self.contribution.amount,
                status=Payment.Status.PENDING,
                receipt_image='receipts/test.jpg',
                paid_month=self.contribution.month,
            )

            with patch('apps.bot.notifications.send_telegram_photo', return_value=True) as send_photo:
                self.assertTrue(notify_admin_about_payment(payment))

            send_photo.assert_called_once()
            _, photo_path, caption = send_photo.call_args.args
            self.assertEqual(photo_path, receipt_path)
            self.assertIn("Yangi to'lov cheki", caption)
            self.assertIn('@ali', caption)
            self.assertIn('50 000', caption)
            self.assertIn('pending', caption)

    @override_settings(ADMIN_TELEGRAM_ID='777', TELEGRAM_BOT_TOKEN='token')
    def test_admin_notification_falls_back_to_text_when_image_missing(self):
        payment = Payment.objects.create(
            user=self.user,
            contribution=self.contribution,
            amount=self.contribution.amount,
            status=Payment.Status.PENDING,
            receipt_image='receipts/missing.jpg',
            paid_month=self.contribution.month,
        )

        with patch('apps.bot.notifications.send_telegram_message', return_value=True) as send_message:
            self.assertTrue(notify_admin_about_payment(payment))

        send_message.assert_called_once()
        self.assertIn("Yangi to'lov cheki", send_message.call_args.args[1])
