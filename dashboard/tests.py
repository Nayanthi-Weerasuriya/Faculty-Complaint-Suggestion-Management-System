from django.test import TestCase
from django.urls import reverse
from accounts.models import User, UserRole


class SystemAdministratorAccessTests(TestCase):
    def setUp(self):
        self.coordinator = User.objects.create_user(
            username='coordinator', password='password123', role=UserRole.ADMINISTRATOR
        )
        self.system_admin = User.objects.create_user(
            username='system_admin', password='password123', role=UserRole.SYSTEM_ADMIN
        )
        self.management = User.objects.create_user(
            username='dean', password='password123', role=UserRole.FACULTY_MANAGEMENT
        )

    def test_system_administrator_can_open_system_dashboard(self):
        self.client.force_login(self.system_admin)
        self.assertEqual(self.client.get(reverse('system_dashboard')).status_code, 200)

    def test_complaint_coordinator_cannot_open_system_dashboard(self):
        self.client.force_login(self.coordinator)
        self.assertEqual(self.client.get(reverse('system_dashboard')).status_code, 403)

    def test_faculty_management_can_open_read_only_detailed_reports(self):
        self.client.force_login(self.management)
        self.assertEqual(self.client.get(reverse('management_reports')).status_code, 200)

    def test_coordinator_completed_summary_matches_filtered_cases(self):
        from categories.models import Category
        from cases.models import Case, CaseStatus
        category = Category.objects.create(name='Facilities')
        for index, status in enumerate([CaseStatus.SOLVED, CaseStatus.SOLVED, CaseStatus.CLOSED, CaseStatus.SUBMITTED, CaseStatus.REJECTED]):
            Case.objects.create(title=f'Case {index}', category=category, location='Hall', description='Details',
                                submitted_by=self.coordinator, status=status,
                                resolution_notes='Fixed' if status in [CaseStatus.SOLVED, CaseStatus.CLOSED] else '')
        self.client.force_login(self.coordinator)
        response = self.client.get(reverse('admin_dashboard'), {'status': 'resolved'})
        self.assertEqual(response.context['resolved_cases'], 3)
        self.assertEqual(response.context['table_cases'].count(), 3)
        self.assertEqual(set(response.context['table_cases'].values_list('status', flat=True)), {CaseStatus.SOLVED, CaseStatus.CLOSED})
        individual = self.client.get(reverse('admin_dashboard'), {'status': 'solved'})
        self.assertEqual(individual.context['table_cases'].count(), 2)
