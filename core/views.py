from venv import logger
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.views import redirect_to_login
from .forms import UserRegistrationForm, SkillForm, StudentProfileForm, MeetingForm
from .models import StudentProfile, Skill, SkillRequest, Review, Message, Notification, Meeting, Report, UserBlock, MessageRequest
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Avg, Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from datetime import timedelta, datetime
from django.views.decorators.csrf import csrf_exempt
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.db import transaction
import logging
import json
from django.views.decorators.http import require_POST

# ==============================
# EMAIL NOTIFICATION FUNCTIONS
# ==============================

def activate_account(request, uidb64, token):
    """Activate user account after email verification"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user and default_token_generator.check_token(user, token):
        if not user.is_active:
            user.is_active = True
            user.save()
            messages.success(request, 'Your account has been verified successfully! You can now log in.')
        else:
            messages.info(request, 'Your account is already active. You can log in.')
        return redirect('core:login')
    else:
        messages.error(request, 'Invalid or expired verification link. Please register again.')
        return redirect('core:register')
    
def send_email_notification(subject, template_name, context, recipient_list):
    """Generic function to send email notifications"""
    try:
        logger.info(f"📧 Attempting to send email: {subject} to {recipient_list}")
        
        # Check if we're in production and email is configured
        if settings.DEBUG:
            logger.info(f"DEBUG MODE: Would send email to {recipient_list}")
            # In debug mode, you might want to log instead of actually sending
            return True
            
        html_content = render_to_string(f'core/emails/{template_name}', context)
        text_content = "Please view this email in HTML format."
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipient_list,
            reply_to=[settings.DEFAULT_FROM_EMAIL]
        )
        email.attach_alternative(html_content, "text/html")
        
        result = email.send(fail_silently=False)
        logger.info(f"✅ Email sent successfully! Result: {result}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Email sending failed: {str(e)}")
        logger.error(f"Recipients: {recipient_list}")
        logger.error(f"Subject: {subject}")
        # Don't return False here - let the user continue even if email fails
        return True  # Change this to True to prevent registration from hanging

def notify_new_skill(skill):
    """Notify all users when a new skill is added"""
    try:
        users = User.objects.filter(is_active=True).exclude(id=skill.owner.id)
        
        subject = f"🎯 New Skill Available: {skill.title}"
        template_name = 'new_skill_notification.html'
        
        for user in users:
            context = {
                'user': user,
                'skill': skill,
                'skill_owner': skill.owner,
                'site_name': get_current_site(None).name,
            }
            
            send_email_notification(subject, template_name, context, [user.email])
            
            # Also create in-app notification
            Notification.objects.create(
                user=user,
                message=f"New skill available: {skill.title} by {skill.owner.username}",
                notification_type='new_skill'
            )
    except Exception as e:
        print(f"Error in notify_new_skill: {str(e)}")

def notify_skill_request(skill_request):
    """Notify skill owner when someone requests their skill"""
    try:
        subject = f"📬 New Skill Request: {skill_request.skill.title}"
        template_name = 'skill_request_notification.html'
        
        context = {
            'skill_owner': skill_request.owner,
            'requester': skill_request.requester,
            'skill': skill_request.skill,
            'request': skill_request,
            'site_name': get_current_site(None).name,
        }
        
        send_email_notification(subject, template_name, context, [skill_request.owner.email])
        
        # In-app notification
        Notification.objects.create(
            user=skill_request.owner,
            message=f"{skill_request.requester.username} requested to learn {skill_request.skill.title}",
            notification_type='skill_request'
        )
    except Exception as e:
        print(f"Error in notify_skill_request: {str(e)}")

def notify_request_status(skill_request, status):
    """Notify requester when their skill request is approved/rejected"""
    try:
        status_display = "approved" if status == 'APPROVED' else "rejected"
        subject = f"📝 Skill Request {status_display.capitalize()}: {skill_request.skill.title}"
        template_name = 'request_status_notification.html'
        
        context = {
            'requester': skill_request.requester,
            'skill_owner': skill_request.owner,
            'skill': skill_request.skill,
            'status': status,
            'status_display': status_display,
            'site_name': get_current_site(None).name,
        }
        
        send_email_notification(subject, template_name, context, [skill_request.requester.email])
        
        # In-app notification
        Notification.objects.create(
            user=skill_request.requester,
            message=f"Your request for {skill_request.skill.title} has been {status_display}",
            notification_type='request_status'
        )
    except Exception as e:
        print(f"Error in notify_request_status: {str(e)}")

def notify_meeting_invite(meeting, participant):
    """Notify participants when invited to a meeting"""
    try:
        subject = f"📅 Meeting Invitation: {meeting.title}"
        template_name = 'meeting_invite_notification.html'
        
        context = {
            'participant': participant,
            'meeting': meeting,
            'organizer': meeting.organizer,
            'site_name': get_current_site(None).name,
        }
        
        send_email_notification(subject, template_name, context, [participant.email])
        
        # In-app notification
        Notification.objects.create(
            user=participant,
            message=f"{meeting.organizer.username} invited you to a meeting: {meeting.title}",
            notification_type='meeting_invite'
        )
    except Exception as e:
        print(f"Error in notify_meeting_invite: {str(e)}")

def notify_meeting_update(meeting, participant, update_type):
    """Notify participants about meeting updates"""
    try:
        subject = f"🔄 Meeting Updated: {meeting.title}"
        template_name = 'meeting_update_notification.html'
        
        context = {
            'participant': participant,
            'meeting': meeting,
            'update_type': update_type,
            'organizer': meeting.organizer,
            'site_name': get_current_site(None).name,
        }
        
        send_email_notification(subject, template_name, context, [participant.email])
        
        # In-app notification
        Notification.objects.create(
            user=participant,
            message=f"Meeting '{meeting.title}' has been {update_type}",
            notification_type='meeting_update'
        )
    except Exception as e:
        print(f"Error in notify_meeting_update: {str(e)}")

def notify_new_review(review):
    """Notify skill owner when they receive a new review"""
    try:
        subject = f"⭐ New Review for Your Skill: {review.skill.title}"
        template_name = 'new_review_notification.html'
        
        context = {
            'skill_owner': review.skill.owner,
            'reviewer': review.reviewer,
            'review': review,
            'skill': review.skill,
            'site_name': get_current_site(None).name,
        }
        
        send_email_notification(subject, template_name, context, [review.skill.owner.email])
        
        # In-app notification
        Notification.objects.create(
            user=review.skill.owner,
            message=f"{review.reviewer.username} left a review for {review.skill.title}",
            notification_type='new_review'
        )
    except Exception as e:
        print(f"Error in notify_new_review: {str(e)}")

def notify_skill_session_start(skill_request):
    """Notify participants when a skill session starts"""
    try:
        subject = f"🚀 Skill Session Started: {skill_request.skill.title}"
        template_name = 'skill_session_start_notification.html'
        
        context = {
            'participant': skill_request.requester,
            'skill_owner': skill_request.owner,
            'skill': skill_request.skill,
            'skill_request': skill_request,
            'site_name': get_current_site(None).name,
        }
        
        send_email_notification(subject, template_name, context, [skill_request.requester.email])
        
        # In-app notification
        Notification.objects.create(
            user=skill_request.requester,
            message=f"Skill session for {skill_request.skill.title} has started!",
            notification_type='skill_session'
        )
    except Exception as e:
        print(f"Error in notify_skill_session_start: {str(e)}")

def notify_skill_session_complete(skill_request):
    """Notify participants when a skill session is completed"""
    try:
        subject = f"🎉 Skill Session Completed: {skill_request.skill.title}"
        template_name = 'skill_session_complete_notification.html'
        
        # Notify both parties
        for user in [skill_request.requester, skill_request.owner]:
            context = {
                'user': user,
                'other_user': skill_request.requester if user == skill_request.owner else skill_request.owner,
                'skill': skill_request.skill,
                'skill_request': skill_request,
                'site_name': get_current_site(None).name,
            }
            
            send_email_notification(subject, template_name, context, [user.email])
            
            # In-app notification
            Notification.objects.create(
                user=user,
                message=f"Skill session for {skill_request.skill.title} has been completed!",
                notification_type='skill_completed'
            )
    except Exception as e:
        print(f"Error in notify_skill_session_complete: {str(e)}")

def notify_new_message(message):
    """Notify user when they receive a new message"""
    try:
        subject = f"💬 New Message from {message.from_user.username}"
        template_name = 'new_message_notification.html'
        
        context = {
            'recipient': message.to_user,
            'sender': message.from_user,
            'message': message,
            'site_name': get_current_site(None).name,
        }
        
        send_email_notification(subject, template_name, context, [message.to_user.email])
        
        # In-app notification
        Notification.objects.create(
            user=message.to_user,
            message=f"New message from {message.from_user.username}",
            notification_type='message'
        )
    except Exception as e:
        print(f"Error in notify_new_message: {str(e)}")

# ==============================
# AUTHENTICATION VIEWS
# ==============================

def welcome(request):
    """Welcome page for non-authenticated users"""
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    
    skills = Skill.objects.order_by('-created_at')[:10]
    return render(request, 'core/welcome.html', {'skills': skills})

def index(request):
    """Home page for non-authenticated users"""
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    
    skills = Skill.objects.order_by('-created_at')[:10]
    return render(request, 'core/index.html', {'skills': skills})

def register(request):
    """User registration with email verification"""
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                new_user = form.save(commit=False)
                # TEMPORARY: Activate users immediately until email is fixed
                new_user.is_active = True
                new_user.save()

                # Try to send welcome email (but don't break if it fails)
                try:
                    current_site = get_current_site(request)
                    subject = 'Welcome to SkillSwap!'
                    html_message = render_to_string('core/emails/welcome_email.html', {
                        'user': new_user,
                        'domain': current_site.domain,
                    })
                    
                    text_message = f"""
                    Welcome to SkillSwap, {new_user.username}!
                    
                    Your account has been created successfully.
                    You can now log in and start sharing skills.
                    
                    Thank you,
                    The SkillSwap Team
                    """
                    
                    send_mail(
                        subject=subject,
                        message=text_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[new_user.email],
                        html_message=html_message,
                        fail_silently=True,  # Don't raise errors
                    )
                    
                    messages.success(request, 'Registration successful! Welcome email sent.')
                    logger.info(f"Welcome email sent to {new_user.email}")
                    
                except Exception as e:
                    logger.error(f"Email sending failed: {str(e)}")
                    messages.success(request, 'Registration successful! You can now log in.')
                
                return redirect('core:login')
                
            except Exception as e:
                logger.error(f"Registration error: {str(e)}")
                messages.error(request, 'An error occurred during registration. Please try again.')
                return render(request, 'core/register.html', {'form': form})
                
    else:
        form = UserRegistrationForm()

    return render(request, 'core/register.html', {'form': form})

def debug_info(request):
    """Debug view to check email configuration"""
    info = {
        'email_backend': settings.EMAIL_BACKEND,
        'email_host': settings.EMAIL_HOST,
        'email_port': settings.EMAIL_PORT,
        'email_user_set': bool(settings.EMAIL_HOST_USER),
        'email_pass_set': bool(settings.EMAIL_HOST_PASSWORD),
        'debug': settings.DEBUG,
        'allowed_hosts': settings.ALLOWED_HOSTS,
    }
    return JsonResponse(info)

@csrf_exempt
def user_login(request):
    """User login with email verification check"""
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_active:
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                return redirect('core:dashboard')
            else:
                # User exists but account is not active (email not verified)
                messages.error(request, 'Please verify your email address before logging in. Check your email for the verification link.')
                return render(request, 'core/login.html', {
                    'username': username,
                    'show_resend_verification': True
                })
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'core/login.html')

def resend_verification_email(request):
    """Resend email verification link"""
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            if user.is_active:
                messages.info(request, 'Your account is already active. You can log in.')
                return redirect('core:login')
            
            # Generate new verification email
            current_site = get_current_site(request)
            subject = 'Verify your SkillSwap account'
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            verification_link = f"http://{current_site.domain}{reverse('core:activate', args=[uid, token])}"

            message = render_to_string('core/verify_email.html', {
                'user': user,
                'verification_link': verification_link,
                'domain': current_site.domain,
            })

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            
            messages.success(request, 'Verification email sent! Please check your inbox.')
            return redirect('core:login')
            
        except User.DoesNotExist:
            messages.error(request, 'No account found with this email address.')
    
    return render(request, 'core/resend_verification.html')

def user_logout(request):
    """User logout"""
    logout(request)
    return redirect('core:index')

# ==============================
# PROFILE VIEWS
# ==============================

def view_profile(request, username):
    """View user profile"""
    profile_user = get_object_or_404(User, username=username)
    profile = getattr(profile_user, "profile", None)
    reviews = profile_user.reviews_received.all() if hasattr(profile_user, "reviews_received") else []
    
    return render(
        request,
        'core/view_profile.html',
        {'profile_user': profile_user, 'profile': profile, 'reviews': reviews}
    )

@login_required
def edit_profile(request):
    """Allow current user to edit their own profile"""
    profile, created = StudentProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = StudentProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('core:view_profile', username=request.user.username)
    else:
        form = StudentProfileForm(instance=profile)
    
    return render(request, 'core/edit_profile.html', {'form': form})

# ==============================
# DASHBOARD & MAIN VIEWS
# ==============================

@login_required
def dashboard(request):
    """User dashboard"""
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

@login_required
def skill_requests(request):
    """View for managing skill requests"""
    requests_made = request.user.requests_made.all()
    requests_received = request.user.requests_received.all()
    
    return render(request, 'core/skill_requests.html', {
        'requests_made': requests_made,
        'requests_received': requests_received,
    })

# ==============================
# SKILL MANAGEMENT VIEWS
# ==============================

def skill_list(request):
    """List all skills with filtering and pagination"""
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
        skills = skills.annotate(request_count=Count('requests')).order_by('-request_count', '-created_at')
    elif sort_by == 'rating':
        skills = skills.annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating', '-created_at')
    elif sort_by == 'recent':
        skills = skills.order_by('-created_at')
    elif sort_by == 'name':
        skills = skills.order_by('title')
    else:
        skills = skills.order_by('-created_at')
    
    # Add additional context for each skill
    for skill in skills:
        skill.is_new = (timezone.now() - skill.created_at).days <= 7
        avg_rating = skill.reviews.aggregate(Avg('rating'))['rating__avg']
        skill.average_rating = round(avg_rating, 1) if avg_rating else None
        skill.request_count = skill.requests.count()
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(skills, 12)
    
    try:
        skills_page = paginator.page(page)
    except PageNotAnInteger:
        skills_page = paginator.page(1)
    except EmptyPage:
        skills_page = paginator.page(paginator.num_pages)
    
    # Get unique categories for filter dropdown
    categories = Skill.objects.values_list('category', flat=True).distinct().order_by('category')
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

@login_required
def create_skill(request):
    """Create a new skill"""
    if request.method == 'POST':
        form = SkillForm(request.POST)
        if form.is_valid():
            skill = form.save(commit=False)
            skill.owner = request.user
            skill.save()
            
            # Send notification to all users about new skill
            notify_new_skill(skill)
            
            messages.success(request, 'Skill created and notified all users!')
            return redirect('core:skill_list')
    else:
        form = SkillForm()
    return render(request, 'core/create_skill.html', {'form': form})

def skill_detail(request, skill_id):
    """View skill details"""
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

@login_required
def request_skill(request, skill_id):
    """Request to learn a skill"""
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
    
    # DEBUG: Log the notification attempt
    logger = logging.getLogger(__name__)
    logger.info(f"Creating skill request: {req.id}")
    logger.info(f"Skill owner: {skill.owner.username} ({skill.owner.email})")
    logger.info(f"Requester: {request.user.username} ({request.user.email})")
    
    # Send notification to skill owner
    try:
        notify_skill_request(req)
        logger.info("Skill request notification function called successfully")
    except Exception as e:
        logger.error(f"Error in notify_skill_request: {str(e)}")
        messages.warning(request, 'Request sent, but there was an issue with notifications.')
    else:
        messages.success(request, 'Request sent to skill owner.')
    
    return redirect('core:dashboard')

@login_required
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
    notify_skill_session_start(skill_request)
    
    messages.success(request, f"Skill session with {skill_request.requester.username} started!")
    return redirect('core:dashboard')

@login_required
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
    
    # Send notification to both parties
    notify_skill_session_complete(skill_request)
    
    messages.success(request, f"Skill session completed successfully!")
    return redirect('core:dashboard')

@login_required
def accept_request(request, request_id):
    """Accept a skill request"""
    req = get_object_or_404(SkillRequest, id=request_id, owner=request.user)
    req.status = 'APPROVED'
    req.save()
    
    # Send notification to requester
    notify_request_status(req, 'APPROVED')
    
    messages.success(request, 'Request accepted.')
    return redirect('core:dashboard')

@login_required
def reject_request(request, request_id):
    """Reject a skill request"""
    req = get_object_or_404(SkillRequest, id=request_id, owner=request.user)
    req.status = 'REJECTED'
    req.save()
    
    # Send notification to requester
    notify_request_status(req, 'REJECTED')
    
    messages.success(request, 'Request rejected.')
    return redirect('core:dashboard')

@login_required
def complete_request(request, request_id):
    """Mark a request as completed"""
    req = get_object_or_404(SkillRequest, id=request_id)
    if request.user not in [req.requester, req.owner]:
        messages.error(request, 'Not authorized.')
        return redirect('core:dashboard')
    req.status = 'COMPLETED'
    req.save()
    messages.success(request, 'Marked as completed. Please leave a review.')
    return redirect('core:dashboard')

# ==============================
# REVIEW VIEWS
# ==============================

@login_required
def add_review(request, skill_id):
    """Add a review for a skill"""
    skill = get_object_or_404(Skill, id=skill_id)

    if request.method == 'POST':
        rating = int(request.POST.get('rating'))
        comment = request.POST.get('comment')

        # Allow both owner and other users to review/comment
        review = Review.objects.create(
            skill=skill,
            reviewer=request.user,
            rating=rating,
            comment=comment,
            created_at=timezone.now()
        )
        
        # Send notification to skill owner about new review
        if request.user != skill.owner:
            notify_new_review(review)
        
        messages.success(request, 'Your review or comment has been submitted.')
        return redirect('core:skill_detail', skill_id=skill_id)

@login_required
def edit_review(request, review_id):
    """Edit a review"""
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

@login_required
def delete_review(request, review_id):
    """Delete a review"""
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

# ==============================
# MESSAGING VIEWS
# ==============================

@login_required
def send_message(request):
    """Send a message to another user"""
    users = User.objects.exclude(id=request.user.id)
    preselect = request.GET.get('to')

    if request.method == 'POST':
        recipient_id = request.POST.get('to_user')
        message_text = request.POST.get('message')
        recipient = get_object_or_404(User, id=recipient_id)

        message = Message.objects.create(
            from_user=request.user,
            to_user=recipient,
            content=message_text
        )

        # Send email notification for new message
        notify_new_message(message)

        messages.success(request, f"Message sent to {recipient.username}.")
        return redirect('core:inbox')

    return render(request, 'core/send_message.html', {'users': users, 'preselect': preselect})

@login_required
def inbox(request):
    """View user's inbox"""
    messages = Message.objects.filter(
        Q(to_user=request.user) | Q(from_user=request.user)
    ).order_by('sent_at')

    return render(request, 'core/inbox.html', {'messages': messages})

