from django.contrib import admin
from django.utils.html import format_html

from apps.contributions.models import MonthlyContribution, Payment


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    autocomplete_fields = ('user',)
    readonly_fields = ('paid_at', 'receipt_link')
    fields = ('user', 'amount', 'payment_method', 'status', 'paid_at', 'receipt_link', 'receipt_file_id', 'note')

    def receipt_link(self, obj):
        if obj and obj.receipt_image:
            return format_html('<a href="{}" target="_blank">Skrinshotni ochish</a>', obj.receipt_image.url)
        return '-'
    receipt_link.short_description = 'Skrinshot'


@admin.register(MonthlyContribution)
class MonthlyContributionAdmin(admin.ModelAdmin):
    list_display = ('month', 'amount', 'due_date', 'is_active', 'paid_count', 'pending_count', 'unpaid_count')
    list_filter = ('is_active', 'month')
    search_fields = ('month',)
    date_hierarchy = 'due_date'
    fieldsets = (
        ('Badal', {
            'fields': ('month', 'amount', 'due_date', 'is_active'),
        }),
        ("To'lov kartasi", {
            'fields': ('payment_card_number', 'payment_card_holder'),
        }),
    )
    inlines = (PaymentInline,)

    def paid_count(self, obj):
        return obj.payments.filter(status=Payment.Status.APPROVED).count()
    paid_count.short_description = "To'laganlar"

    def pending_count(self, obj):
        return obj.payments.filter(status=Payment.Status.PENDING).count()
    pending_count.short_description = 'Kutilmoqda'

    def unpaid_count(self, obj):
        return obj.unpaid_users_count
    unpaid_count.short_description = "To'lamaganlar"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'contribution', 'amount', 'status', 'payment_method', 'receipt_link', 'paid_at')
    list_filter = ('status', 'contribution', 'payment_method', 'paid_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    autocomplete_fields = ('user',)
    date_hierarchy = 'paid_at'
    actions = ('approve_payments', 'reject_payments')

    readonly_fields = ('receipt_link',)

    def receipt_link(self, obj):
        if obj.receipt_image:
            return format_html('<a href="{}" target="_blank">Skrinshotni ochish</a>', obj.receipt_image.url)
        if obj.receipt_file_id:
            return 'Telegram file_id bor, lekin lokal rasm saqlanmagan'
        return '-'
    receipt_link.short_description = 'Skrinshot'

    @admin.action(description="Tanlangan to'lovlarni tasdiqlash")
    def approve_payments(self, request, queryset):
        updated = queryset.update(status=Payment.Status.APPROVED)
        self.message_user(request, f"{updated} ta to'lov tasdiqlandi.")

    @admin.action(description="Tanlangan to'lovlarni rad etish")
    def reject_payments(self, request, queryset):
        updated = queryset.update(status=Payment.Status.REJECTED)
        self.message_user(request, f"{updated} ta to'lov rad etildi.")
