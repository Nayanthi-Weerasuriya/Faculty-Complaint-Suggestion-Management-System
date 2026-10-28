import logging
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from .models import Notification

logger = logging.getLogger(__name__)


def create_notification(recipient, title, message, case=None, notification_type='status_update'):
    if not recipient or not recipient.is_active:
        return None
    notification = Notification.objects.create(recipient=recipient, case=case, title=title,
                                               message=message, notification_type=notification_type)
    if recipient.email:
        def deliver_email():
            try:
                send_mail(title, message, settings.DEFAULT_FROM_EMAIL, [recipient.email])
            except Exception:
                logger.exception('Email delivery failed for notification %s', notification.pk)
        transaction.on_commit(deliver_email)
    return notification
