from gettext import translation
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.views import redirect_to_login
from .forms import UserRegistrationForm, SkillForm
from .models import StudentProfile, Skill, SkillRequest, Review, Message
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Message, Notification
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .forms import StudentProfileForm
from core import models
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Avg
from django.shortcuts import render
from django.contrib.auth.models import User
from .models import Skill, SkillRequest, Review, Meeting
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta, datetime
from .models import Meeting
from .forms import MeetingForm
from django.views.decorators.csrf import csrf_exempt

@staff_member_required
def admin_dashboard(request):
    total_users = User.objects.count()
    total_skills = Skill.objects.count()
    total_requests = SkillRequest.objects.count()
    completed_swaps = SkillRequest.objects.filter(status='COMPLETED').count()
    avg_rating = Review.objects.aggregate(Avg('rating'))['rating__avg'] or 0
    total_meetings = Meeting.objects.count()

    popular_categories = (
        Skill.objects.values('category')
        .annotate(total=Count('id'))
        .order_by('-total')[:5]
    )

    return render(request, 'core/admin_dashboard.html', {
        'total_users': total_users,
        'total_skills': total_skills,
        'total_requests': total_requests,
        'completed_swaps': completed_swaps,
        'avg_rating': round(avg_rating, 2),
        'total_meetings': total_meetings,
        'popular_categories': popular_categories,
    })



def view_profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    
    # Use the same relationship name as in models.py
    profile = getattr(profile_user, "profile", None)  # Changed from "studentprofile" to "profile"
    
    reviews = profile_user.reviews_received.all() if hasattr(profile_user, "reviews_received") else []
    
    return render(
        request,
        'core/view_profile.html',
        {'profile_user': profile_user, 'profile': profile, 'reviews': reviews}
    )

def edit_profile(request):
    """Allow current user to edit their own profile"""
    # Get or create profile
    profile, created = StudentProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = StudentProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('core:view_profile', username=request.user.username)
    else:
        form = StudentProfileForm(instance=profile)
    
    return render(request, 'core/edit_profile.html', {'form': form})

def welcome(request):
      # If user is logged in, redirect to dashboard instead of index
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    
    skills = Skill.objects.order_by('-created_at')[:10]
    return render(request, 'core/welcome.html', {'skills': skills})

def index(request):
    # If user is logged in, redirect to dashboard instead of index
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    
    skills = Skill.objects.order_by('-created_at')[:10]
    return render(request, 'core/index.html', {'skills': skills})

@csrf_exempt
def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            new_user = form.save(commit=False)
            new_user.set_password(form.cleaned_data['password'])
            new_user.save()

            # Automatically log in the user after registration
            login(request, new_user)

            messages.success(request, 'Registration successful! Please complete your profile.')
            return redirect('core:edit_profile')
    else:
        form = UserRegistrationForm()

    return render(request, 'core/register.html', {'form': form})

@csrf_exempt
def user_login(request):
    # ADD THIS CHECK - If user is already logged in, redirect to dashboard
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('core:dashboard')
        else:
            messages.error(request, 'Invalid credentials.')
    return render(request, 'core/login.html')

def user_logout(request):
    logout(request)
    return redirect('core:index')


def dashboard(request):
    my_skills = request.user.skills.all()
    my_requests = request.user.requests_made.all()
    received = request.user.requests_received.all()

    # Add these for enhanced statistics
    skills_with_stats = []
    for skill in my_skills:
        skills_with_stats.append({
            'skill': skill,
            'total_requests': skill.requests.count(),
            'approved_requests': skill.requests.filter(status='APPROVED').count(),
            'in_progress_requests': skill.requests.filter(status='IN_PROGRESS').count(),
        })

    return render(request, 'core/dashboard.html', {
        'my_skills': my_skills,
        'my_requests': my_requests,
        'received': received,
        'skills_with_stats': skills_with_stats,  
    })


def skill_requests(request):
    """View for managing skill requests"""
    # Requests user has made to others
    requests_made = request.user.requests_made.all()
    
    # Requests others have made to user's skills  
    requests_received = request.user.requests_received.all()
    
    return render(request, 'core/skill_requests.html', {
        'requests_made': requests_made,
        'requests_received': requests_received,
    })

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta


