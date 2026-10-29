from django.contrib import admin
from config.admin import WorkflowReadOnlyAdmin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(WorkflowReadOnlyAdmin):
    list_display = ('case', 'action_type', 'user', 'timestamp', 'ip_address')
    list_filter = ('action_type', 'timestamp')
    search_fields = ('case__case_number', 'user__username', 'notes', 'old_value', 'new_value')
    readonly_fields = ('case', 'user', 'action_type', 'old_value', 'new_value', 'notes', 'ip_address', 'timestamp')