@login_required
def reply_message(request):
    """Reply to a message"""
    if request.method == 'POST':
        to_user_id = request.POST.get('to_user_id')
        content = request.POST.get('content')
        attachment = request.FILES.get('attachment')

        try:
            to_user = User.objects.get(id=to_user_id)
        except User.DoesNotExist:
            messages.error(request, "User not found.")
            return redirect('core:inbox')

        message = Message.objects.create(
            from_user=request.user,
            to_user=to_user,
            content=content,
            attachment=attachment
        )
        
        # Send notification for reply
        notify_new_message(message)
        
        messages.success(request, "Reply sent successfully!")
    return redirect('core:inbox')

@login_required
def chat_room(request, username):
    """Chat room with specific user"""
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

@login_required
def chat_dashboard(request):
    """Main chat dashboard with conversation list and active chat"""
    
    # Get all unique users that the current user has conversed with
    sent_to_users = Message.objects.filter(
        from_user=request.user
    ).values_list('to_user', flat=True).distinct()
    
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
    
    # Initialize blocking and message request status with safe defaults
    is_blocked = False
    has_blocked_you = False
    has_pending_request = False
    is_pending_request_receiver = False
    has_rejected_request = False
    
    if selected_user:
        active_user = get_object_or_404(User, username=selected_user)
        active_messages = Message.objects.filter(
            Q(from_user=request.user, to_user=active_user) |
            Q(from_user=active_user, to_user=request.user)
        ).order_by('sent_at')
        
        # FLEXIBLE BLOCKING CHECK - Try multiple field name patterns
        try:
            # Pattern 1: blocker/blocked (your defined model)
            is_blocked = UserBlock.objects.filter(
                blocker=request.user, 
                blocked=active_user
            ).exists()
            has_blocked_you = UserBlock.objects.filter(
                blocker=active_user, 
                blocked=request.user
            ).exists()
        except Exception as e:
            try:
                # Pattern 2: from_user/to_user
                is_blocked = UserBlock.objects.filter(
                    from_user=request.user, 
                    to_user=active_user
                ).exists()
                has_blocked_you = UserBlock.objects.filter(
                    from_user=active_user, 
                    to_user=request.user
                ).exists()
            except Exception as e2:
                try:
                    # Pattern 3: user/blocked_user
                    is_blocked = UserBlock.objects.filter(
                        user=request.user, 
                        blocked_user=active_user
                    ).exists()
                    has_blocked_you = UserBlock.objects.filter(
                        user=active_user, 
                        blocked_user=request.user
                    ).exists()
                except Exception as e3:
                    print(f"DEBUG: All blocking patterns failed: {e}, {e2}, {e3}")
                    is_blocked = False
                    has_blocked_you = False
        
        # FLEXIBLE MESSAGE REQUEST CHECK - Try multiple field name patterns
        try:
            # Pattern 1: sender/receiver
            has_pending_request = MessageRequest.objects.filter(
                sender=request.user,
                receiver=active_user,
                status='pending'
            ).exists()
            
            is_pending_request_receiver = MessageRequest.objects.filter(
                sender=active_user,
                receiver=request.user,
                status='pending'
            ).exists()
            
            has_rejected_request = MessageRequest.objects.filter(
                Q(sender=request.user, receiver=active_user) |
                Q(sender=active_user, receiver=request.user),
                status='rejected'
            ).exists()
        except Exception as e:
            try:
                # Pattern 2: from_user/to_user
                has_pending_request = MessageRequest.objects.filter(
                    from_user=request.user,
                    to_user=active_user,
                    status='pending'
                ).exists()
                
                is_pending_request_receiver = MessageRequest.objects.filter(
                    from_user=active_user,
                    to_user=request.user,
                    status='pending'
                ).exists()
                
                has_rejected_request = MessageRequest.objects.filter(
                    Q(from_user=request.user, to_user=active_user) |
                    Q(from_user=active_user, to_user=request.user),
                    status='rejected'
                ).exists()
            except Exception as e2:
                print(f"DEBUG: All message request patterns failed: {e}, {e2}")
                has_pending_request = False
                is_pending_request_receiver = False
                has_rejected_request = False
        
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
        'user_data': user_data,
        'active_user': active_user,
        'active_messages': active_messages,
        'upcoming_meetings': upcoming_meetings,
        'users': User.objects.exclude(id=request.user.id),
        'is_blocked': is_blocked,
        'has_blocked_you': has_blocked_you,
        'has_pending_request': has_pending_request,
        'is_pending_request_receiver': is_pending_request_receiver,
        'has_rejected_request': has_rejected_request,
    })

