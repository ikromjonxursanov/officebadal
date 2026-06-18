from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class MonthlyContribution(models.Model):
    """Har oy uchun badal summasi va to'lov sanasi."""
    month = models.DateField(unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateField()
    payment_card_number = models.CharField(
        max_length=40,
        blank=True,
        verbose_name='Karta raqami',
    )
    payment_card_holder = models.CharField(
        max_length=120,
        blank=True,
        verbose_name='Karta egasi',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Oylik badal'
        verbose_name_plural = 'Oylik badallar'
        ordering = ['-month']

    def __str__(self):
        return f"{self.month.strftime('%Y-%m')} - {self.amount} so'm"

    @property
    def payment_details(self):
        lines = []
        if self.payment_card_number:
            lines.append(f"Karta: {self.payment_card_number}")
        if self.payment_card_holder:
            lines.append(f"Karta egasi: {self.payment_card_holder}")
        return '\n'.join(lines)

    @property
    def unpaid_users_count(self):
        user_model = settings.AUTH_USER_MODEL
        return self._meta.apps.get_model(user_model).objects.filter(
            is_active=True
        ).exclude(
            payments__contribution=self,
            payments__status=Payment.Status.APPROVED,
        ).count()

    def clean(self):
        if self.month and self.month.day != 1:
            raise ValidationError({
                'month': "Oy maydoni oyning 1-sanasi bo'lishi kerak."
            })

        if self.month and self.due_date:
            if self.due_date.year != self.month.year or self.due_date.month != self.month.month:
                raise ValidationError({
                    'due_date': "To'lov kuni badal oyining ichida bo'lishi kerak."
                })


class Payment(models.Model):
    """Har bir foydalanuvchining badal to'lovi."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Tasdiqlash kutilmoqda'
        APPROVED = 'approved', 'Tasdiqlandi'
        REJECTED = 'rejected', 'Rad etildi'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    contribution = models.ForeignKey(
        MonthlyContribution,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_at = models.DateTimeField(default=timezone.now, editable=False)
    payment_method = models.CharField(max_length=50, default='Naqd')
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    receipt_file_id = models.CharField(max_length=255, blank=True)
    receipt_image = models.FileField(upload_to='receipts/', blank=True)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "To'lov"
        verbose_name_plural = "To'lovlar"
        unique_together = ('user', 'contribution')
        ordering = ['-paid_at']

    def __str__(self):
        return f"{self.user} - {self.contribution} - {self.amount}"

    @property
    def paid_date(self):
        return timezone.localtime(self.paid_at).date()
