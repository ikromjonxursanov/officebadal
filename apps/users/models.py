from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Ofis xodimlari uchun maxsus foydalanuvchi modeli."""
    telegram_id = models.BigIntegerField(unique=True, null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Foydalanuvchi'
        verbose_name_plural = 'Foydalanuvchilar'
        ordering = ['first_name', 'last_name']

    def __str__(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.username