def skill_list(request):
    # Start with all skills
    skills = Skill.objects.all()
    
    # Get filter parameters from request
    sort_by = request.GET.get('sort', 'recent')
    category_filter = request.GET.get('category', '')
    search_query = request.GET.get('q', '')
    level_filter = request.GET.get('level', '')
    
    # Apply search filter
    if search_query:
        skills = skills.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__icontains=search_query) |
            Q(owner__username__icontains=search_query) |
            Q(owner__first_name__icontains=search_query) |
            Q(owner__last_name__icontains=search_query)
        )
    
    # Apply category filter
    if category_filter:
        skills = skills.filter(category__iexact=category_filter)
    
    # Apply level filter
    if level_filter:
        skills = skills.filter(level__iexact=level_filter)
    
    # Apply sorting
    if sort_by == 'popular':
        # Sort by number of requests (most popular first)
        skills = skills.annotate(request_count=Count('requests')).order_by('-request_count', '-created_at')
    elif sort_by == 'rating':
        # Sort by average rating (highest rated first)
        skills = skills.annotate(
            avg_rating=Avg('reviews__rating')
        ).order_by('-avg_rating', '-created_at')
    elif sort_by == 'recent':
        # Sort by most recently created
        skills = skills.order_by('-created_at')
    elif sort_by == 'name':
        # Sort alphabetically by title
        skills = skills.order_by('title')
    else:
        # Default sorting (most recent)
        skills = skills.order_by('-created_at')
    
    # Add additional context for each skill
    for skill in skills:
        # Mark as new if created in last 7 days
        skill.is_new = (timezone.now() - skill.created_at).days <= 7
        # Calculate average rating
        avg_rating = skill.reviews.aggregate(Avg('rating'))['rating__avg']
        skill.average_rating = round(avg_rating, 1) if avg_rating else None
        # Get request count
        skill.request_count = skill.requests.count()
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(skills, 12)  # Show 12 skills per page
    
    try:
        skills_page = paginator.page(page)
    except PageNotAnInteger:
        skills_page = paginator.page(1)
    except EmptyPage:
        skills_page = paginator.page(paginator.num_pages)
    
    # Get unique categories for filter dropdown
    categories = Skill.objects.values_list('category', flat=True).distinct().order_by('category')
    
    # Get unique levels for filter dropdown
    levels = Skill.objects.values_list('level', flat=True).distinct().order_by('level')
    
    context = {
        'skills': skills_page,
        'categories': categories,
        'levels': levels,
        'current_sort': sort_by,
        'current_category': category_filter,
        'current_level': level_filter,
        'search_query': search_query,
        'paginator': paginator,
    }
    
    return render(request, 'core/skill_list.html', context)



def create_skill(request):
    if request.method == 'POST':
        form = SkillForm(request.POST)
        if form.is_valid():
            skill = form.save(commit=False)
            skill.owner = request.user
            skill.save()
            messages.success(request, 'Skill created.')
            return redirect('core:skill_list')
    else:
        form = SkillForm()
    return render(request, 'core/create_skill.html', {'form': form})


def skill_detail(request, skill_id):
    skill = get_object_or_404(Skill, id=skill_id)
    reviews = Review.objects.filter(skill=skill).order_by('-created_at')
    
    # Calculate request statistics
    total_requests = SkillRequest.objects.filter(skill=skill).count()
    approved_requests = SkillRequest.objects.filter(skill=skill, status='APPROVED').count()
    pending_requests = SkillRequest.objects.filter(skill=skill, status='PENDING').count()
    in_progress_requests = SkillRequest.objects.filter(skill=skill, status='IN_PROGRESS').count()
    completed_requests = SkillRequest.objects.filter(skill=skill, status='COMPLETED').count()
    
    # Get active sessions (in progress)
    active_sessions = SkillRequest.objects.filter(skill=skill, status='IN_PROGRESS')
    
    # Calculate approval rate (avoid division by zero)
    approval_rate = 0
    if total_requests > 0:
        approval_rate = round((approved_requests / total_requests) * 100)
    
    return render(request, 'core/skill_detail.html', {
        'skill': skill,
        'reviews': reviews,
        'total_requests': total_requests,
        'approved_requests': approved_requests,
        'pending_requests': pending_requests,
        'in_progress_requests': in_progress_requests,
        'completed_requests': completed_requests,
        'approval_rate': approval_rate,
        'active_sessions': active_sessions,
    })