@login_required
def send_chat_message(request):
    """Send message from chat interface"""
    if request.method == 'POST':
        to_user_id = request.POST.get('to_user')
        content = request.POST.get('content')
        attachment = request.FILES.get('attachment')
        
        if to_user_id and content:
            to_user = get_object_or_404(User, id=to_user_id)
            
            # Check if user is blocked
            if UserBlock.objects.filter(blocker=request.user, blocked=to_user).exists():
                messages.error(request, 'You have blocked this user.')
                return redirect(f'/chat/?user={to_user.username}')
            
            if UserBlock.objects.filter(blocker=to_user, blocked=request.user).exists():
                messages.error(request, 'This user has blocked you.')
                return redirect(f'/chat/?user={to_user.username}')
            
            # Check message request status
            message_request = MessageRequest.objects.filter(
                Q(sender=request.user, receiver=to_user) |
                Q(sender=to_user, receiver=request.user)
            ).first()
            
            if message_request:
                if message_request.status == 'rejected':
                    messages.error(request, 'Message request was rejected.')
                    return redirect(f'/chat/?user={to_user.username}')
                elif message_request.status == 'pending':
                    messages.error(request, 'Message request is still pending.')
                    return redirect(f'/chat/?user={to_user.username}')
            else:
                # Create a new message request for first-time messaging
                if not Message.objects.filter(
                    Q(from_user=request.user, to_user=to_user) |
                    Q(from_user=to_user, to_user=request.user)
                ).exists():
                    MessageRequest.objects.create(
                        sender=request.user,
                        receiver=to_user,
                        message=content
                    )
                    messages.success(request, 'Message request sent! The user will need to accept it first.')
                    return redirect(f'/chat/?user={to_user.username}')
            
            # Create the message
            message = Message.objects.create(
                from_user=request.user,
                to_user=to_user,
                content=content,
                attachment=attachment
            )
            
            # Send notification for new message
            notify_new_message(message)
            
            messages.success(request, "Message sent!")
            return redirect(f'/chat/?user={to_user.username}')
    
    return redirect('core:chat_dashboard')

