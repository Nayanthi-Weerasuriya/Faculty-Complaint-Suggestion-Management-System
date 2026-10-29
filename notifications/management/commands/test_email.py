from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError


class Command(BaseCommand):
    help = 'Send an explicit SMTP delivery test to an address you control.'

    def add_arguments(self, parser):
        parser.add_argument('--to', required=True, help='Recipient address for this test message.')

    def handle(self, *args, **options):
        if settings.EMAIL_BACKEND != 'django.core.mail.backends.smtp.EmailBackend':
            raise CommandError('Configure the SMTP email backend before testing delivered email.')
        try:
            validate_email(options['to'])
            validate_email(settings.DEFAULT_FROM_EMAIL)
        except ValidationError:
            raise CommandError('Set a valid recipient and DEFAULT_FROM_EMAIL address.') from None
        if not settings.EMAIL_HOST:
            raise CommandError('Set EMAIL_HOST before testing delivery.')
        try:
            sent = send_mail('FMSC portal delivery test',
                             'This is a requested email configuration test for the FMSC portal.',
                             settings.DEFAULT_FROM_EMAIL, [options['to']], fail_silently=False)
        except Exception:
            raise CommandError('SMTP delivery failed. Check server configuration and credentials; no secrets are printed.') from None
        if sent != 1:
            raise CommandError('The mail backend did not accept the test message.')
        self.stdout.write(self.style.SUCCESS('SMTP accepted the test message. Confirm receipt in the inbox or spam folder.'))
