from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
    path('register/', views.register, name='register'),
    path('search/', views.search_blood, name='search_blood'),
    path('dashboard/', views.donor_dashboard, name='donor_dashboard'),
    path('send-request/<int:donor_id>/', views.send_request, name='send_request'),
    path('approve/<int:request_id>/', views.approve_request, name='approve_request'),
    path('reject/<int:request_id>/', views.reject_request, name='reject_request'),
    path('confirm-donation/<int:request_id>/', views.confirm_donation, name='confirm_donation'),
    path('cancel-request/<int:request_id>/', views.cancel_approved_request, name='cancel_approved_request'),

    # Authentication URLs
    path('signup/', views.signup, name='signup'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='index'), name='logout'),
    path('my-requests/', views.my_sent_requests, name='my_sent_requests'),
    path('my-requests/clear/', views.clear_request_history, name='clear_request_history'),

    path('toggle-availability/', views.toggle_availability, name='toggle_availability'),
    path('toggle-emergency/', views.toggle_emergency, name='toggle_emergency'),
    path('confirm-donation/<int:request_id>/', views.confirm_donation, name='confirm_donation'),
    path('cancel-request/<int:request_id>/', views.cancel_approved_request, name='cancel_approved_request'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),

    # Admin URLs
    path('admin-dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('admin-dashboard/reject/<int:user_id>/', views.admin_reject_user, name='admin_reject_user'),
    path('admin-dashboard/accept/<int:user_id>/', views.admin_accept_user, name='admin_accept_user'),
    path('admin-dashboard/view-profile/<int:user_id>/', views.admin_view_profile, name='admin_view_profile'),
]