@login_required
def mark_messages_read(request, username):
    """Mark messages from a user as read"""
    other_user = get_object_or_404(User, username=username)
    Message.objects.filter(
        from_user=other_user, to_user=request.user, is_read=False
    ).update(is_read=True)
    
    return JsonResponse({'status': 'success'})

@login_required
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

@login_required
def conversation(request, username):
    """View conversation with specific user"""
    other_user = get_object_or_404(User, username=username)
    messages = Message.objects.filter(
        Q(from_user=request.user, to_user=other_user) |
        Q(from_user=other_user, to_user=request.user)
    ).order_by('sent_at')
    return render(request, 'core/conversation.html', {'messages': messages, 'other_user': other_user})

# ==============================
# MEETING VIEWS
# ==============================

@login_required
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
                    notify_meeting_invite(meeting, participant)
            
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

@login_required
def calendar(request):
    """Calendar view of meetings"""
    meetings = Meeting.objects.filter(
        Q(organizer=request.user) | Q(participants=request.user)
    ).distinct().select_related('organizer', 'related_skill')
    
    context = {
        'meetings': meetings,
    }
    return render(request, 'core/calendar.html', context)

@login_required
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
                notify_meeting_invite(meeting, other_user)
            
            messages.success(request, f"Meeting scheduled successfully with {other_user.get_full_name() or other_user.username}!")
            return redirect('core:chat_dashboard')
            
    else:
        # Pre-fill with default values and the target user as participant
        default_time = timezone.now() + timedelta(hours=24)
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