def request_skill(request, skill_id):
    skill = get_object_or_404(Skill, id=skill_id)
    
    # Check if user is trying to request their own skill
    if skill.owner == request.user:
        messages.error(request, 'You cannot request your own skill.')
        return redirect('core:skill_detail', skill_id=skill.id)
    
    # Check if user has already requested this skill
    existing_request = SkillRequest.objects.filter(
        skill=skill, 
        requester=request.user
    ).first()
    
    if existing_request:
        # User has already requested this skill
        if existing_request.status == 'PENDING':
            messages.info(request, 'You have already requested this skill. Your request is pending approval.')
        elif existing_request.status == 'APPROVED':
            messages.info(request, 'Your request for this skill has been approved!')
        elif existing_request.status == 'REJECTED':
            messages.info(request, 'Your previous request for this skill was rejected.')
        elif existing_request.status == 'COMPLETED':
            messages.info(request, 'You have already completed learning this skill!')
        else:
            messages.info(request, 'You have already requested this skill.')
        return redirect('core:skill_detail', skill_id=skill.id)
    
    # Create new request if no existing request found
    req = SkillRequest.objects.create(
        skill=skill, 
        requester=request.user, 
        owner=skill.owner, 
        status='PENDING'
    )
    messages.success(request, 'Request sent to skill owner.')
    return redirect('core:dashboard')


def start_skill_session(request, request_id):
    """Mark a skill request as In Progress"""
    skill_request = get_object_or_404(SkillRequest, id=request_id)
    
    # Check if user is the skill owner
    if request.user != skill_request.owner:
        messages.error(request, 'Only the skill owner can start a session.')
        return redirect('core:dashboard')
    
    # Check if request is approved
    if skill_request.status != 'APPROVED':
        messages.error(request, 'Can only start sessions for approved requests.')
        return redirect('core:dashboard')
    
    # Update status and set start time
    skill_request.status = 'IN_PROGRESS'
    skill_request.started_at = timezone.now()
    skill_request.save()
    
    # Send notification to requester
    Notification.objects.create(
        user=skill_request.requester,
        message=f"Your skill session for '{skill_request.skill.title}' has started!",
        notification_type='skill_session'
    )
    
    messages.success(request, f"Skill session with {skill_request.requester.username} started!")
    return redirect('core:dashboard')


def complete_skill_session(request, request_id):
    """Mark a skill request as Completed"""
    skill_request = get_object_or_404(SkillRequest, id=request_id)
    
    # Check if user is either the owner or requester
    if request.user not in [skill_request.owner, skill_request.requester]:
        messages.error(request, 'Not authorized to complete this session.')
        return redirect('core:dashboard')
    
    # Check if request is in progress
    if skill_request.status != 'IN_PROGRESS':
        messages.error(request, 'Can only complete sessions that are in progress.')
        return redirect('core:dashboard')
    
    # Update status and set completion time
    skill_request.status = 'COMPLETED'
    skill_request.completed_at = timezone.now()
    skill_request.save()
    
    # Send notification to the other user
    other_user = skill_request.requester if request.user == skill_request.owner else skill_request.owner
    Notification.objects.create(
        user=other_user,
        message=f"Skill session for '{skill_request.skill.title}' has been completed!",
        notification_type='skill_completed'
    )
    
    messages.success(request, f"Skill session completed successfully!")
    return redirect('core:dashboard')



def accept_request(request, request_id):
    req = get_object_or_404(SkillRequest, id=request_id, owner=request.user)
    req.status = 'ACCEPTED'
    req.save()
    messages.success(request, 'Request accepted.')
    return redirect('core:dashboard')


def reject_request(request, request_id):
    req = get_object_or_404(SkillRequest, id=request_id, owner=request.user)
    req.status = 'REJECTED'
    req.save()
    messages.success(request, 'Request rejected.')
    return redirect('core:dashboard')


def complete_request(request, request_id):
    req = get_object_or_404(SkillRequest, id=request_id)
    if request.user not in [req.requester, req.owner]:
        messages.error(request, 'Not authorized.')
        return redirect('core:dashboard')
    req.status = 'COMPLETED'
    req.save()
    messages.success(request, 'Marked as completed. Please leave a review.')
    return redirect('core:dashboard')


def send_message(request):
    users = User.objects.exclude(id=request.user.id)  # exclude current user
    preselect = request.GET.get('to')  # ✅ capture preselected user ID

    if request.method == 'POST':
        recipient_id = request.POST.get('to_user')
        message_text = request.POST.get('message')
        recipient = get_object_or_404(User, id=recipient_id)

        Message.objects.create(
            from_user=request.user,
            to_user=recipient,
            content=message_text
        )

        # Optional: notification
        Notification.objects.create(
            user=recipient,
            message=f"You have a new message from {request.user.username}"
        )

        messages.success(request, f"Message sent to {recipient.username}.")
        return redirect('core:inbox')

    # ✅ Include preselect in the context
    return render(request, 'core/send_message.html', {'users': users, 'preselect': preselect})


