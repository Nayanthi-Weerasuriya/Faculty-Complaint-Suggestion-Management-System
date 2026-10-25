from django.urls import path
from . import views

urlpatterns = [
    path('notifications/', views.notification_list_view, name='notification_list'),
    path('notifications/<int:pk>/read/', views.mark_notification_read_view, name='mark_notification_read'),
    path('notifications/read-all/', views.mark_all_read_view, name='mark_all_notifications_read'),
]
