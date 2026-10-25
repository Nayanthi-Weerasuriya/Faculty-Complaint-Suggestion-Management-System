from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ('FMSC Portal Profile', {
            'fields': ('role', 'reg_or_staff_id', 'department_or_unit', 'contact_number', 'assigned_authority')
        }),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'reg_or_staff_id', 'department_or_unit', 'is_active')
    list_filter = ('role', 'is_active', 'is_staff', 'department_or_unit')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'reg_or_staff_id')