def add_review(request, skill_id):
    skill = get_object_or_404(Skill, id=skill_id)

    if request.method == 'POST':
        rating = int(request.POST.get('rating'))
        comment = request.POST.get('comment')

        # Allow both owner and other users to review/comment
        Review.objects.create(
            skill=skill,
            reviewer=request.user,
            rating=rating,
            comment=comment,
            created_at=timezone.now()
        )
        messages.success(request, 'Your review or comment has been submitted.')
        return redirect('core:skill_detail', skill_id=skill_id)


def edit_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)

    # Only the author of the review can edit
    if review.reviewer != request.user:
        messages.error(request, "You can only edit your own review.")
        return redirect('core:skill_detail', skill_id=review.skill.id)

    if request.method == 'POST':
        review.rating = int(request.POST.get('rating'))
        review.comment = request.POST.get('comment')
        review.save()
        messages.success(request, "Your review has been updated.")
        return redirect('core:skill_detail', skill_id=review.skill.id)

    return render(request, 'core/edit_review.html', {'review': review})



def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)

    # Only the author can delete
    if review.reviewer != request.user:
        messages.error(request, "You can only delete your own review.")
        return redirect('core:skill_detail', skill_id=review.skill.id)

    if request.method == 'POST':
        skill_id = review.skill.id
        review.delete()
        messages.success(request, "Your review has been deleted.")
        return redirect('core:skill_detail', skill_id=skill_id)

    return render(request, 'core/delete_review.html', {'review': review})

from django.db.models import Q


def inbox(request):
    # Identify all messages where the user is either sender or receiver
    messages = Message.objects.filter(
        Q(to_user=request.user) | Q(from_user=request.user)
    ).order_by('sent_at')

    return render(request, 'core/inbox.html', {'messages': messages})

def reply_message(request):
    if request.method == 'POST':
        to_user_id = request.POST.get('to_user_id')
        content = request.POST.get('content')
        attachment = request.FILES.get('attachment')

        try:
            to_user = User.objects.get(id=to_user_id)
        except User.DoesNotExist:
            messages.error(request, "User not found.")
            return redirect('core:inbox')

        Message.objects.create(
            from_user=request.user,
            to_user=to_user,
            content=content,
            attachment=attachment
        )
        messages.success(request, "Reply sent successfully!")
    return redirect('core:inbox')

def chat_room(request, username):
    other_user = get_object_or_404(User, username=username)
    room_name = f"chat_{min(request.user.id, other_user.id)}_{max(request.user.id, other_user.id)}"

    # Messages between users
    chat_messages = Message.objects.filter(
        from_user__in=[request.user, other_user],
        to_user__in=[request.user, other_user]
    ).order_by('sent_at')

    return render(request, 'core/chat_room.html', {
        'room_name': room_name,
        'other_user': other_user,
        'messages': chat_messages,
    })

def user_profile(request, user_id):
    profile_user = get_object_or_404(User, id=user_id)
    skills = Skill.objects.filter(owner=profile_user)
    return render(request, 'core/user_profile.html', {'profile_user': profile_user, 'skills': skills})

def search_skills(request):
    query = request.GET.get('q')
    if query:
        results = Skill.objects.filter(title__icontains=query)
    else:
        results = Skill.objects.none()
    return render(request, 'core/search_results.html', {'results': results, 'query': query})


def notifications(request):
    # Placeholder for now — you can later connect to real Notification model
    return render(request, 'core/notifications.html', {})


def conversation(request, username):
    other_user = get_object_or_404(User, username=username)
    messages = Message.objects.filter(
        Q(from_user=request.user, to_user=other_user) |
        Q(from_user=other_user, to_user=request.user)
    ).order_by('sent_at')
    return render(request, 'core/conversation.html', {'messages': messages, 'other_user': other_user})



