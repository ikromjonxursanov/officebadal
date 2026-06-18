from django.conf import settings
from django.db import models


class MonthlyContribution(models.Model):
    """Har oy uchun badal summasi va to'lov sanasi."""
    month = models.DateField(unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateField()
    is_active = models.BooleanField(default=True)
    payment_card_number = models.CharField(
        max_length=40,
        blank=True,
        default='',
        verbose_name='Karta raqami'
    )
    payment_card_holder = models.CharField(
        max_length=120,
        blank=True,
        default='',
        verbose_name='Karta egasi'
    )
    payment_note = models.TextField(
        blank=True,
        default='',
        verbose_name='To`lov ko`rsatmasi'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Oylik badal'
        verbose_name_plural = 'Oylik badallar'
        ordering = ['-month']

    def __str__(self):
        return f"{self.month.strftime('%Y-%m')} - {self.amount} so'm"


class Payment(models.Model):
    """Har bir foydalanuvchining badal to'lovi.

    `status` orqali to'lovning holati saqlanadi:
    - pending: foydalanuvchi to'lov so'ragan, admin tasdiqlashi kerak
    - approved: admin tasdiqlagan, to'lov rasmiy ravishda qabul qilingan
    - rejected: admin rad etgan
    """
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Kutilmoqda'),
        (STATUS_APPROVED, 'Tasdiqlandi'),
        (STATUS_REJECTED, 'Rad etildi'),
    ]

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
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    payment_method = models.CharField(max_length=50, default='Naqd')
    submitted_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_payments'
    )
    note = models.TextField(blank=True)

    class Meta:
        verbose_name = "To'lov"
        verbose_name_plural = "To'lovlar"
        unique_together = ('user', 'contribution')
        ordering = ['-submitted_at']

    def __str__(self):
        status_label = dict(self.STATUS_CHOICES).get(self.status, self.status)
        return (
            f"{self.user} - {self.contribution} - {self.amount} "
            f"({status_label})"
        )
