from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    STUDENT = 'student', 'Student'
    LECTURER = 'lecturer', 'Lecturer'
    ADMINISTRATOR = 'administrator', 'Administrator'
    AUTHORITY = 'authority', 'Relevant Authority'
    FACULTY_MANAGEMENT = 'faculty_management', 'Faculty Management'
    SYSTEM_ADMIN = 'system_admin', 'System Administrator'


class User(AbstractUser):
    """
    Custom user model supporting all 6 faculty stakeholder roles
    defined in Section 6 and Appendix A.
    """
    role = models.CharField(
        max_length=30,
        choices=UserRole.choices,
        default=UserRole.STUDENT,
        help_text="Role determining access permissions in the portal"
    )
    reg_or_staff_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Registration Number (students) or Employee/Staff ID (lecturers/staff)"
    )
    department_or_unit = models.CharField(
        max_length=150,
        blank=True,
        help_text="Academic department or administrative unit"
    )
    contact_number = models.CharField(
        max_length=25,
        blank=True,
        help_text="Mobile or contact telephone number"
    )
    assigned_authority = models.ForeignKey(
        'authorities.Authority',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_staff',
        help_text="Specific authority unit this user represents (if role is Relevant Authority)"
    )

    class Meta:
        ordering = ['username']

    def __str__(self):
        full_name = self.get_full_name()
        display_name = full_name if full_name else self.username
        role_label = self.get_role_display()
        return f"{display_name} ({role_label})"

    @property
    def is_student(self):
        return self.role == UserRole.STUDENT

    @property
    def is_lecturer(self):
        return self.role == UserRole.LECTURER

    @property
    def is_reporting_user(self):
        return self.role in [UserRole.STUDENT, UserRole.LECTURER]

    @property
    def is_admin_user(self):
        return self.role in [UserRole.ADMINISTRATOR, UserRole.SYSTEM_ADMIN] or self.is_superuser

    @property
    def is_authority_user(self):
        return self.role == UserRole.AUTHORITY

    @property
    def is_management_user(self):
        return self.role in [UserRole.FACULTY_MANAGEMENT, UserRole.ADMINISTRATOR, UserRole.SYSTEM_ADMIN]
