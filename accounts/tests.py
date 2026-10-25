from django.test import TestCase
from django.contrib.auth import authenticate
from accounts.models import User, UserRole


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
