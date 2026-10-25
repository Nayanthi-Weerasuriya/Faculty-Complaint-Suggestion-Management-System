from accounts.models import UserRole


def can_view_case(user, case):
    return (user == case.submitted_by or user.is_admin_user
            or user.role == UserRole.FACULTY_MANAGEMENT
            or (user.is_authority_user and user.assigned_authority_id is not None
                and user.assigned_authority_id == case.assigned_authority_id))
