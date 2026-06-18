from django.contrib import admin

from apps.duties.models import DutyAssignment, DutyCycle


@admin.register(DutyCycle)
class DutyCycleAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)


@admin.register(DutyAssignment)
class DutyAssignmentAdmin(admin.ModelAdmin):
    list_display = ('month', 'user', 'duty_cycle')
    list_filter = ('month', 'duty_cycle')
    search_fields = ('user__first_name', 'user__last_name', 'user__username')