def chat_dashboard(request):
    """Main chat dashboard with conversation list and active chat"""
    
    # Get all unique users that the current user has conversed with
    # Messages where current user is sender
    sent_to_users = Message.objects.filter(
        from_user=request.user
    ).values_list('to_user', flat=True).distinct()
    
    # Messages where current user is receiver  
    received_from_users = Message.objects.filter(
        to_user=request.user
    ).values_list('from_user', flat=True).distinct()
    
    # Combine and get unique user IDs
    all_user_ids = set(sent_to_users) | set(received_from_users)
    chat_users = User.objects.filter(id__in=all_user_ids)
    
    # Get last message and unread count for each user
    user_data = []
    for user in chat_users:
        # Get the last message in this conversation
        last_message = Message.objects.filter(
            Q(from_user=request.user, to_user=user) |
            Q(from_user=user, to_user=request.user)
        ).order_by('-sent_at').first()
        
        # Get unread message count from this user
        unread_count = Message.objects.filter(
            from_user=user, to_user=request.user, is_read=False
        ).count()
        
        user_data.append({
            'user': user,
            'last_message': last_message,
            'unread_count': unread_count
        })
    
    # Sort by last message timestamp (most recent first)
    user_data.sort(key=lambda x: x['last_message'].sent_at if x['last_message'] else timezone.make_aware(datetime.min), reverse=True)
    
    # Get messages for active conversation if user is selected
    active_user = None
    active_messages = []
    selected_user = request.GET.get('user')
    
    if selected_user:
        active_user = get_object_or_404(User, username=selected_user)
        active_messages = Message.objects.filter(
            Q(from_user=request.user, to_user=active_user) |
            Q(from_user=active_user, to_user=request.user)
        ).order_by('sent_at')
        
        # Mark messages from active user as read when opening conversation
        if active_user:
            Message.objects.filter(
                from_user=active_user, to_user=request.user, is_read=False
            ).update(is_read=True)
    
    # Get upcoming meetings
    now = timezone.now()
    upcoming_meetings = Meeting.objects.filter(
        Q(organizer=request.user) | Q(participants=request.user),
        scheduled_date__gte=now,
        status__in=['scheduled', 'confirmed']
    ).order_by('scheduled_date')[:5]
    
    return render(request, 'core/chat_dashboard.html', {
        'user_data': user_data,  # Pass the structured data instead of raw users
        'active_user': active_user,
        'active_messages': active_messages,
        'upcoming_meetings': upcoming_meetings,
        'users': User.objects.exclude(id=request.user.id)
    })


def send_chat_message(request):
    """Send message from chat interface"""
    if request.method == 'POST':
        to_user_id = request.POST.get('to_user')
        content = request.POST.get('content')
        attachment = request.FILES.get('attachment')
        
        if to_user_id and content:
            to_user = get_object_or_404(User, id=to_user_id)
            Message.objects.create(
                from_user=request.user,
                to_user=to_user,
                content=content,
                attachment=attachment
            )
            messages.success(request, "Message sent!")
            
            # SIMPLE FIX: Use redirect with URL string
            return redirect(f'/chat/?user={to_user.username}')
    
    # If something goes wrong, redirect to chat dashboard
    return redirect('core:chat_dashboard')



def mark_messages_read(request, username):
    """Mark messages from a user as read"""
    other_user = get_object_or_404(User, username=username)
    Message.objects.filter(
        from_user=other_user, to_user=request.user, is_read=False
    ).update(is_read=True)
    
    return JsonResponse({'status': 'success'})


def search_users(request):
    """Search users for starting new conversations"""
    query = request.GET.get('q', '')
    if query:
        users = User.objects.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        ).exclude(id=request.user.id)[:10]
    else:
        users = User.objects.none()
    
    return render(request, 'core/user_search_results.html', {'users': users, 'query': query})

def debug_urls(request):
    from django.urls import get_resolver
    resolver = get_resolver()
    url_list = []
    
    for pattern in resolver.url_patterns:
        if hasattr(pattern, 'pattern'):
            url_list.append(f"{pattern.pattern} -> {getattr(pattern, 'name', 'No name')}")
    
    return HttpResponse('<br>'.join(sorted(url_list)))


########## MEETING SCHEDULING ############
from django.utils import timezone
from datetime import timedelta, datetime
from .models import Meeting
from .forms import MeetingForm


def schedule_meeting(request):
    """Schedule a new meeting"""
    if request.method == 'POST':
        form = MeetingForm(request.POST, organizer=request.user)
        if form.is_valid():
            meeting = form.save(commit=False)
            meeting.organizer = request.user
            meeting.save()
            form.save_m2m()  # Save participants
            
            # Send notifications to participants
            for participant in meeting.participants.all():
                if participant != request.user:
                    Notification.objects.create(
                        user=participant,
                        message=f"{request.user.username} invited you to a meeting: {meeting.title}",
                        notification_type='meeting_invite'
                    )
            
            messages.success(request, f"Meeting '{meeting.title}' scheduled successfully!")
            return redirect('core:meeting_detail', meeting_id=meeting.id)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        # Pre-fill with default values
        default_time = timezone.now() + timedelta(hours=24)
        form = MeetingForm(initial={
            'scheduled_date': default_time.strftime('%Y-%m-%dT%H:%M'),
            'duration_minutes': 60
        }, organizer=request.user)
    
    return render(request, 'core/schedule_meeting.html', {'form': form})


def calendar(request):
    # Get meetings where user is either organizer or participant
    meetings = Meeting.objects.filter(
        Q(organizer=request.user) | Q(participants=request.user)
    ).distinct().select_related('organizer', 'related_skill')
    
    context = {
        'meetings': meetings,
    }
    return render(request, 'core/calendar.html', context)