@login_required
def meeting_detail(request, meeting_id):
    """View meeting details"""
    meeting = get_object_or_404(Meeting, id=meeting_id)
    
    # Check if user is organizer or participant
    if request.user != meeting.organizer and request.user not in meeting.participants.all():
        messages.error(request, "You don't have permission to view this meeting.")
        return redirect('core:my_meetings')
    
    return render(request, 'core/meeting_detail.html', {
        'meeting': meeting,
        'now': timezone.now()
    })

@login_required
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

@login_required
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
            notify_meeting_update(meeting, participant, status)
        
        messages.success(request, f"Meeting status updated to {status}.")
    
    return redirect('core:meeting_detail', meeting_id=meeting.id)

@login_required
def meeting_calendar(request):
    """Calendar view of meetings"""
    meetings = Meeting.objects.filter(
        Q(organizer=request.user) | Q(participants=request.user)
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

# ==============================
# ADMIN VIEWS
# ==============================

@staff_member_required
def admin_portal(request):
    """Admin portal dashboard"""
    return render(request, 'core/admin_portal.html')

@staff_member_required
def admin_dashboard(request):
    """Admin dashboard with statistics"""
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

@staff_member_required
def manage_users(request):
    """Manage users (admin only)"""
    users = User.objects.all()
    return render(request, 'core/manage_users.html', {'users': users})

@staff_member_required
def edit_user(request, user_id):
    """Edit user (admin only)"""
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user.username = request.POST.get('username')
        user.email = request.POST.get('email')
        user.save()
        messages.success(request, 'User updated successfully.')
        return redirect('core:manage_users')
    return render(request, 'core/edit_user.html', {'user': user})

@staff_member_required
def delete_user(request, user_id):
    """Delete user (admin only)"""
    user = get_object_or_404(User, id=user_id)
    user.delete()
    messages.success(request, 'User deleted successfully.')
    return redirect('core:manage_users')

@staff_member_required
def manage_skills(request):
    """Manage skills (admin only)"""
    skills = Skill.objects.all()
    return render(request, 'core/manage_skills.html', {'skills': skills})

@staff_member_required
def edit_skill(request, skill_id):
    """Edit skill (admin only)"""
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

@staff_member_required
def delete_skill(request, skill_id):
    """Delete skill (admin only)"""
    skill = get_object_or_404(Skill, id=skill_id)
    skill.delete()
    messages.success(request, 'Skill deleted successfully.')
    return redirect('core:manage_skills')

@staff_member_required
def manage_requests(request):
    """Manage skill requests (admin only)"""
    status_filter = request.GET.get('status', '')
    if status_filter:
        requests = SkillRequest.objects.filter(status=status_filter)
    else:
        requests = SkillRequest.objects.all()
    
    return render(request, 'core/manage_requests.html', {
        'requests': requests,
        'current_status': status_filter
    })

@staff_member_required
def approve_request(request, request_id):
    """Approve skill request (admin only)"""
    skill_request = get_object_or_404(SkillRequest, id=request_id)
    skill_request.status = 'APPROVED'
    skill_request.save()
    messages.success(request, f'Skill request #{skill_request.id} has been approved.')
    return redirect('core:manage_requests')

@staff_member_required
def reject_request(request, request_id):
    """Reject skill request (admin only)"""
    skill_request = get_object_or_404(SkillRequest, id=request_id)
    skill_request.status = 'REJECTED'
    skill_request.save()
    messages.success(request, f'Skill request #{skill_request.id} has been rejected.')
    return redirect('core:manage_requests')

@staff_member_required
def delete_request(request, req_id):
    """Delete skill request (admin only)"""
    req = get_object_or_404(SkillRequest, id=req_id)
    req.delete()
    messages.success(request, 'Skill request deleted successfully.')
    return redirect('core:manage_requests')

@staff_member_required
def manage_reviews(request):
    """Manage reviews (admin only)"""
    reviews = Review.objects.all()
    return render(request, 'core/manage_reviews.html', {'reviews': reviews})

@staff_member_required
def delete_review(request, review_id):
    """Delete review (admin only)"""
    review = get_object_or_404(Review, id=review_id)
    review.delete()
    messages.success(request, 'Review deleted successfully.')
    return redirect('core:manage_reviews')

@staff_member_required
def manage_reports(request):
    """Manage reports (admin only)"""
    reports = Report.objects.all()
    return render(request, 'core/manage_reports.html', {'reports': reports})

@staff_member_required
def resolve_report(request, report_id):
    """Resolve report (admin only)"""
    report = get_object_or_404(Report, id=report_id)
    report.resolved = True
    report.save()
    messages.success(request, 'Report marked as resolved.')
    return redirect('core:manage_reports')

@staff_member_required
def manage_meetings(request):
    """Manage meetings (admin only)"""
    meetings = Meeting.objects.select_related('organizer').prefetch_related('participants')
    return render(request, 'core/manage_meetings.html', {'meetings': meetings})

@staff_member_required
def edit_meeting(request, meeting_id):
    """Edit meeting (admin only)"""
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
    """Delete meeting (admin only)"""
    meeting = get_object_or_404(Meeting, id=meeting_id)
    meeting.delete()
    messages.success(request, 'Meeting deleted successfully.')
    return redirect('core:manage_meetings')

# ==============================
# UTILITY VIEWS
# ==============================

@login_required
def delete_account(request):
    """Delete user account"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                user = request.user
                print(f"Starting deletion for user: {user.username}")
                
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
                print(f"Deletion result: {deletion_result}")
                
                messages.success(request, 'Your account has been permanently deleted.')
                return redirect('core:login')
                
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Account deletion error for user {request.user.id if request.user.is_authenticated else 'unknown'}: {str(e)}")
            logger.error(f"Full error: {repr(e)}")
            
            messages.error(request, 'An error occurred while deleting your account. Please try again.')
            return redirect('core:index')
    
    return redirect('core:index')

def user_profile(request, user_id):
    """View user profile by ID"""
    profile_user = get_object_or_404(User, id=user_id)
    skills = Skill.objects.filter(owner=profile_user)
    return render(request, 'core/user_profile.html', {'profile_user': profile_user, 'skills': skills})

def search_skills(request):
    """Search skills"""
    query = request.GET.get('q')
    if query:
        results = Skill.objects.filter(title__icontains=query)
    else:
        results = Skill.objects.none()
    return render(request, 'core/search_results.html', {'results': results, 'query': query})

@login_required
def notifications(request):
    """View user notifications"""
    user_notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'core/notifications.html', {'notifications': user_notifications})

def debug_urls(request):
    """Debug URL patterns"""
    from django.urls import get_resolver
    resolver = get_resolver()
    url_list = []
    
    for pattern in resolver.url_patterns:
        if hasattr(pattern, 'pattern'):
            url_list.append(f"{pattern.pattern} -> {getattr(pattern, 'name', 'No name')}")
    
    return HttpResponse('<br>'.join(sorted(url_list)))


@login_required
def test_email(request):
    """Test email functionality"""
    try:
        # Test basic email
        send_mail(
            'Test Email from SkillSwap',
            'This is a test email to verify your email configuration.',
            settings.DEFAULT_FROM_EMAIL,
            [request.user.email],
            fail_silently=False,
        )
        
        # Test notification email
        test_skill = Skill.objects.first()
        if test_skill:
            notify_skill_request(SkillRequest.objects.create(
                skill=test_skill,
                requester=request.user,
                owner=test_skill.owner,
                status='PENDING'
            ))
        
        messages.success(request, f'Test emails sent to {request.user.email}. Check your inbox and spam folder.')
    except Exception as e:
        messages.error(request, f'Email test failed: {str(e)}')
    
    return redirect('core:dashboard')

# ==============================
# BLOCKING & MESSAGE REQUESTS
# ==============================
# views.py
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json

@login_required
@require_POST
def block_user(request, username):
    try:
        print(f"Block user called for: {username} by {request.user.username}")  # Debug
        
        # Get the user to block
        try:
            user_to_block = User.objects.get(username=username)
        except User.DoesNotExist:
            return JsonResponse({
                'status': 'error', 
                'message': f'User {username} not found'
            }, status=404)
        
        # Don't allow blocking yourself
        if request.user.id == user_to_block.id:
            return JsonResponse({
                'status': 'error', 
                'message': 'You cannot block yourself'
            }, status=400)
        
        # Check if already blocked
        existing_block = UserBlock.objects.filter(
            blocker=request.user,
            blocked=user_to_block
        ).first()
        
        if existing_block:
            return JsonResponse({
                'status': 'success', 
                'message': 'User was already blocked',
                'blocked': True
            })
        
        # Create the block
        block = UserBlock.objects.create(
            blocker=request.user,
            blocked=user_to_block
        )
        
        # Update any pending message requests
        MessageRequest.objects.filter(
            from_user=user_to_block, 
            to_user=request.user,
            status='PENDING'
        ).update(status='DECLINED')
        
        print(f"Successfully blocked {username}")  # Debug
        
        return JsonResponse({
            'status': 'success', 
            'message': f'You have blocked {username}',
            'blocked': True
        })
        
    except Exception as e:
        print(f"Error blocking user: {str(e)}")  # Debug
        return JsonResponse({
            'status': 'error', 
            'message': str(e)
        }, status=500)
    
@login_required
def blocked_users_list(request):
    """View to show list of blocked users"""
    # Get all users blocked by the current user
    blocked_relations = UserBlock.objects.filter(blocker=request.user)
    blocked_users = [relation.blocked for relation in blocked_relations]
    
    return render(request, 'core/blocked_users.html', {'blocked_users': blocked_users})

@login_required
@require_POST
def unblock_user(request, username):
    """Unblock a user - POST only"""
    try:
        user_to_unblock = get_object_or_404(User, username=username)
        
        # Delete the block relationship
        deleted_count, _ = UserBlock.objects.filter(
            blocker=request.user,
            blocked=user_to_unblock
        ).delete()
        
        if deleted_count > 0:
            messages.success(request, f'You have unblocked {username}')
            print(f"Successfully unblocked {username}")  # Debug
        else:
            messages.warning(request, f'You had not blocked {username}')
            
    except Exception as e:
        messages.error(request, f'Error unblocking user: {str(e)}')
        print(f"Error in unblock_user: {str(e)}")  # Debug
    
    # Always redirect back to the blocked users list
    return redirect('core:blocked_users_list')

@login_required
@require_POST
def accept_message_request(request, username):
    """Accept a message request"""
    try:
        sender = User.objects.get(username=username)
        
        # Update message request status
        message_request = MessageRequest.objects.get(
            sender=sender,
            receiver=request.user,
            status='pending'
        )
        message_request.status = 'accepted'
        message_request.save()
        
        return JsonResponse({'success': True})
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'})
    except MessageRequest.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Message request not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_POST
def reject_message_request(request, username):
    """Reject a message request"""
    try:
        sender = User.objects.get(username=username)
        
        # Update message request status
        message_request = MessageRequest.objects.get(
            sender=sender,
            receiver=request.user,
            status='pending'
        )
        message_request.status = 'rejected'
        message_request.save()
        
        return JsonResponse({'success': True})
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'})
    except MessageRequest.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Message request not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# ADD THIS MISSING FUNCTION:
@login_required
@require_POST
def decline_message_request(request, request_id):
    """Decline a message request by ID (alternative approach)"""
    try:
        message_request = get_object_or_404(MessageRequest, id=request_id, to_user=request.user)
        
        if message_request.status == 'pending':
            message_request.status = 'rejected'
            message_request.save()
            
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'Message request already processed'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_POST
def report_user(request, username):
    """Report a user"""
    try:
        data = json.loads(request.body)
        reason = data.get('reason', '')
        
        user_to_report = User.objects.get(username=username)
        
        # Here you would typically save the report to a database
        # For now, we'll just log it
        print(f"User {request.user.username} reported {username} for: {reason}")
        
        # In a real application, you might want to:
        # 1. Save the report to a database
        # 2. Send an email to admins
        # 3. Trigger moderation actions
        
        return JsonResponse({'success': True})
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def message_requests(request):
    """View pending message requests"""
    pending_requests = MessageRequest.objects.filter(
        to_user=request.user, 
        status='PENDING'
    )
    
    return render(request, 'core/message_requests.html', {
        'pending_requests': pending_requests
    })

@login_required
def blocked_users(request):
    """View blocked users"""
    blocked_users = User.objects.filter(
        id__in=UserBlock.objects.filter(blocker=request.user).values('blocked')
    )
    
    return render(request, 'core/blocked_users.html', {
        'blocked_users': blocked_users
    })


@login_required
def debug_userblock_fields(request):
    """Debug view to check UserBlock fields"""
    from core.models import UserBlock
    fields = [f.name for f in UserBlock._meta.get_fields()]
    return JsonResponse({'fields': fields})

@login_required
def debug_userblock(request):
    """Debug UserBlock model"""
    try:
        # Test if we can query UserBlock
        block_count = UserBlock.objects.count()
        fields = [f.name for f in UserBlock._meta.get_fields()]
        
        # Try to create a test block (with yourself to avoid affecting real users)
        test_block, created = UserBlock.objects.get_or_create(
            blocker=request.user,
            blocked=request.user  # Block yourself for testing
        )
        
        return JsonResponse({
            'success': True,
            'block_count': block_count,
            'fields': fields,
            'test_block_created': created,
            'test_block_id': test_block.id
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        })
    

@login_required
def debug_models(request):
    """Debug both models to see actual field names"""
    from core.models import UserBlock, MessageRequest
    
    userblock_fields = []
    for field in UserBlock._meta.get_fields():
        userblock_fields.append({
            'name': field.name,
            'type': type(field).__name__,
            'related_model': getattr(field, 'related_model', None)
        })
    
    messagerequest_fields = []
    for field in MessageRequest._meta.get_fields():
        messagerequest_fields.append({
            'name': field.name,
            'type': type(field).__name__,
            'related_model': getattr(field, 'related_model', None)
        })
    
    return JsonResponse({
        'UserBlock_fields': userblock_fields,
        'MessageRequest_fields': messagerequest_fields
    })