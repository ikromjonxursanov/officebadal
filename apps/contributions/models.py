# contributions/models.py
from django.db import models
from apps.users.models import User


class MonthlyContribution(models.Model):
    """Oylik badal sozlamalari"""
    month = models.DateField(unique=True)  # Masalan: 2026-06-01
    amount = models.DecimalField(max_digits=12, decimal_places=2)  # 50000.00
    due_date = models.DateField()  # Har oyning qaysi sanasida to'lanishi kerak

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Oylik badal"
        verbose_name_plural = "Oylik badallar"
        ordering = ['-month']

    def __str__(self):
        return f"{self.month.strftime('%Y-%m')} - {self.amount} so'm"


class Payment(models.Model):
    """To'lovlar"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    contribution = models.ForeignKey(MonthlyContribution, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_at = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=50, default="Naqd")  # Naqd, Bank, Click va h.k.

    class Meta:
        verbose_name = "To'lov"
        verbose_name_plural = "To'lovlar"
        unique_together = ('user', 'contribution')
        ordering = ['-paid_at']

    def __str__(self):
        return f"{self.user} - {self.contribution} - {self.amount}"