from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

app_name = 'core'

urlpatterns = [
    # Public & Auth URLs
    path('', views.welcome, name='welcome'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('account/delete/', views.delete_account, name='delete_account'),
    # Password Reset URLs
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='registration/password_reset_form.html',
             email_template_name='registration/password_reset_email.html',
             subject_template_name='registration/password_reset_subject.txt'
         ), 
         name='password_reset'),
    
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='registration/password_reset_done.html'
         ), 
         name='password_reset_done'),
    
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='registration/password_reset_confirm.html'
         ), 
         name='password_reset_confirm'),
    
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='registration/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
    
    # Debug URL
    path('debug-email/', views.debug_email_test, name='debug_email'),

    # User Dashboard & Profile URLs
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/<str:username>/', views.view_profile, name='view_profile'),
    
    # Skills URLs
    path('skills/', views.skill_list, name='skill_list'),
    path('skills/create/', views.create_skill, name='create_skill'),
    path('skills/<int:skill_id>/', views.skill_detail, name='skill_detail'),
    path('skill-requests/', views.skill_requests, name='skill_requests'),
    path('skills/<int:skill_id>/request/', views.request_skill, name='request_skill'),
    path('skills/<int:skill_id>/review/', views.add_review, name='add_review'),
    path('search/', views.search_skills, name='search_skills'),
    path('requests/<int:request_id>/start/', views.start_skill_session, name='start_skill_session'),
    path('requests/<int:request_id>/complete/', views.complete_skill_session, name='complete_skill_session'),
    # Request Management URLs
    path('requests/<int:request_id>/accept/', views.accept_request, name='accept_request'),
    path('requests/<int:request_id>/reject/', views.reject_request, name='reject_request'),
    path('requests/<int:request_id>/complete/', views.complete_request, name='complete_request'),
    
    # Review URLs
    path('reviews/<int:review_id>/edit/', views.edit_review, name='edit_review'),
    path('reviews/<int:review_id>/delete/', views.delete_review, name='delete_review'),
    
    # Chat & Messaging URLs
    path('inbox/', views.inbox, name='inbox'),
    path('messages/send/', views.send_message, name='send_message'),
    path('reply_message/', views.reply_message, name='reply_message'),
    path('conversation/<str:username>/', views.conversation, name='conversation'),
    
    # Modern Chat URLs
    path('chat/', views.chat_dashboard, name='chat_dashboard'),
    path('quick-schedule/<str:username>/', views.quick_schedule, name='quick_schedule'),
    path('chat/send/', views.send_chat_message, name='send_chat_message'),
    path('chat/mark-read/<str:username>/', views.mark_messages_read, name='mark_messages_read'),
    path('chat/search-users/', views.search_users, name='search_users'),
    path('chat/<str:username>/', views.chat_room, name='chat_room'),
    
    # Meeting URLs
    path('meetings/', views.my_meetings, name='my_meetings'),
    path('meetings/schedule/', views.schedule_meeting, name='schedule_meeting'),
    path('meetings/quick/<str:username>/', views.quick_schedule, name='quick_schedule'),
    path('meetings/<int:meeting_id>/', views.meeting_detail, name='meeting_detail'),
    path('meetings/<int:meeting_id>/<str:status>/', views.update_meeting_status, name='update_meeting_status'),
    path('meetings/calendar/', views.calendar, name='meeting_calendar'),
    
    # Notifications & Debug
    path('notifications/', views.notifications, name='notifications'),
    path('debug-urls/', views.debug_urls, name='debug_urls'),
    
    # ===== ADMIN MANAGEMENT URLS =====
    # Main Admin Dashboard
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-portal/', views.admin_portal, name='admin_portal'),
    
    # Management List Views
    path('management/users/', views.manage_users, name='manage_users'),
    path('management/skills/', views.manage_skills, name='manage_skills'),
    path('management/requests/', views.manage_requests, name='manage_requests'),
    path('management/reviews/', views.manage_reviews, name='manage_reviews'),
    path('management/meetings/', views.manage_meetings, name='manage_meetings'),
     
    # User Management Actions
    path('management/users/<int:user_id>/edit/', views.edit_user, name='edit_user'),
    path('management/users/<int:user_id>/delete/', views.delete_user, name='delete_user'),
    
    # Skill Management Actions
    path('management/skills/<int:skill_id>/edit/', views.edit_skill, name='edit_skill'),
    path('management/skills/<int:skill_id>/delete/', views.delete_skill, name='delete_skill'),
    
    # Request Management Actions
    path('management/requests/<int:request_id>/approve/', views.approve_request, name='approve_request'),
    path('management/requests/<int:request_id>/reject/', views.reject_request, name='reject_request'),
    path('management/requests/<int:request_id>/delete/', views.delete_request, name='delete_request'),
    
    # Review Management Actions
    path('management/reviews/<int:review_id>/delete/', views.delete_review, name='delete_review'),
    
    # Meeting Management Actions
    path('management/meetings/<int:meeting_id>/edit/', views.edit_meeting, name='edit_meeting'),
    path('management/meetings/<int:meeting_id>/delete/', views.delete_meeting, name='delete_meeting'),
    
    # Report Management Actions
    path('management/reports/<int:report_id>/resolve/', views.resolve_report, name='resolve_report'),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)