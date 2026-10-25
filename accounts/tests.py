from django.test import TestCase
from django.contrib.auth import authenticate
from django.urls import reverse
from accounts.models import User, UserRole
from authorities.models import Authority


class AccountsModelAndAuthTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="student_user",
            email="student@mgt.sjp.ac.lk",
            password="secretpassword",
            role=UserRole.STUDENT,
            reg_or_staff_id="FMSC/2026/9999"
        )
        self.admin = User.objects.create_user(
            username="admin_user",
            email="admin@mgt.sjp.ac.lk",
            password="secretpassword",
            role=UserRole.ADMINISTRATOR,
            reg_or_staff_id="EMP-ADMIN-01"
        )

    def test_user_role_properties(self):
        self.assertTrue(self.student.is_student)
        self.assertTrue(self.student.is_reporting_user)
        self.assertFalse(self.student.is_admin_user)

        self.assertTrue(self.admin.is_admin_user)
        self.assertFalse(self.admin.is_student)

    def test_multi_identifier_login(self):
        """User can authenticate via username, email, or student registration number"""
        # Login using username
        user1 = authenticate(username="student_user", password="secretpassword")
        self.assertIsNotNone(user1)

        # Login using university email
        user2 = authenticate(username="student@mgt.sjp.ac.lk", password="secretpassword")
        self.assertIsNotNone(user2)

        # Login using registration number (Wireframe 1)
        user3 = authenticate(username="FMSC/2026/9999", password="secretpassword")
        self.assertIsNotNone(user3)


class ComplaintHandlerLoginTests(TestCase):
    def setUp(self):
        self.maintenance = Authority.objects.create(
            name="Maintenance Division", officer_name="Officer", designation="Engineer", email="maintenance@example.com"
        )
        self.handler = User.objects.create_user(
            username="maintenance_handler", password="secretpassword", role=UserRole.AUTHORITY,
            assigned_authority=self.maintenance
        )

    def test_handler_can_sign_in_to_own_selected_unit(self):
        response = self.client.post(reverse('complaint_handler_login'), {
            'unit': 'maintenance', 'username': 'maintenance_handler', 'password': 'secretpassword'
        })
        self.assertRedirects(response, reverse('authority_dashboard'))

    def test_handler_cannot_sign_in_to_another_unit(self):
        response = self.client.post(reverse('complaint_handler_login'), {
            'unit': 'it', 'username': 'maintenance_handler', 'password': 'secretpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Use the credentials assigned to the selected complaint-handling unit.")
