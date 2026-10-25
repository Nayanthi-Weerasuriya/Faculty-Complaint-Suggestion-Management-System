from django.urls import path
from . import views

urlpatterns = [
    path('admin/', views.admin_dashboard_view, name='admin_dashboard'),
    path('authority/', views.authority_dashboard_view, name='authority_dashboard'),
    path('management/', views.management_dashboard_view, name='management_dashboard'),
]
