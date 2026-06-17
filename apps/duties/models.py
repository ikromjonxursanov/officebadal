from django.db import models
from django.conf import settings


class DutyCycle(models.Model):
    name = models.CharField(max_length=100, default="Bozorlik navbati")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class DutyAssignment(models.Model):
    duty_cycle = models.ForeignKey(
        DutyCycle,
        on_delete=models.CASCADE,
        related_name='assignments'
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='duty_assignments'
    )

    month = models.DateField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['duty_cycle', 'month'],
                name='unique_duty_per_month'
            )
        ]
        ordering = ['month']

    def __str__(self):
        return f"{self.month.strftime('%Y-%m')} → {self.user}"