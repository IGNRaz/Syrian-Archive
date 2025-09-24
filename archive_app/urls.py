from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # ==================== HOME & DASHBOARD ====================
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # ==================== AUTHENTICATION ====================
    path('register/', views.register, name='register'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('upload-uid/', views.upload_uid_document, name='upload_uid_document'),
    path('change-password/', views.change_password, name='change_password'),
    path('password_reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    ), name='password_reset_complete'),
    
    # ==================== POSTS ====================
    path('posts/', views.post_list, name='post_list'),
    path('posts/create/', views.post_create, name='post_create'),
    path('posts/<int:pk>/', views.post_detail, name='post_detail'),
    path('posts/<int:pk>/edit/', views.post_edit, name='post_edit'),
    path('posts/<int:pk>/delete/', views.post_delete, name='post_delete'),
    
    # ==================== LIKES ====================
    path('posts/<int:pk>/like/', views.toggle_like, name='toggle_like'),
    
    # ==================== TRUST/VERIFICATION ====================
    path('posts/<int:pk>/trust/', views.toggle_trust, name='toggle_trust'),
    
    # ==================== REPORTS & VERIFICATION ====================
    path('posts/<int:pk>/report/', views.report_post, name='report_post'),
    path('posts/<int:pk>/verify/', views.verify_post, name='verify_post'),
    
    # ==================== PEOPLE ====================
    path('people/', views.person_list, name='person_list'),
    path('people/create/', views.person_create, name='person_create'),
    path('people/<int:pk>/', views.person_detail, name='person_detail'),
    path('people/<int:pk>/edit/', views.person_edit, name='person_edit'),
    path('people/<int:pk>/delete/', views.person_delete, name='person_delete'),
    
    # ==================== EVENTS ====================
    path('events/', views.event_list, name='event_list'),
    path('events/create/', views.event_create, name='event_create'),
    path('events/<int:pk>/', views.event_detail, name='event_detail'),
    path('events/<int:pk>/edit/', views.event_edit, name='event_edit'),
    
    # ==================== VERIFICATION REQUESTS ====================
    path('verification/request/', views.request_verification, name='request_verification'),
    
    # ==================== PROFILE ====================
    path('profile/', views.profile_view, name='profile_view'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/<str:username>/', views.profile_view, name='profile_view_user'),
    
    # ==================== ADMIN DASHBOARD ====================
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    
    # Admin Users
    path('admin-panel/users/', views.admin_users, name='admin_users'),
    path('admin-panel/users/<int:pk>/', views.admin_user_detail, name='admin_user_detail'),
    
    # Admin Posts
    path('admin-panel/posts/', views.admin_posts, name='admin_posts'),
    path('admin-panel/posts/<int:pk>/', views.admin_post_detail, name='admin_post_detail'),
    path('admin-panel/posts/<int:pk>/update-status/', views.admin_post_status_update, name='admin_post_status_update'),
    
    # Admin Reports
    path('admin-panel/reports/', views.admin_reports, name='admin_reports'),
    path('admin-panel/reports/<int:pk>/', views.admin_report_detail, name='admin_report_detail'),
    
    # Admin Verifications
    path('admin-panel/verifications/', views.admin_verifications, name='admin_verifications'),
    path('admin-panel/verifications/<int:pk>/', views.admin_verification_detail, name='admin_verification_detail'),
    
    # Admin People
    path('admin-panel/people/', views.admin_people, name='admin_people'),
    path('admin-panel/people/<int:pk>/', views.admin_person_detail, name='admin_person_detail'),
    path('admin-panel/people/<int:pk>/update-role/', views.admin_person_update_role, name='admin_person_update_role'),
    path('admin-panel/people/<int:pk>/update-status/', views.admin_person_update_status, name='admin_person_update_status'),
    path('admin-panel/people/<int:pk>/delete/', views.admin_person_delete, name='admin_person_delete'),
    
    # Admin Events
    path('admin-panel/events/', views.admin_events, name='admin_events'),
    path('admin-panel/events/<int:pk>/', views.admin_event_detail, name='admin_event_detail'),
    
    # Admin IP Bans
    path('admin-panel/ip-bans/', views.admin_ip_bans, name='admin_ip_bans'),
    path('admin-panel/ip-bans/<int:pk>/', views.admin_ip_ban_detail, name='admin_ip_ban_detail'),
    
    # ==================== LOGS ====================
    path('admin-panel/logs/', views.admin_logs, name='admin_logs'),
    path('admin-panel/logs/download/', views.admin_logs_download, name='admin_logs_download'),
]

