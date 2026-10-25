from .models import AuditLog


def log_audit(case, user, action_type, old_value='', new_value='', notes='', request=None):
    """
    Helper function to record an entry in the case audit log
    """
    ip = None
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')

    return AuditLog.objects.create(
        case=case,
        user=user if (user and user.is_authenticated) else None,
        action_type=action_type,
        old_value=str(old_value) if old_value else '',
        new_value=str(new_value) if new_value else '',
        notes=notes,
        ip_address=ip
    )
