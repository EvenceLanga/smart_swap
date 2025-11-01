from django import forms
from django.contrib.auth.models import User
from .models import Skill, StudentProfile, Meeting
from django.utils import timezone

class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Repeat password', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('username','first_name','email')

    def clean_password2(self):
        cd = self.cleaned_data
        if cd.get('password') != cd.get('password2'):
            raise forms.ValidationError('Passwords don\'t match.')
        return cd.get('password2')

class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = ['title','category','description','level','availability']

class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ['photo', 'course', 'year', 'bio', 'skills_offered', 'skills_wanted']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Tell us about yourself...'}),
            'skills_offered': forms.Textarea(attrs={'rows': 2, 'placeholder': 'e.g. Python, Painting, Public Speaking'}),
            'skills_wanted': forms.Textarea(attrs={'rows': 2, 'placeholder': 'e.g. Guitar, Spanish, Data Analysis'}),
        }

class MeetingForm(forms.ModelForm):
    scheduled_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'form-input',
            'min': timezone.now().strftime('%Y-%m-%dT%H:%M')
        }),
        input_formats=['%Y-%m-%dT%H:%M']
    )
    
    participants = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select select2-multiple',
            'data-placeholder': 'Select participants...'
        }),
        required=False
    )
    
    location = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'id': 'location-input',
            'placeholder': 'Start typing address or enter meeting link...'
        }),
        required=False,
        help_text="Enter physical address or video call link"
    )
    
    duration_minutes = forms.IntegerField(
        min_value=15,
        max_value=480,
        initial=60,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'min': '15',
            'max': '480',
            'step': '15'
        })
    )
    
    class Meta:
        model = Meeting
        fields = ['title', 'description', 'meeting_type', 'scheduled_date', 
                 'duration_minutes', 'location', 'participants', 'related_skill']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter meeting title...'
            }),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-textarea',
                'placeholder': 'Describe the purpose of this meeting...'
            }),
            'meeting_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'related_skill': forms.Select(attrs={
                'class': 'form-select'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        organizer = kwargs.pop('organizer', None)
        super().__init__(*args, **kwargs)
        
        # Only show users who are not the organizer
        if organizer:
            self.fields['participants'].queryset = User.objects.exclude(id=organizer.id)
        
        # Set initial duration if not provided
        if not self.initial.get('duration_minutes'):
            self.initial['duration_minutes'] = 60
            
        # Set minimum datetime for scheduled_date
        now = timezone.now()
        self.fields['scheduled_date'].widget.attrs['min'] = now.strftime('%Y-%m-%dT%H:%M')
        
        # Add help text for scheduled_date
        self.fields['scheduled_date'].help_text = f"Meetings cannot be scheduled before {now.strftime('%Y-%m-%d %H:%M')}"
    
    def clean_scheduled_date(self):
        scheduled_date = self.cleaned_data['scheduled_date']
        if scheduled_date < timezone.now():
            raise forms.ValidationError("Meeting cannot be scheduled in the past.")
        
        # Check if scheduled date is too far in the future (optional)
        max_future_date = timezone.now() + timezone.timedelta(days=365)  # 1 year max
        if scheduled_date > max_future_date:
            raise forms.ValidationError("Meeting cannot be scheduled more than 1 year in advance.")
            
        return scheduled_date
    
    def clean_duration_minutes(self):
        duration = self.cleaned_data['duration_minutes']
        if duration < 15:
            raise forms.ValidationError("Meeting duration must be at least 15 minutes.")
        if duration > 480:  # 8 hours
            raise forms.ValidationError("Meeting duration cannot exceed 8 hours.")
        return duration
    
    def clean_participants(self):
        participants = self.cleaned_data['participants']
        # You can add additional validation for participants if needed
        return participants
    
    def clean(self):
        cleaned_data = super().clean()
        scheduled_date = cleaned_data.get('scheduled_date')
        duration_minutes = cleaned_data.get('duration_minutes')
        
        # Check if meeting ends in the past (just in case)
        if scheduled_date and duration_minutes:
            end_time = scheduled_date + timezone.timedelta(minutes=duration_minutes)
            if end_time < timezone.now():
                raise forms.ValidationError(
                    "The meeting would end in the past. Please adjust the date/time or duration."
                )
        
        return cleaned_data