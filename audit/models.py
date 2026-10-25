from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """
    Complete audit trail of submissions, assignments, status changes,
    comments, and closures (Section 11, Appendix A).
    """
    case = models.ForeignKey('cases.Case', on_delete=models.CASCADE, related_name='audit_logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action_type = models.CharField(max_length=100, help_text="e.g. Created, Assigned, Status Updated, Resolved, Closed")
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"

    def __str__(self):
        user_name = self.user.username if self.user else "System"
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {self.case.case_number} - {self.action_type} by {user_name}"
