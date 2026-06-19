from django.contrib import admin
from django.db.models import Sum

from apps.contributions.models import Payment
from apps.expenses.models import Expense
from apps.users.models import User


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('title', 'amount', 'date', 'created_by', 'created_at')
    list_filter = ('date', 'created_by')
    search_fields = ('title', 'description', 'created_by__username')
    date_hierarchy = 'date'

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def changelist_view(self, request, extra_context=None):
        confirmed_total = Payment.objects.filter(
            status=Payment.Status.CONFIRMED,
        ).aggregate(total=Sum('amount'))['total'] or 0
        expense_total = Expense.objects.aggregate(total=Sum('amount'))['total'] or 0
        pending_count = Payment.objects.filter(status=Payment.Status.PENDING).count()
        confirmed_count = Payment.objects.filter(status=Payment.Status.CONFIRMED).count()
        active_users = User.objects.filter(is_active=True).count()

        extra_context = extra_context or {}
        extra_context['office_summary'] = {
            'confirmed_total': confirmed_total,
            'expense_total': expense_total,
            'balance': confirmed_total - expense_total,
            'active_users': active_users,
            'confirmed_count': confirmed_count,
            'pending_count': pending_count,
            'unpaid_count': max(active_users - confirmed_count - pending_count, 0),
        }
        return super().changelist_view(request, extra_context=extra_context)
