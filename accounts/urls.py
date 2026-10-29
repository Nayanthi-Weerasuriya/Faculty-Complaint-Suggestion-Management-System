from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .forms import FacultyPasswordResetForm
from .views import ComplaintHandlerLoginView, FacultyLoginView, FacultyLogoutView, profile_view

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('register/done/', views.registration_done_view, name='registration_done'),
    path('verify/resend/', views.resend_verification_view, name='resend_verification'),
    path('verify/<str:token>/', views.verify_email_view, name='verify_email'),
    path('password-reset/', auth_views.PasswordResetView.as_view(form_class=FacultyPasswordResetForm, template_name='accounts/password_reset.html', email_template_name='accounts/password_reset_email.txt'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='accounts/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='accounts/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/complete/', auth_views.PasswordResetCompleteView.as_view(template_name='accounts/password_reset_complete.html'), name='password_reset_complete'),
    path('login/', FacultyLoginView.as_view(), name='login'),
    path('complaint-handler/', ComplaintHandlerLoginView.as_view(), name='complaint_handler_login'),
    path('logout/', FacultyLogoutView.as_view(), name='logout'),
    path('profile/', profile_view, name='profile'),
]
