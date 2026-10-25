from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from .models import User


class FacultyAuthBackend(ModelBackend):
    """
    Allows authentication using username, university email, or student/employee registration number.
    Matches Wireframe 1 specifications.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get('reg_or_staff_id') or kwargs.get('email')
        if not username or not password:
            return None

        try:
            # Query by username, email, or registration / staff ID
            user = User.objects.filter(
                Q(username__iexact=username) |
                Q(email__iexact=username) |
                Q(reg_or_staff_id__iexact=username)
            ).first()

            if user and user.check_password(password) and self.user_can_authenticate(user):
                return user
        except Exception:
            return None
        return None
