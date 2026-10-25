from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Notification


@login_required
def notification_list_view(request):
    notifications = Notification.objects.filter(recipient=request.user).order_by('-sent_at')
    return render(request, 'notifications/notification_list.html', {'notifications': notifications})


@login_required
def mark_notification_read_view(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.is_read = True
    notification.save()
    if notification.case:
        return redirect('case_detail', pk=notification.case.pk)
    return redirect('notification_list')


@login_required
def mark_all_read_view(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return redirect('notification_list')