def quick_schedule(request, username):
    """Quick schedule a meeting with a specific user"""
    try:
        other_user = User.objects.get(username=username)
    except User.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect('core:chat_dashboard')
    
    if request.method == 'POST':
        form = MeetingForm(request.POST, request.FILES, organizer=request.user)
        if form.is_valid():
            meeting = form.save(commit=False)
            meeting.organizer = request.user
            meeting.save()
            form.save_m2m()  # Save participants
            
            # Ensure the target user is added as participant
            meeting.participants.add(other_user)
            
            # Send notification to the participant
            if other_user != request.user:
                Notification.objects.create(
                    user=other_user,
                    message=f"{request.user.get_full_name() or request.user.username} invited you to a meeting: {meeting.title}",
                    notification_type='meeting_invite'
                )
            
            messages.success(request, f"Meeting scheduled successfully with {other_user.get_full_name() or other_user.username}!")
            return redirect('core:chat_dashboard')  # Redirect back to chat
            
    else:
        # Pre-fill with default values and the target user as participant
        default_time = timezone.now() + timedelta(hours=24)  # Tomorrow same time
        form = MeetingForm(
            initial={
                'scheduled_date': default_time.strftime('%Y-%m-%dT%H:%M'),
                'title': f"Meeting with {other_user.get_full_name() or other_user.username}",
                'organizer': request.user
            },
            organizer=request.user
        )
    
    return render(request, 'core/quick_schedule.html', {
        'form': form,
        'other_user': other_user
    })


def meeting_detail(request, meeting_id):
    """View meeting details"""
    meeting = get_object_or_404(Meeting, id=meeting_id)
    
    # Check if user is organizer or participant
    if request.user != meeting.organizer and request.user not in meeting.participants.all():
        messages.error(request, "You don't have permission to view this meeting.")
        return redirect('core:my_meetings')
    
    return render(request, 'core/meeting_detail.html', {
        'meeting': meeting,
        'now': timezone.now()  # Pass current time to template
    })


def my_meetings(request):
    """View user's meetings"""
    now = timezone.now()
    
    # Get meetings where user is organizer or participant
    organized = request.user.organized_meetings.all()
    participating = request.user.meetings.all()
    
    # Combine and remove duplicates
    all_meetings = (organized | participating).distinct()
    
    upcoming_meetings = all_meetings.filter(scheduled_date__gte=now, status__in=['scheduled', 'confirmed'])
    past_meetings = all_meetings.filter(scheduled_date__lt=now) | all_meetings.filter(status='completed')
    
    return render(request, 'core/my_meetings.html', {
        'upcoming_meetings': upcoming_meetings,
        'past_meetings': past_meetings
    })


def update_meeting_status(request, meeting_id, status):
    """Update meeting status (confirm, cancel, etc.)"""
    meeting = get_object_or_404(Meeting, id=meeting_id)
    
    # Check permissions
    if request.user != meeting.organizer and request.user not in meeting.participants.all():
        messages.error(request, "You don't have permission to update this meeting.")
        return redirect('core:my_meetings')
    
    valid_statuses = [choice[0] for choice in Meeting.STATUS_CHOICES]
    if status in valid_statuses:
        meeting.status = status
        meeting.save()
        
        # Notify other participants
        participants = meeting.participants.exclude(id=request.user.id)
        for participant in participants:
            Notification.objects.create(
                user=participant,
                message=f"Meeting '{meeting.title}' status updated to {status} by {request.user.username}",
                notification_type='meeting_update'
            )
        
        messages.success(request, f"Meeting status updated to {status}.")
    
    return redirect('core:meeting_detail', meeting_id=meeting.id)


def meeting_calendar(request):
    """Calendar view of meetings"""
    meetings = Meeting.objects.filter(
        models.Q(organizer=request.user) | models.Q(participants=request.user)
    ).distinct()
    
    # Format for fullcalendar
    events = []
    for meeting in meetings:
        events.append({
            'id': meeting.id,
            'title': meeting.title,
            'start': meeting.scheduled_date.isoformat(),
            'end': meeting.end_time.isoformat(),
            'url': f"/meetings/{meeting.id}/",
            'color': '#6366f1' if meeting.organizer == request.user else '#10b981',
            'textColor': 'white'
        })
    
    return render(request, 'core/meeting_calendar.html', {'events': events})


