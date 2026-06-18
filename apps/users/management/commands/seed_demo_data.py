from datetime import date

from django.core.management.base import BaseCommand

from apps.contributions.models import MonthlyContribution, Payment
from apps.duties.models import DutyAssignment, DutyCycle
from apps.expenses.models import Expense
from apps.users.models import User


class Command(BaseCommand):
    help = 'Create sample demo data for local testing'

    def handle(self, *args, **options):
        # Users
        users = []
        for index, name in enumerate([
            ('Ali', 'Aliyev'),
            ('Vali', 'Valiyev'),
            ('Hasan', 'Hasanov'),
            ('Gani', 'Ganiev'),
        ], start=1):
            user, created = User.objects.get_or_create(
                username=f'user{index}',
                defaults={
                    'first_name': name[0],
                    'last_name': name[1],
                    'phone': f'+99890{index}00000',
                    'is_active': True,
                },
            )
            users.append(user)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created user: {user.username}'))

        # Monthly contribution
        today = date.today()
        contribution, created = MonthlyContribution.objects.get_or_create(
            month=today.replace(day=1),
            defaults={
                'amount': 50000,
                'due_date': today.replace(day=5),
                'is_active': True,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Created demo contribution'))

        # Sample payments for first user
        if users:
            Payment.objects.get_or_create(
                user=users[0],
                contribution=contribution,
                defaults={'amount': contribution.amount},
            )

        # Duty cycle and assignment
        duty_cycle, _ = DutyCycle.objects.get_or_create(
            name='Bozorlik navbati',
            defaults={'is_active': True},
        )
        DutyAssignment.objects.get_or_create(
            duty_cycle=duty_cycle,
            month=today.replace(day=1),
            defaults={'user': users[1] if len(users) > 1 else users[0]},
        )

        # Expense sample
        Expense.objects.get_or_create(
            date=today,
            category='coffee',
            amount=12000,
            defaults={
                'description': 'Demo coffee expense',
                'added_by': users[0],
            },
        )

        self.stdout.write(self.style.SUCCESS('Demo data setup completed.'))
