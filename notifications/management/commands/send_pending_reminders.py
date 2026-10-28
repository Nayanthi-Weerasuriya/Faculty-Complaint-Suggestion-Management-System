from datetime import timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from accounts.models import User, UserRole
from cases.models import Case, CaseStatus
from notifications.models import Notification
from notifications.utils import create_notification


class Command(BaseCommand):
    help = 'Send at most one pending-case reminder per recipient and case each day.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7)

    def handle(self, *args, **options):
        if options['days'] < 1:
            raise CommandError('--days must be at least 1.')
        cases = Case.objects.filter(updated_at__lte=timezone.now() - timedelta(days=options['days'])).exclude(
            status__in=[CaseStatus.SOLVED, CaseStatus.CLOSED, CaseStatus.REJECTED])
        count = 0
        for case in cases:
            recipients = User.objects.filter(role=UserRole.ADMINISTRATOR, is_active=True)
            if case.assigned_authority_id:
                recipients = User.objects.filter(role=UserRole.AUTHORITY, assigned_authority=case.assigned_authority, is_active=True)
                if not recipients.exists():
                    recipients = User.objects.filter(role=UserRole.ADMINISTRATOR, is_active=True)
            for recipient in recipients:
                if Notification.objects.filter(case=case, recipient=recipient, notification_type='reminder', sent_at__date=timezone.localdate()).exists():
                    continue
                create_notification(recipient, f'Pending case: {case.case_number}',
                                    f'{case.title} is {case.get_status_display().lower()}, age {case.age_days} days. Please review.',
                                    case=case, notification_type='reminder')
                count += 1
        self.stdout.write(self.style.SUCCESS(f'Created {count} pending-case reminders.'))
