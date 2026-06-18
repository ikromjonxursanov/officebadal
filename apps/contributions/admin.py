from django.contrib import admin
from django.utils import timezone

from apps.contributions.models import MonthlyContribution, Payment


@admin.register(MonthlyContribution)
class MonthlyContributionAdmin(admin.ModelAdmin):
    list_display = (
        'month',
        'amount',
        'due_date',
        'is_active',
        'payment_card_number',
        'payment_card_holder'
    )
    list_filter = ('is_active',)
    search_fields = ('month', 'payment_card_number', 'payment_card_holder')
    fieldsets = (
        ('Asosiy ma`lumot', {
            'fields': ('month', 'amount', 'due_date', 'is_active')
        }),
        ('To`lov ma`lumotlari', {
            'fields': (
                'payment_card_number',
                'payment_card_holder',
                'payment_note'
            )
        }),
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'contribution',
        'amount',
        'status',
        'payment_method',
        'submitted_at',
        'paid_at',
    )
    list_filter = ('status', 'payment_method', 'submitted_at', 'paid_at')
    search_fields = (
        'user__username',
        'user__first_name',
        'user__last_name',
        'contribution__month',
    )
    readonly_fields = ('submitted_at', 'paid_at')
    fieldsets = (
        ('Asosiy ma`lumot', {
            'fields': ('user', 'contribution', 'amount', 'status')
        }),
        ('To`lov tafsiloti', {
            'fields': ('payment_method', 'note', 'submitted_at', 'paid_at')
        }),
        ('Tasdiqlovchi', {
            'fields': ('approved_by',)
        }),
    )

    actions = ['mark_as_approved', 'mark_as_rejected']

    @admin.action(description='Tanlangan to`lovlarni tasdiqlash')
    def mark_as_approved(self, request, queryset):
        queryset.update(
            status=Payment.STATUS_APPROVED,
            approved_by=request.user,
            paid_at=timezone.now(),
        )

    @admin.action(description='Tanlangan to`lovlarni rad etish')
    def mark_as_rejected(self, request, queryset):
        queryset.update(
            status=Payment.STATUS_REJECTED,
            approved_by=request.user,
            paid_at=None,
        )
