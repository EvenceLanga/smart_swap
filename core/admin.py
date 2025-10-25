from django.contrib import admin
from .models import (
    StudentProfile, Skill, SkillRequest, Review, Message,
    Notification, Meeting
)

# ------------------- STUDENT PROFILE -------------------
@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'year', 'rating')
    search_fields = ('user__username', 'course', 'year')
    list_filter = ('course', 'year')
    readonly_fields = ('rating',)

# ------------------- SKILL -------------------
@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'category', 'level', 'created_at')
    search_fields = ('title', 'owner__username', 'category')
    list_filter = ('category', 'level', 'availability')
    date_hierarchy = 'created_at'

# ------------------- SKILL REQUEST -------------------
@admin.register(SkillRequest)
class SkillRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'skill', 'requester', 'owner', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('skill__title', 'requester__username', 'owner__username')
    date_hierarchy = 'created_at'

# ------------------- REVIEW -------------------
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('skill', 'reviewer', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('skill__title', 'reviewer__username')
    date_hierarchy = 'created_at'

# ------------------- MESSAGE -------------------
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('from_user', 'to_user', 'sent_at', 'is_read')
    search_fields = ('from_user__username', 'to_user__username')
    list_filter = ('is_read',)
    date_hierarchy = 'sent_at'

# ------------------- MEETING -------------------
@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ('title', 'organizer', 'meeting_type', 'scheduled_date', 'status')
    list_filter = ('status', 'meeting_type')
    search_fields = ('title', 'organizer__username', 'location')
    date_hierarchy = 'scheduled_date'

# ------------------- NOTIFICATION -------------------
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'notification_type', 'is_read', 'created_at')
    list_filter = ('is_read', 'notification_type')
    search_fields = ('user__username', 'message')
    date_hierarchy = 'created_at'
