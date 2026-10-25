from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower


class UserRole(models.TextChoices):
    STUDENT = 'student', 'Student'
    LECTURER = 'lecturer', 'Lecturer'
    ADMINISTRATOR = 'administrator', 'Complaint Coordinator'
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

    registration_pending = models.BooleanField(default=False, editable=False)
    verification_sent_at = models.DateTimeField(null=True, blank=True, editable=False)
    email_verified_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ['username']
        constraints = [
            models.UniqueConstraint(Lower('username'), name='unique_username_case_insensitive'),
            models.UniqueConstraint(Lower('email'), condition=~models.Q(email=''), name='unique_nonempty_email_case_insensitive'),
            models.UniqueConstraint(Lower('reg_or_staff_id'), condition=models.Q(reg_or_staff_id__isnull=False) & ~models.Q(reg_or_staff_id=''), name='unique_nonempty_registration_case_insensitive'),
        ]

    def __str__(self):
        full_name = self.get_full_name()
        display_name = full_name if full_name else self.username
        role_label = self.get_role_display()
        return f"{display_name} ({role_label})"

    def save(self, *args, **kwargs):
        # System Administrators must be able to use the protected configuration
        # interface; operational staff do not receive that technical access.
        if self.role == UserRole.SYSTEM_ADMIN or self.is_superuser:
            self.is_staff = True
        super().save(*args, **kwargs)

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
    def is_administrator(self):
        """Operational case administrator (not the system configuration role)."""
        return self.role == UserRole.ADMINISTRATOR

    @property
    def is_system_administrator(self):
        """System configuration administrator, including Django superusers."""
        return self.role == UserRole.SYSTEM_ADMIN or self.is_superuser

    @property
    def can_manage_authorities(self):
        """Authorized users who maintain the faculty authority directory."""
        return self.is_system_administrator

    @property
    def is_authority_user(self):
        return self.role == UserRole.AUTHORITY

    @property
    def is_management_user(self):
        return self.role in [UserRole.FACULTY_MANAGEMENT, UserRole.ADMINISTRATOR, UserRole.SYSTEM_ADMIN]

    def has_perm(self, perm, obj=None):
        return (self.is_active and self.role == UserRole.SYSTEM_ADMIN) or super().has_perm(perm, obj)

    def has_module_perms(self, app_label):
        return (self.is_active and self.role == UserRole.SYSTEM_ADMIN) or super().has_module_perms(app_label)
