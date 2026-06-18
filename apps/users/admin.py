from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.users.models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ('username', 'first_name', 'last_name',
                    'phone', 'telegram_id', 'is_active')
    list_filter = ('is_active', 'is_staff', 'is_superuser')
    search_fields = ('username', 'first_name',
                     'last_name', 'phone', 'telegram_id')
    ordering = ('first_name', 'last_name')
    fieldsets = DjangoUserAdmin.fieldsets + (
        ('Telegram', {'fields': ('telegram_id', 'phone')}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ('Telegram', {'fields': ('telegram_id', 'phone')}),
    )
