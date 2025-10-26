# core/context_processors.py
from django.utils import timezone
from .models import Skill, Message, SkillRequest  # Import your models

def notification_counts(request):
    if not request.user.is_authenticated:
        return {}
    
    try:
        # Count new skills added today (excluding user's own skills)
        new_skills_count = Skill.objects.filter(
            created_at__date=timezone.now().date()
        ).exclude(user=request.user).count()
        
        # Count pending meeting requests (adjust based on your Meeting model)
        # If you have a Meeting model, use this:
        # meeting_notifications_count = Meeting.objects.filter(
        #     participants=request.user,
        #     status='pending'
        # ).count()
        
        # For now, using skill requests as meetings count
        meeting_notifications_count = SkillRequest.objects.filter(
            skill__user=request.user,  # Requests received for user's skills
            status='PENDING'
        ).count()
        
        # Count user's pending skill requests (requests they made)
        skill_requests_count = SkillRequest.objects.filter(
            requester=request.user,
            status='PENDING'
        ).count()
        
        # Count unread messages (you already have this)
        unread_count = Message.objects.filter(
            to_user=request.user, 
            is_read=False
        ).count()
        
        # Total notifications for dashboard badge
        total_notifications = (
            new_skills_count + 
            meeting_notifications_count + 
            skill_requests_count +
            unread_count
        )
        
        return {
            'new_skills_count': new_skills_count,
            'meeting_notifications_count': meeting_notifications_count,
            'skill_requests_count': skill_requests_count,
            'unread_count': unread_count,
            'total_notifications': total_notifications,
        }
        
    except Exception as e:
        # Return empty counts if there's any error
        return {
            'new_skills_count': 0,
            'meeting_notifications_count': 0,
            'skill_requests_count': 0,
            'unread_count': 0,
            'total_notifications': 0,
        }