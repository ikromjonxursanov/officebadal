# duties/models.py
from django.db import models
from apps.users.models import User


class DutyCycle(models.Model):
    """Navbatchilik tsikli"""
    name = models.CharField(max_length=100, default="Bozorlik navbati")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class DutyAssignment(models.Model):
    """Oylik navbatchilik"""
    duty_cycle = models.ForeignKey(DutyCycle, on_delete=models.CASCADE, related_name='assignments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='duty_assignments')
    month = models.DateField()  # Masalan: 2026-07-01 (iyul)

    class Meta:
        unique_together = ('duty_cycle', 'month')
        ordering = ['month']

    def __str__(self):
        return f"{self.month.strftime('%Y-%m')} → {self.user}"