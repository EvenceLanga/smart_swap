from django import forms
from django.contrib.auth.models import User
from .models import Skill
from .models import StudentProfile
from .models import Meeting
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
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        input_formats=['%Y-%m-%dT%H:%M']
    )
    
    class Meta:
        model = Meeting
        fields = ['title', 'description', 'meeting_type', 'scheduled_date', 
                 'duration_minutes', 'location', 'participants', 'related_skill']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'participants': forms.SelectMultiple(attrs={'class': 'select2'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.organizer = kwargs.pop('organizer', None)
        super().__init__(*args, **kwargs)
        
        # Only show users who are not the organizer
        if self.organizer:
            self.fields['participants'].queryset = User.objects.exclude(id=self.organizer.id)
        
    def clean_scheduled_date(self):
        scheduled_date = self.cleaned_data['scheduled_date']
        if scheduled_date < timezone.now():
            raise forms.ValidationError("Meeting cannot be scheduled in the past.")
        return scheduled_date
    

class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = ['title', 'category', 'description', 'level', 'availability']
