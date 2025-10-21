from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import (
    User, Profile, Post, Comment, Person, Event, PostVerification, 
    PostReport, Like, VerificationRequest
)


class CustomUserCreationForm(UserCreationForm):
    """Custom user registration form with additional fields"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your first name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your last name'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Choose a username'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter a strong password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        })
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user


class CustomAuthenticationForm(AuthenticationForm):
    """Custom login form with Bootstrap styling"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Username or Email'
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password'
        })


class ProfileForm(forms.ModelForm):
    """Form for editing user profile"""
    profile_picture = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.jpg,.jpeg,.png,.gif,.webp,image/jpeg,image/png,image/gif,image/webp'}))
    uid_document = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}))
    
    class Meta:
        model = Profile
        fields = ['bio']
        widgets = {
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Tell us about yourself...'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['profile_picture'].initial = self.user.profile_picture
            self.fields['uid_document'].initial = self.user.uid_document
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.user:
            if 'profile_picture' in self.cleaned_data:
                self.user.profile_picture = self.cleaned_data['profile_picture']
            if 'uid_document' in self.cleaned_data:
                self.user.uid_document = self.cleaned_data['uid_document']
            if commit:
                self.user.save()
        if commit:
            profile.save()
        return profile


class UserEditForm(forms.ModelForm):
    """Form for editing user basic information"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First Name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last Name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email Address'
            })
        }


class PostForm(forms.ModelForm):
    """Form for creating and editing posts"""
    class Meta:
        model = Post
        fields = ['title', 'content', 'attachment', 'event', 'people']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter post title...'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Share your story, news, or information...'
            }),
            'attachment': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.jpg,.jpeg,.png,.gif,.webp,.mp4,.mov,.avi,.webm,.mkv,.mpeg,.mpg,.3gp,.ogg,.ogv,.wav,.mp3,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.zip,.rar,image/*,video/*,audio/*,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-powerpoint,application/vnd.openxmlformats-officedocument.presentationml.presentation,application/zip,application/x-rar-compressed'
            }),
            'event': forms.Select(attrs={
                'class': 'form-select'
            }),
            'people': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'size': 5
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['event'].queryset = Event.objects.filter(status='approved')
        self.fields['event'].empty_label = "Select an event (optional)"
        self.fields['people'].queryset = Person.objects.filter(status='approved')


class CommentForm(forms.ModelForm):
    """Form for adding comments to posts"""
    class Meta:
        model = Comment
        fields = ['content', 'attachment']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Add your comment...'
            }),
            'attachment': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.jpg,.jpeg,.png,.gif,.webp,.mp4,.mov,.avi,.webm,.mkv,.mpeg,.mpg,.3gp,.ogg,.ogv,.wav,.mp3,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.zip,.rar,image/*,video/*,audio/*,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-powerpoint,application/vnd.openxmlformats-officedocument.presentationml.presentation,application/zip,application/x-rar-compressed'
            })
        }


class PersonForm(forms.ModelForm):
    """Form for creating and editing people"""
    class Meta:
        model = Person
        fields = ['name', 'role', 'image']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full name of the person'
            }),
            'role': forms.Select(attrs={
                'class': 'form-select'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }


class EventForm(forms.ModelForm):
    """Form for creating events"""
    class Meta:
        model = Event
        fields = ['title', 'description', 'date', 'participants', 'journalists']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Event title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe the event...'
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'participants': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'size': 5
            }),
            'journalists': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'size': 5
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['participants'].queryset = Person.objects.filter(status='approved')
        self.fields['journalists'].queryset = User.objects.filter(role='journalist')


class PostVerificationForm(forms.ModelForm):
    """Form for verifying posts"""
    class Meta:
        model = PostVerification
        fields = ['type']
        widgets = {
            'type': forms.Select(attrs={
                'class': 'form-select'
            })
        }


class PostReportForm(forms.ModelForm):
    """Form for reporting posts"""
    class Meta:
        model = PostReport
        fields = ['reason']
        widgets = {
            'reason': forms.Select(attrs={
                'class': 'form-select'
            })
        }


class VerificationRequestForm(forms.ModelForm):
    """Form for requesting role verification"""
    
    class Meta:
        model = VerificationRequest
        fields = ['requested_role']
        widgets = {
            'requested_role': forms.Select(
                choices=[
                    ('journalist', 'Journalist'),
                    ('politician', 'Politician')
                ],
                attrs={
                    'class': 'form-select'
                }
            )
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only allow journalist and politician roles for verification requests
        self.fields['requested_role'].choices = [
            ('journalist', 'Journalist'),
            ('politician', 'Politician')
        ]


# Search and Filter Forms

class PostSearchForm(forms.Form):
    
    search = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search posts by title or content...'
        })
    )
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + Post.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    author = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        empty_label="All Authors",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    event = forms.ModelChoiceField(
        queryset=Event.objects.filter(status='approved'),
        required=False,
        empty_label="All Events",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )


class PeopleSearchForm(forms.Form):
    """Form for searching and filtering people"""
    search = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name or location...'
        })
    )
    role = forms.ChoiceField(
        choices=[('', 'All Roles')] + Person.ROLE_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    status = forms.ChoiceField(
        choices=[('', 'All Status'), ('pending', 'Pending'), ('approved', 'Approved')],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    location = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filter by location...'
        })
    )
    age_min = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=150,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min age'
        })
    )
    age_max = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=150,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max age'
        })
    )


class EventSearchForm(forms.Form):
    """Form for searching and filtering events"""
    search = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search events by title or description...'
        })
    )
    status = forms.ChoiceField(
        choices=[('', 'All Status'), ('pending', 'Pending'), ('approved', 'Approved')],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    creator = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        empty_label="All Creators",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )


class UserSearchForm(forms.Form):
    """Form for searching and filtering users (admin)"""
    search = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by username, email, or name...'
        })
    )
    role = forms.ChoiceField(
        choices=[('', 'All Roles')] + User.ROLE_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    is_verified = forms.ChoiceField(
        choices=[
            ('', 'All Users'),
            ('true', 'Verified Only'),
            ('false', 'Unverified Only')
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    is_active = forms.ChoiceField(
        choices=[
            ('', 'All Users'),
            ('true', 'Active Only'),
            ('false', 'Inactive Only')
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    date_joined_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    date_joined_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )


# Admin Forms

class AdminUserStatusForm(forms.Form):
    """Form for admin to change user status"""
    is_active = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    is_identity_verified = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Admin notes (optional)...'
        })
    )


class AdminPostStatusForm(forms.Form):
    """Form for admin to change post status"""
    status = forms.ChoiceField(
        choices=Post.STATUS_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    admin_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Admin notes (optional)...'
        })
    )


class AdminPersonStatusForm(forms.Form):
    """Form for admin to change person status"""
    status = forms.ChoiceField(
        choices=[('pending', 'Pending'), ('approved', 'Approved')],
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    admin_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Admin notes (optional)...'
        })
    )


class AdminEventStatusForm(forms.Form):
    """Form for admin to change event status"""
    status = forms.ChoiceField(
        choices=[('pending', 'Pending'), ('approved', 'Approved')],
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    admin_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Admin notes (optional)...'
        })
    )


class ReportHandlingForm(forms.Form):
    """Form for handling reports"""
    action = forms.ChoiceField(
        choices=[
            ('dismiss', 'Dismiss Report'),
            ('warn_user', 'Warn User'),
            ('remove_content', 'Remove Content'),
            ('suspend_user', 'Suspend User')
        ],
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    admin_notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Explain the action taken...'
        })
    )


class VerificationHandlingForm(forms.Form):
    """Form for handling verification requests"""
    action = forms.ChoiceField(
        choices=[
            ('approve', 'Approve Request'),
            ('reject', 'Reject Request')
        ],
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    admin_notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Explain the decision...'
        })
    )