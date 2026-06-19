from django.contrib import admin
from django import forms
from django.http import HttpResponse
from django.utils.html import format_html
from openpyxl import Workbook

from apps.bot.notifications import notify_user_payment_confirmed, notify_user_payment_rejected
from apps.contributions.models import ContributionSetting, MonthlyContribution, Payment


class PaymentAdminForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        reject_reason = cleaned_data.get('reject_reason', '')
        if status == Payment.Status.REJECTED and not reject_reason.strip():
            self.add_error('reject_reason', "Rad etilganda sabab yozilishi shart.")
        return cleaned_data


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    autocomplete_fields = ('user',)
    readonly_fields = ('paid_at', 'receipt_link')
    fields = (
        'user',
        'amount',
        'payment_method',
        'status',
        'paid_at',
        'receipt_link',
        'receipt_ocr_text',
        'extracted_amount',
        'extracted_date',
        'extracted_card_last4',
        'transaction_id',
        'reject_reason',
        'note',
    )

    def receipt_link(self, obj):
        if obj and obj.receipt_image:
            return format_html(
                '<a href="{0}" target="_blank">Skrinshotni ochish</a><br>'
                '<img src="{0}" style="max-width: 220px; max-height: 320px; margin-top: 8px;" />',
                obj.receipt_image.url,
            )
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
        return obj.payments.filter(status=Payment.Status.CONFIRMED).count()
    paid_count.short_description = "To'laganlar"

    def pending_count(self, obj):
        return obj.payments.filter(status=Payment.Status.PENDING).count()
    pending_count.short_description = 'Kutilmoqda'

    def unpaid_count(self, obj):
        return obj.unpaid_users_count
    unpaid_count.short_description = "To'lamaganlar"


@admin.register(ContributionSetting)
class ContributionSettingAdmin(admin.ModelAdmin):
    list_display = ('amount', 'due_day', 'payment_card_holder', 'is_active', 'created_at')
    list_filter = ('is_active',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    form = PaymentAdminForm
    list_display = ('user', 'contribution', 'amount', 'status', 'payment_method', 'receipt_link', 'paid_at')
    list_filter = ('paid_month', 'status', 'contribution', 'payment_method', 'paid_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    autocomplete_fields = ('user',)
    date_hierarchy = 'paid_at'
    actions = ('approve_payments', 'reject_payments', 'export_selected_payments_to_excel')

    readonly_fields = ('paid_at', 'receipt_link')
    fieldsets = (
        ("To'lov", {
            'fields': ('user', 'contribution', 'amount', 'paid_month', 'payment_method', 'status', 'paid_at'),
        }),
        ('Chek', {
            'fields': (
                'receipt_link',
                'receipt_ocr_text',
                'extracted_amount',
                'extracted_date',
                'extracted_card_last4',
                'transaction_id',
            ),
        }),
        ('Admin qarori', {
            'fields': ('reject_reason', 'note'),
        }),
    )

    def receipt_link(self, obj):
        if obj.receipt_image:
            return format_html(
                '<a href="{0}" target="_blank">Skrinshotni ochish</a><br>'
                '<img src="{0}" style="max-width: 260px; max-height: 380px; margin-top: 8px;" />',
                obj.receipt_image.url,
            )
        if obj.receipt_file_id:
            return 'Telegram file_id bor, lekin lokal rasm saqlanmagan'
        return '-'
    receipt_link.short_description = 'Skrinshot'

    @admin.action(description="Tanlangan to'lovlarni tasdiqlash")
    def approve_payments(self, request, queryset):
        updated = 0
        for payment in queryset.select_related('user', 'contribution'):
            old_status = payment.status
            payment.status = Payment.Status.CONFIRMED
            payment.reject_reason = ''
            payment.full_clean()
            payment.save(update_fields=['status', 'reject_reason'])
            if old_status != Payment.Status.CONFIRMED:
                notify_user_payment_confirmed(payment)
            updated += 1
        self.message_user(request, f"{updated} ta to'lov tasdiqlandi.")

    @admin.action(description="Tanlangan to'lovlarni rad etish")
    def reject_payments(self, request, queryset):
        payments = list(queryset.select_related('user', 'contribution'))
        missing_reason = [payment for payment in payments if not payment.reject_reason.strip()]
        if missing_reason:
            self.message_user(
                request,
                "Rad etish uchun avval har bir payment ichida reject reason yozing.",
                level='ERROR',
            )
            return

        updated = 0
        for payment in payments:
            old_status = payment.status
            payment.status = Payment.Status.REJECTED
            payment.full_clean()
            payment.save(update_fields=['status'])
            if old_status != Payment.Status.REJECTED:
                notify_user_payment_rejected(payment)
            updated += 1
        self.message_user(request, f"{updated} ta to'lov rad etildi.")

    @admin.action(description='Export selected payments to Excel')
    def export_selected_payments_to_excel(self, request, queryset):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = 'Payments'
        sheet.append([
            'Telegram username',
            'Month',
            'Amount',
            'Status',
            'Paid date / created date',
            'Confirmed date',
            'Reject reason',
        ])

        for payment in queryset.select_related('user', 'contribution').order_by('paid_month', 'user__username'):
            sheet.append([
                payment.user.username,
                payment.paid_month.strftime('%Y-%m') if payment.paid_month else payment.contribution.month.strftime('%Y-%m'),
                float(payment.amount),
                payment.status,
                payment.paid_at.strftime('%Y-%m-%d %H:%M'),
                payment.paid_at.strftime('%Y-%m-%d %H:%M') if payment.status == Payment.Status.CONFIRMED else '',
                payment.reject_reason,
            ])

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = 'attachment; filename="payments.xlsx"'
        workbook.save(response)
        return response

    def save_model(self, request, obj, form, change):
        old_status = None
        if change and obj.pk:
            old_status = Payment.objects.filter(pk=obj.pk).values_list('status', flat=True).first()

        super().save_model(request, obj, form, change)

        if old_status == obj.status:
            return
        if obj.status == Payment.Status.CONFIRMED:
            notify_user_payment_confirmed(obj)
        elif obj.status == Payment.Status.REJECTED:
            notify_user_payment_rejected(obj)
