from django.conf import settings
from django.db import models


class NotificationType(models.TextChoices):
    NEW_CASE = 'new_case', 'New Case Submitted'
    ASSIGNED = 'assigned', 'Case Assigned to Authority'
    STATUS_UPDATE = 'status_update', 'Status Update'
    SOLVED = 'solved', 'Case Solved'
    CLOSED = 'closed', 'Case Closed'
    REMINDER = 'reminder', 'Pending Case Reminder'


class Notification(models.Model):
    """
    In-app notification system informing users of case submissions,
    status changes, and resolution messages (Section 11 & Appendix A).
    """
    case = models.ForeignKey('cases.Case', on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=NotificationType.choices, default=NotificationType.STATUS_UPDATE)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f"Notification to {self.recipient.username}: {self.title}"
