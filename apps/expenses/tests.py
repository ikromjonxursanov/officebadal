from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.expenses.models import Expense
from apps.users.models import User


class ExpenseModelTests(TestCase):
    def test_expense_str(self):
        user = User.objects.create_user(username='admin_1', password='test-pass')
        expense = Expense.objects.create(
            title='Choy',
            amount=Decimal('25000.00'),
            date=timezone.localdate(),
            created_by=user,
        )

        self.assertIn('Choy', str(expense))
