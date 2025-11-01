from datetime import timedelta
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver


# ------------------ PROFILE ------------------
class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    bio = models.TextField(blank=True)
    course = models.CharField(max_length=100, blank=True)
    year = models.CharField(max_length=20, blank=True)
    rating = models.FloatField(default=0.0)
    skills_offered = models.TextField(blank=True, help_text="Skills you can teach (comma-separated)")
    skills_wanted = models.TextField(blank=True, help_text="Skills you want to learn (comma-separated)")

    def __str__(self):
        return f"{self.user.username}'s Profile"


# Automatically create or update profile when user is created
@receiver(post_save, sender=User)
def create_or_update_student_profile(sender, instance, created, **kwargs):
    if created:
        StudentProfile.objects.create(user=instance)
    else:
        instance.profile.save()


# ------------------ SKILL ------------------
class Skill(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='skills')
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    level = models.CharField(max_length=50, blank=True)
    availability = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.title} by {self.owner.username}"


# ------------------ SKILL REQUEST ------------------
class SkillRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
    ]
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='requests')
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requests_made')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requests_received')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(default=timezone.now)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True) 
    completed_at = models.DateTimeField(null=True, blank=True)  

    def __str__(self):
        return f"Request {self.id}: {self.requester.username} -> {self.skill.title} ({self.status})"


# ------------------ REVIEW ------------------
class Review(models.Model):
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(null=True, blank=True)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Review for {self.skill.title} - {self.rating}/5"


# ------------------ MESSAGE ------------------
class Message(models.Model):
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages_sent')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages_received')
    content = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    attachment = models.FileField(upload_to='attachments/', blank=True, null=True)
    reply_to = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='replies')

    def __str__(self):
        return f"From {self.from_user} to {self.to_user} ({self.sent_at.strftime('%Y-%m-%d %H:%M')})"


# ------------------ NOTIFICATION ------------------
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message}"


# ------------------ CLEANUP FUNCTION ------------------
def delete_old_notifications(days=30):
    from datetime import timedelta
    cutoff = timezone.now() - timedelta(days=days)
    Notification.objects.filter(created_at__lt=cutoff).delete()

class Meeting(models.Model):
    MEETING_TYPES = [
        ('skill_swap', 'Skill Swap Session'),
        ('tutoring', 'Tutoring Session'),
        ('project', 'Project Collaboration'),
        ('general', 'General Meeting'),
    ]
    
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organized_meetings')
    participants = models.ManyToManyField(User, related_name='meetings', blank=True)
    meeting_type = models.CharField(max_length=20, choices=MEETING_TYPES, default='general')
    scheduled_date = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=30)  # Meeting duration in minutes
    location = models.CharField(max_length=300, blank=True, help_text="Physical location or meeting link")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # For skill-related meetings
    related_skill = models.ForeignKey('Skill', on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['scheduled_date']
    
    def __str__(self):
        return f"{self.title} - {self.scheduled_date.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def end_time(self):
        return self.scheduled_date + timedelta(minutes=self.duration_minutes)
    
    def is_upcoming(self):
        return self.scheduled_date > timezone.now() and self.status in ['scheduled', 'confirmed']
    
class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('message', 'New Message'),
        ('meeting_invite', 'Meeting Invitation'),
        ('meeting_update', 'Meeting Update'),
        ('skill_request', 'Skill Request'),
        ('review', 'New Review'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='message')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    related_meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.message}"

class Report(models.Model):
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_made')
    reported_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_received')
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Report: {self.reporter.username} → {self.reported_user.username}"

class Report(models.Model):
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_made')
    reported_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_received')
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Report: {self.reporter.username} → {self.reported_user.username}"

# In core/models.py
from django.db.models import Q

class MeetingManager(models.Manager):
    def for_user(self, user):
        return self.filter(
            Q(participants=user) | Q(organizer=user)
        ).distinct()