from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile, BlogPost, Comment

class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    profile_picture = forms.ImageField(required=False)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already in use. Please use a different email.")
        return email

class ProfileUpdateForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=50, 
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control shadow-sm', 'placeholder': 'Enter first name'})
    )
    last_name = forms.CharField(
        max_length=50, 
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control shadow-sm', 'placeholder': 'Enter first name'})
    )

    class Meta:
        model = Profile
        fields = ['profile_picture', 'cover_image', 'bio', 'facebook', 'twitter', 'linkedin']
        widgets = {
            'bio': forms.Textarea(attrs={'class': 'form-control shadow-sm', 'rows': 3, 'placeholder': 'Write something about yourself...'}),
            'facebook': forms.URLInput(attrs={'class': 'form-control shadow-sm', 'placeholder': 'Facebook profile URL'}),
            'twitter': forms.URLInput(attrs={'class': 'form-control shadow-sm', 'placeholder': 'Twitter profile URL'}),
            'linkedin': forms.URLInput(attrs={'class': 'form-control shadow-sm', 'placeholder': 'LinkedIn profile URL'}),
        }

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data.get('first_name')
        user.last_name = self.cleaned_data.get('last_name')
        if commit:
            user.save()
            profile.save()
        return profile

class LoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter password'}))

class BlogPostForm(forms.ModelForm):
    class Meta:
        model = BlogPost
        fields = ['title', 'content', 'image', 'video']

        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter post title'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Write your post here...'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'video': forms.FileInput(attrs={'class': 'form-control'}),
        }

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Write a comment...'}),
        }