def quick_schedule(request, username):
    """Quick schedule with a specific user"""
    other_user = get_object_or_404(User, username=username)
    
    if request.method == 'POST':
        form = MeetingForm(request.POST, organizer=request.user)
        if form.is_valid():
            meeting = form.save(commit=False)
            meeting.organizer = request.user
            meeting.save()
            meeting.participants.add(other_user)  # Add the specific user
            
            messages.success(request, f"Meeting scheduled with {other_user.username}!")
            return redirect('core:chat_dashboard') + f'?user={username}'
    else:
        default_time = timezone.now() + timedelta(hours=24)
        form = MeetingForm(initial={
            'scheduled_date': default_time.strftime('%Y-%m-%dT%H:%M'),
            'title': f"Meeting with {other_user.username}",
            'participants': [other_user]
        }, organizer=request.user)
    
    return render(request, 'core/quick_schedule.html', {
        'form': form,
        'other_user': other_user
    })


from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Skill, SkillRequest, Review, Report
from .forms import SkillForm

# ---------- Admin Portal ----------
@staff_member_required
def admin_portal(request):
    return render(request, 'core/admin_portal.html')

# ---------- Manage Users ----------
@staff_member_required
def manage_users(request):
    users = User.objects.all()
    return render(request, 'core/manage_users.html', {'users': users})

@staff_member_required
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.delete()
    messages.success(request, 'User deleted successfully.')
    return redirect('core:manage_users')

# ---------- Manage Skills ----------
@staff_member_required
def manage_skills(request):
    skills = Skill.objects.all()
    return render(request, 'core/manage_skills.html', {'skills': skills})

@staff_member_required
def delete_skill(request, skill_id):
    skill = get_object_or_404(Skill, id=skill_id)
    skill.delete()
    messages.success(request, 'Skill deleted successfully.')
    return redirect('core:manage_skills')

# ---------- Manage Requests ----------
@staff_member_required
def approve_request(request, request_id):
    skill_request = get_object_or_404(SkillRequest, id=request_id)
    skill_request.status = 'APPROVED'
    skill_request.save()
    messages.success(request, f'Skill request #{skill_request.id} has been approved.')
    return redirect('core:manage_requests')

@staff_member_required
def reject_request(request, request_id):
    skill_request = get_object_or_404(SkillRequest, id=request_id)
    skill_request.status = 'REJECTED'
    skill_request.save()
    messages.success(request, f'Skill request #{skill_request.id} has been rejected.')
    return redirect('core:manage_requests')

@staff_member_required
def delete_request(request, req_id):
    req = get_object_or_404(SkillRequest, id=req_id)
    req.delete()
    messages.success(request, 'Skill request deleted successfully.')
    return redirect('core:manage_requests')

@staff_member_required
def manage_requests(request):
    status_filter = request.GET.get('status', '')
    if status_filter:
        requests = SkillRequest.objects.filter(status=status_filter)
    else:
        requests = SkillRequest.objects.all()
    
    return render(request, 'core/manage_requests.html', {
        'requests': requests,  # Make sure this is 'requests' (plural)
        'current_status': status_filter
    })
# ---------- Manage Reviews ----------
@staff_member_required
def manage_reviews(request):
    reviews = Review.objects.all()
    return render(request, 'core/manage_reviews.html', {'reviews': reviews})

@staff_member_required
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    review.delete()
    messages.success(request, 'Review deleted successfully.')
    return redirect('core:manage_reviews')

# ---------- Manage Reports ----------
@staff_member_required
def manage_reports(request):
    reports = Report.objects.all()
    return render(request, 'core/manage_reports.html', {'reports': reports})

@staff_member_required
def resolve_report(request, report_id):
    report = get_object_or_404(Report, id=report_id)
    report.resolved = True
    report.save()
    messages.success(request, 'Report marked as resolved.')
    return redirect('core:manage_reports')


@staff_member_required
def manage_meetings(request):
    meetings = Meeting.objects.select_related('organizer')
    return render(request, 'core/manage_meetings.html', {'meetings': meetings})

# ---------- EDIT USER ----------
@staff_member_required
def edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user.username = request.POST.get('username')
        user.email = request.POST.get('email')
        user.save()
        messages.success(request, 'User updated successfully.')
        return redirect('core:manage_users')
    return render(request, 'core/edit_user.html', {'user': user})

# ---------- DELETE USER ----------
@staff_member_required
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.delete()
    messages.success(request, 'User deleted successfully.')
    return redirect('core:manage_users')

