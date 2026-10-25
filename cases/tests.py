from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from accounts.models import User, UserRole
from categories.models import Category
from authorities.models import Authority
from cases.models import Case, CaseType, CasePriority, CaseStatus
from cases.forms import CaseProgressUpdateForm, CaseSubmissionForm


class CaseModelTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="test_student",
            password="password123",
            role=UserRole.STUDENT,
            reg_or_staff_id="FMSC/2026/0001"
        )
        self.category = Category.objects.create(name="Classroom Facilities")
        self.authority = Authority.objects.create(
            name="Maintenance Division",
            officer_name="Eng. Perera",
            designation="Works Engineer",
            email="maint@sjp.ac.lk"
        )

    def test_case_number_auto_generation(self):
        """Case numbers should auto-generate in FMSC-YYYY-XXXX format"""
        year = timezone.now().year
        case1 = Case.objects.create(
            title="Broken desk in Hall B",
            case_type=CaseType.COMPLAINT,
            priority=CasePriority.NORMAL,
            category=self.category,
            location="Hall B",
            description="Desk is damaged",
            declaration=True,
            submitted_by=self.student
        )
        self.assertTrue(case1.case_number.startswith(f"FMSC-{year}-"))
        self.assertEqual(case1.case_number, f"FMSC-{year}-0001")

        case2 = Case.objects.create(
            title="Broken projector in Lab 1",
            case_type=CaseType.COMPLAINT,
            priority=CasePriority.URGENT,
            category=self.category,
            location="Lab 1",
            description="Projector lamp red",
            declaration=True,
            submitted_by=self.student
        )
        self.assertEqual(case2.case_number, f"FMSC-{year}-0002")

    def test_age_days_calculation(self):
        """Age in days should correctly calculate elapsed days from submission"""
        five_days_ago = timezone.now() - timedelta(days=5)
        case = Case.objects.create(
            title="Old unstarted complaint",
            category=self.category,
            location="Library",
            description="AC leaking",
            declaration=True,
            submitted_by=self.student,
            submitted_at=five_days_ago
        )
        self.assertEqual(case.age_days, 5)

    def test_resolution_note_required_on_solved(self):
        """Acceptance Criterion 17: Case cannot be marked solved without resolution notes"""
        case = Case.objects.create(
            title="Corridor water leak",
            category=self.category,
            location="2nd floor",
            description="Water leaking",
            declaration=True,
            submitted_by=self.student,
            status=CaseStatus.IN_PROGRESS,
            assigned_authority=self.authority
        )

        # Form with status=SOLVED but empty resolution_notes should fail validation
        form_invalid = CaseProgressUpdateForm(
            data={'status': CaseStatus.SOLVED, 'resolution_notes': '', 'progress_comment': 'Done'},
            instance=case
        )
        self.assertFalse(form_invalid.is_valid())
        self.assertIn('resolution_notes', form_invalid.errors)

        # Form with valid resolution note should pass
        form_valid = CaseProgressUpdateForm(
            data={'status': CaseStatus.SOLVED, 'resolution_notes': 'Pipe replaced and sealed.', 'progress_comment': ''},
            instance=case
        )
        self.assertTrue(form_valid.is_valid())
