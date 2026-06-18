from django.contrib import admin

from apps.expenses.models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('date', 'category', 'amount', 'added_by', 'description')
    list_filter = ('category', 'date')
    search_fields = ('description', 'added_by__username')
    ordering = ('-date',)
