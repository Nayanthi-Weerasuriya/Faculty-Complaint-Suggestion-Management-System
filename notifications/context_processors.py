from .models import Notification


def unread_notifications(request):
    """
    Context processor adding unread notifications count and top 5 recent notifications to templates
    """
    if request.user.is_authenticated:
        unread = Notification.objects.filter(recipient=request.user, is_read=False)
        return {
            'unread_notifications_count': unread.count(),
            'recent_notifications': Notification.objects.filter(recipient=request.user).order_by('-sent_at')[:5]
        }
    return {
        'unread_notifications_count': 0,
        'recent_notifications': []
    }