# ---------- EDIT SKILL ----------
@staff_member_required
def edit_skill(request, skill_id):
    skill = get_object_or_404(Skill, id=skill_id)
    if request.method == 'POST':
        form = SkillForm(request.POST, instance=skill)
        if form.is_valid():
            form.save()
            messages.success(request, 'Skill updated successfully.')
            return redirect('core:manage_skills')
    else:
        form = SkillForm(instance=skill)
    return render(request, 'core/edit_skill.html', {'form': form, 'skill': skill})

# ---------- DELETE SKILL ----------
@staff_member_required
def delete_skill(request, skill_id):
    skill = get_object_or_404(Skill, id=skill_id)
    skill.delete()
    messages.success(request, 'Skill deleted successfully.')
    return redirect('core:manage_skills')

@staff_member_required
def delete_request(request, request_id):
    skill_request = get_object_or_404(SkillRequest, id=request_id)
    skill_request.delete()
    messages.success(request, 'Skill request deleted successfully.')
    return redirect('core:manage_requests')

@staff_member_required
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    review.delete()
    messages.success(request, 'Review deleted successfully.')
    return redirect('core:manage_reviews')

# ---------- Manage Meetings ----------
@staff_member_required
def manage_meetings(request):
    meetings = Meeting.objects.select_related('organizer').prefetch_related('participants')
    return render(request, 'core/manage_meetings.html', {'meetings': meetings})

@staff_member_required
def edit_meeting(request, meeting_id):
    meeting = get_object_or_404(Meeting, id=meeting_id)
    if request.method == 'POST':
        form = MeetingForm(request.POST, instance=meeting, organizer=meeting.organizer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Meeting updated successfully.')
            return redirect('core:manage_meetings')
    else:
        form = MeetingForm(instance=meeting, organizer=meeting.organizer)
    return render(request, 'core/edit_meeting.html', {'form': form, 'meeting': meeting})

@staff_member_required
def delete_meeting(request, meeting_id):
    meeting = get_object_or_404(Meeting, id=meeting_id)
    meeting.delete()
    messages.success(request, 'Meeting deleted successfully.')
    return redirect('core:manage_meetings')

from django.db import transaction 

@login_required
def delete_account(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                user = request.user
                print(f"Starting deletion for user: {user.username}")  # Debug
                
                # Get user ID before any operations
                user_id = user.id
                username = user.username
                
                # Step 1: Logout the user FIRST
                logout(request)
                
                # Step 2: Delete using the user ID (avoids any user object reference issues)
                from django.contrib.auth.models import User
                from core.models import Meeting
                
                # Remove user from meeting participants (ManyToMany)
                user_to_delete = User.objects.get(id=user_id)
                user_to_delete.meetings.clear()
                
                # Delete the user - let database cascades handle the rest
                deletion_result = User.objects.filter(id=user_id).delete()
                print(f"Deletion result: {deletion_result}")  # Debug
                
                messages.success(request, 'Your account has been permanently deleted.')
                return redirect('core:login')
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Account deletion error for user {request.user.id if request.user.is_authenticated else 'unknown'}: {str(e)}")
            logger.error(f"Full error: {repr(e)}")
            
            messages.error(request, 'An error occurred while deleting your account. Please try again.')
            return redirect('core:index')
    
    return redirect('core:index')

# In views.py
import smtplib
from django.core.mail import send_mail, EmailMessage
from django.http import HttpResponse
from django.conf import settings
from django.contrib.auth.models import User

def debug_email_test(request):
    results = []
    
    try:
        # Test 1: Basic SMTP connection
        results.append("=== Testing SMTP Connection ===")
        server = smtplib.SMTP_SSL(settings.EMAIL_HOST, settings.EMAIL_PORT)
        server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        results.append("✓ SMTP Login Successful")
        server.quit()
    except Exception as e:
        results.append(f"✗ SMTP Connection Failed: {str(e)}")
    
    try:
        # Test 2: Send test email
        results.append("=== Testing Email Sending ===")
        send_mail(
            'SkillSwap Test Email',
            'This is a test email from SkillSwap.',
            settings.DEFAULT_FROM_EMAIL,
            [request.user.email] if request.user.is_authenticated else ['test@example.com'],
            fail_silently=False,
        )
        results.append("✓ Test email sent successfully")
    except Exception as e:
        results.append(f"✗ Email Sending Failed: {str(e)}")
    
    try:
        # Test 3: Test password reset specifically
        results.append("=== Testing Password Reset Flow ===")
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode
        
        user = request.user if request.user.is_authenticated else User.objects.first()
        if user:
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            results.append(f"✓ Password reset token generated for {user.email}")
        else:
            results.append("✗ No user found for testing")
            
    except Exception as e:
        results.append(f"✗ Password Reset Test Failed: {str(e)}")
    
    return HttpResponse('<br>'.join(results))