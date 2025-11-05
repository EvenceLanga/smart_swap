from datetime import timedelta
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Q


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
        # Ensure profile exists before saving
        if hasattr(instance, 'profile'):
            instance.profile.save()


# ------------------ SKILL ------------------
class Skill(models.Model):
    CATEGORY_CHOICES = [
        ('programming', 'Programming'),
        ('design', 'Design'),
        ('marketing', 'Marketing'),
        ('business', 'Business'),
        ('language', 'Language'),
        ('music', 'Music'),
        ('other', 'Other'),
    ]

    LEVEL_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]

    AVAILABILITY_CHOICES = [
        ('weekdays', 'Weekdays'),
        ('weekends', 'Weekends'),
        ('evenings', 'Evenings'),
        ('flexible', 'Flexible'),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='skills')
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES)
    description = models.TextField(blank=True)
    level = models.CharField(max_length=50, choices=LEVEL_CHOICES)
    availability = models.CharField(max_length=50, choices=AVAILABILITY_CHOICES)
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
    is_request = models.BooleanField(default=False)  # New field for message requests

    def __str__(self):
        return f"From {self.from_user} to {self.to_user} ({self.sent_at.strftime('%Y-%m-%d %H:%M')})"

    class Meta:
        ordering = ['sent_at']


# ------------------ USER BLOCK MANAGER ------------------
class UserBlockManager(models.Manager):
    def is_blocked(self, user1, user2):
        """Check if two users have blocked each other"""
        return self.filter(
            Q(blocker=user1, blocked=user2) | Q(blocker=user2, blocked=user1)
        ).exists()
    
    def get_blocked_users(self, user):
        """Get all users blocked by a specific user"""
        return User.objects.filter(
            id__in=self.filter(blocker=user).values('blocked')
        )
    
    def get_blocked_by_users(self, user):
        """Get all users who have blocked a specific user"""
        return User.objects.filter(
            id__in=self.filter(blocked=user).values('blocker')
        )


# ------------------ USER BLOCK ------------------
class UserBlock(models.Model):
    blocker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocking')
    blocked = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocked_by')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Use the custom manager
    objects = UserBlockManager()
    
    class Meta:
        unique_together = ['blocker', 'blocked']
        verbose_name = 'User Block'
        verbose_name_plural = 'User Blocks'

    def __str__(self):
        return f"{self.blocker.username} blocked {self.blocked.username}"


# ------------------ MESSAGE REQUEST MANAGER ------------------
class MessageRequestManager(models.Manager):
    def pending_for_user(self, user):
        """Get all pending message requests for a user"""
        return self.filter(to_user=user, status='PENDING')
    
    def accepted_for_user(self, user):
        """Get all accepted message requests for a user"""
        return self.filter(
            Q(from_user=user) | Q(to_user=user),
            status='ACCEPTED'
        )
    
    def can_message(self, user1, user2):
        """Check if two users can message each other"""
        # Check if either user has blocked the other
        if UserBlock.objects.is_blocked(user1, user2):
            return False
        
        # Check if there's an accepted message request
        return self.filter(
            Q(from_user=user1, to_user=user2) | Q(from_user=user2, to_user=user1),
            status='ACCEPTED'
        ).exists()


# ------------------ MESSAGE REQUEST ------------------
class MessageRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('DECLINED', 'Declined'),
        ('BLOCKED', 'Blocked'),
    ]
    
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_requests')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_requests')
    message = models.ForeignKey(Message, on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Use the custom manager
    objects = MessageRequestManager()

    class Meta:
        unique_together = ['from_user', 'to_user']
        ordering = ['-created_at']

    def __str__(self):
        return f"Message request: {self.from_user} → {self.to_user} ({self.status})"


# ------------------ NOTIFICATION ------------------
class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('message', 'New Message'),
        ('meeting_invite', 'Meeting Invitation'),
        ('meeting_update', 'Meeting Update'),
        ('skill_request', 'Skill Request'),
        ('review', 'New Review'),
        ('skill_session', 'Skill Session Started'),
        ('skill_completed', 'Skill Session Completed'),
        ('email_verification', 'Email Verification'),
        ('message_request', 'Message Request'),  # Added for message requests
        ('request_accepted', 'Request Accepted'),  # Added for accepted message requests
        ('request_declined', 'Request Declined'),  # Added for declined message requests
        ('user_blocked', 'User Blocked'),  # Added for blocking
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='message')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    related_meeting = models.ForeignKey('Meeting', on_delete=models.CASCADE, null=True, blank=True)
    related_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='related_notifications')
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.message}"


# ------------------ MEETING ------------------
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
    duration_minutes = models.PositiveIntegerField(default=30)
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


# ------------------ REPORT ------------------
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


# ------------------ MEETING MANAGER ------------------
class MeetingManager(models.Manager):
    def for_user(self, user):
        return self.filter(
            Q(participants=user) | Q(organizer=user)
        ).distinct()


# ------------------ EMAIL VERIFICATION TOKEN ------------------
class EmailVerificationToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    
    def is_valid(self):
        # Token expires after 24 hours
        return not self.is_used and (timezone.now() - self.created_at) < timedelta(hours=24)
    
    def __str__(self):
        return f"Email verification for {self.user.email}"


# ------------------ CLEANUP FUNCTION ------------------
def delete_old_notifications(days=30):
    """Delete notifications older than specified days"""
    cutoff = timezone.now() - timedelta(days=days)
    Notification.objects.filter(created_at__lt=cutoff).delete()