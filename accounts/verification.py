import logging
from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone
from urllib.parse import urlsplit
from .models import User

logger = logging.getLogger(__name__)
SALT = 'accounts.verify-university-email'


def verification_url(request, user):
    token = signing.dumps({'user': user.pk, 'email': user.email, 'sent': user.verification_sent_at.isoformat()}, salt=SALT)
    return request.build_absolute_uri(reverse('verify_email', args=[token]))


def local_verification_preview(request):
    # Demo links are limited to a newly created account in this browser session.
    if (not settings.LOCAL_EMAIL_PREVIEW_ENABLED or not settings.DEBUG
            or settings.EMAIL_BACKEND != 'django.core.mail.backends.console.EmailBackend'
            or urlsplit('//' + request.get_host()).hostname not in {'localhost', '127.0.0.1', '::1'}):
        return None
    user_id = request.session.get('registered_user_id')
    if not user_id:
        return None
    user = User.objects.filter(pk=user_id, registration_pending=True, is_active=False).first()
    if not user or not user.verification_sent_at:
        return None
    age = (timezone.now() - user.verification_sent_at).total_seconds()
    if not 0 <= age <= settings.EMAIL_VERIFICATION_TIMEOUT:
        return None
    return verification_url(request, user)


def send_verification(request, user):
    user.verification_sent_at = timezone.now()
    user.save(update_fields=['verification_sent_at'])
    url = verification_url(request, user)
    try:
        send_mail('Verify your FMSC portal account',
                  'Welcome to the FMSC Complaint and Suggestion Portal.\n\n'
                  f'Verify your university email using this link within 24 hours:\n{url}\n\n'
                  'Open the link and choose Verify email. If you did not register, ignore this message.',
                  settings.DEFAULT_FROM_EMAIL, [user.email])
    except Exception:
        logger.exception('Could not deliver registration verification for user %s', user.pk)
        return False
    return True


def verification_user(token, lock=False):
    try:
        data = signing.loads(token, salt=SALT, max_age=settings.EMAIL_VERIFICATION_TIMEOUT)
        users = User.objects.select_for_update() if lock else User.objects
        user = users.get(pk=data['user'], email=data['email'], registration_pending=True, is_active=False)
        if not user.verification_sent_at or user.verification_sent_at.isoformat() != data['sent']:
            return None
        return user
    except (signing.BadSignature, User.DoesNotExist, KeyError, TypeError, ValueError):
        return None
