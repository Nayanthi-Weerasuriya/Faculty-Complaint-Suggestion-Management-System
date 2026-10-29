from datetime import timedelta
from django.contrib import admin
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from accounts.models import User, UserRole
from authorities.models import Authority
from categories.models import Category
from cases.models import Case, CaseStatus, Attachment, CaseComment
from cases.forms import CaseReviewAssignmentForm
from audit.models import AuditLog


class ReportingFixTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user('manager', role=UserRole.FACULTY_MANAGEMENT)
        self.coordinator = User.objects.create_user('coordinator', role=UserRole.ADMINISTRATOR)
        self.category = Category.objects.create(name='Facilities')
        self.authority = Authority.objects.create(name='Maintenance')

    def case(self, **kwargs):
        return Case.objects.create(title='Leak', description='Details', location='Hall',
                                   category=self.category, submitted_by=self.coordinator, **kwargs)

    def test_chart_percentages_follow_filtered_data_and_empty_results(self):
        self.case(case_type='complaint', priority='urgent')
        for _ in range(3):
            self.case(case_type='suggestion', priority='normal')
        self.client.force_login(self.manager)
        response = self.client.get(reverse('management_dashboard'))
        self.assertEqual(response.context['complaints_percentage'], 25)
        self.assertEqual(response.context['suggestions_percentage'], 75)
        self.assertContains(response, 'width: 25.0%')
        filtered = self.client.get(reverse('management_dashboard'), {'priority': 'urgent'})
        self.assertEqual(filtered.context['urgent_percentage'], 100)
        self.assertEqual(filtered.context['normal_percentage'], 0)
        Case.objects.all().delete()
        empty = self.client.get(reverse('management_dashboard'))
        for key in ['complaints', 'suggestions', 'urgent', 'normal']:
            self.assertEqual(empty.context[key + '_percentage'], 0)

    def test_coordinator_date_controls_filter_inclusively_and_validate(self):
        case = self.case()
        day = timezone.localdate().isoformat()
        self.client.force_login(self.coordinator)
        response = self.client.get(reverse('admin_dashboard'), {'date_from': day, 'date_to': day})
        self.assertContains(response, 'name="date_from"')
        self.assertContains(response, 'name="date_to"')
        self.assertEqual(list(response.context['table_cases']), [case])
        for params in [{'date_from': 'invalid'}, {'date_from': '2026-10-29', 'date_to': '2026-10-01'}]:
            response = self.client.get(reverse('admin_dashboard'), params)
            self.assertTrue(response.context['date_filters'].errors)
            self.assertEqual(response.context['total_cases'], 0)
            self.assertContains(response, 'role="alert"')

    def test_pending_counts_and_age_use_same_cases_and_hide_empty_units(self):
        pending = self.case(status=CaseStatus.ASSIGNED, assigned_authority=self.authority)
        Case.objects.filter(pk=pending.pk).update(submitted_at=timezone.now()-timedelta(days=4))
        self.case(status=CaseStatus.REOPENED, assigned_authority=self.authority)
        self.case(status=CaseStatus.SOLVED, resolution_notes='Done', assigned_authority=self.authority)
        Authority.objects.create(name='Empty inactive', is_active=False)
        self.client.force_login(self.manager)
        response = self.client.get(reverse('management_dashboard'))
        rows = response.context['authority_breakdown']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['assigned'], 1)
        self.assertEqual(rows[0]['average_age'], 4)
        self.assertEqual(rows[0]['not_started'], 1)

    def test_assignment_requires_active_authority_role_handler(self):
        data = dict(category=self.category.pk, priority='normal', assigned_authority=self.authority.pk,
                    status='assigned', admin_notes='Please handle')
        self.assertIn('assigned_authority', CaseReviewAssignmentForm(data).errors)
        officer = User.objects.create_user('officer', role=UserRole.STUDENT, assigned_authority=self.authority)
        self.assertFalse(CaseReviewAssignmentForm(data).is_valid())
        officer.role = UserRole.AUTHORITY
        officer.is_active = False
        officer.save()
        self.assertFalse(CaseReviewAssignmentForm(data).is_valid())
        officer.is_active = True
        officer.save()
        self.assertTrue(CaseReviewAssignmentForm(data).is_valid())
        self.authority.is_active = False
        self.authority.save()
        self.assertFalse(CaseReviewAssignmentForm(data).is_valid())

    def test_workflow_admin_blocks_direct_mutations_but_allows_inspection(self):
        system = User.objects.create_superuser('system', 'system@example.com', 'test-pass')
        self.client.force_login(system)
        case = self.case()
        response = self.client.get(reverse('admin:cases_case_change', args=[case.pk]))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse('admin:cases_case_change', args=[case.pk]), {'status': 'solved'})
        self.assertEqual(response.status_code, 403)
        case.refresh_from_db()
        self.assertEqual(case.status, CaseStatus.SUBMITTED)
        request = response.wsgi_request
        for model in [Case, Attachment, CaseComment, AuditLog]:
            model_admin = admin.site._registry[model]
            self.assertTrue(model_admin.has_view_permission(request))
            self.assertFalse(model_admin.has_add_permission(request))
            self.assertFalse(model_admin.has_change_permission(request))
            self.assertFalse(model_admin.has_delete_permission(request))
        self.assertEqual(self.client.post(reverse('admin:cases_case_delete', args=[case.pk]), {'post': 'yes'}).status_code, 403)

    def test_all_required_status_summaries_follow_filters(self):
        from dashboard.metrics import status_summary
        for status in CaseStatus.values:
            self.case(status=status, priority='urgent' if status == CaseStatus.SUBMITTED else 'normal',
                      resolution_notes='Done' if status in [CaseStatus.SOLVED, CaseStatus.CLOSED] else '')
        counts = dict(status_summary(Case.objects.all()))
        self.assertEqual(counts, {'Total': 10, 'Attempted': 8, 'Not attempted': 1, 'Open': 9,
                                 'Not started': 2, 'Urgent': 1, 'Normal': 9, 'Solved': 1,
                                 'Closed': 1, 'Rejected': 1})
        self.client.force_login(self.manager)
        response = self.client.get(reverse('management_dashboard'), {'priority': 'urgent'})
        self.assertEqual(dict(response.context['status_summary'])['Total'], 1)
        self.assertContains(response, 'Case status summary')
        self.client.force_login(self.coordinator)
        response = self.client.get(reverse('admin_dashboard'), {'date_to': '2000-01-01'})
        self.assertTrue(all(count == 0 for _, count in response.context['status_summary']))
