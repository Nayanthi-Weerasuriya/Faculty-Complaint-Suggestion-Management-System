from django.urls import path
from .views import FacultyLoginView, FacultyLogoutView, profile_view

urlpatterns = [
    path('login/', FacultyLoginView.as_view(), name='login'),
    path('logout/', FacultyLogoutView.as_view(), name='logout'),
    path('profile/', profile_view, name='profile'),
]
