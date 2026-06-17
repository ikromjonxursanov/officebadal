# bot/admin.py
from django.contrib import admin
from apps.users.models import User
from apps.contributions.models import MonthlyContribution, Payment
from apps.duties.models import DutyCycle, DutyAssignment
from apps.expenses.models import Expense

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'username', 'telegram_id', 'phone', 'is_active']
    list_filter = ['is_active']
    search_fields = ['first_name', 'last_name', 'telegram_id']


@admin.register(MonthlyContribution)
class MonthlyContributionAdmin(admin.ModelAdmin):
    list_display = ['month', 'amount', 'due_date', 'is_active']
    list_filter = ['is_active']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['user', 'contribution', 'amount', 'paid_at']
    list_filter = ['paid_at']


@admin.register(DutyCycle)
class DutyCycleAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']


@admin.register(DutyAssignment)
class DutyAssignmentAdmin(admin.ModelAdmin):
    list_display = ['duty_cycle', 'user', 'month']


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['category', 'amount', 'date', 'added_by']
    list_filter = ['category', 'date']