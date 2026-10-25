from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'title', 'notification_type', 'case', 'is_read', 'sent_at')
    list_filter = ('notification_type', 'is_read', 'sent_at')
    search_fields = ('recipient__username', 'title', 'message')
