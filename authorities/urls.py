from django.urls import path
from . import views

urlpatterns = [
    path('authorities/', views.authority_list_view, name='authority_list'),
    path('authorities/add/', views.authority_create_view, name='authority_create'),
    path('authorities/<int:pk>/edit/', views.authority_update_view, name='authority_update'),
    path('authorities/<int:pk>/toggle/', views.authority_toggle_active_view, name='authority_toggle'),
    path('authorities/<int:pk>/delete/', views.authority_delete_view, name='authority_delete'),
]
