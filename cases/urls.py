from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('cases/submit/', views.submit_case_view, name='submit_case'),
    path('cases/my-cases/', views.my_cases_view, name='my_cases'),
    path('cases/<int:pk>/', views.case_detail_view, name='case_detail'),
    path('cases/<int:pk>/review/', views.admin_review_case_view, name='admin_review_case'),
    path('cases/<int:pk>/update/', views.authority_update_case_view, name='authority_update_case'),
    path('cases/<int:pk>/close/', views.admin_close_case_view, name='admin_close_case'),
    path('cases/<int:pk>/reopen/', views.reopen_case_view, name='reopen_case'),
    path('cases/<int:pk>/comment/', views.add_comment_view, name='add_comment'),
]
