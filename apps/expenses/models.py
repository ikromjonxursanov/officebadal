from django.conf import settings
from django.db import models


class Expense(models.Model):
    """Ofis xarajatlari."""
    CATEGORY_CHOICES = [
        ('coffee', 'Kofe'),
        ('tea', 'Choy'),
        ('toilet_paper', 'Hojat qog\'ozi'),
        ('paper', 'Qog\'oz'),
        ('other', 'Boshqa'),
    ]

    date = models.DateField(auto_now_add=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expenses'
    )

    class Meta:
        verbose_name = 'Xarajat'
        verbose_name_plural = 'Xarajatlar'
        ordering = ['-date']

    def __str__(self):
        return f"{self.get_category_display()} - {self.amount} so'm"
