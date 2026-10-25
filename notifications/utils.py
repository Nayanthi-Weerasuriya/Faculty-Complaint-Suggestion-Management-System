from .models import Notification


def create_notification(recipient, title, message, case=None, notification_type='status_update'):
    """
    Helper function to dispatch in-app notifications
    """
    if recipient:
        return Notification.objects.create(
            recipient=recipient,
            case=case,
            title=title,
            message=message,
            notification_type=notification_type
        )
    return None
