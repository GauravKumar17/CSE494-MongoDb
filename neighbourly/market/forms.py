from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from market.data import CATEGORIES
CHOICES = [(x['slug'], x['name']) for x in CATEGORIES]
class SignupForm(forms.Form):
    name = forms.CharField(max_length=80, label='Full name')
    email = forms.EmailField(max_length=180)
    password = forms.CharField(widget=forms.PasswordInput, min_length=10, help_text='Use at least 10 characters.')
    confirm_password = forms.CharField(widget=forms.PasswordInput, label='Confirm password')
    role = forms.ChoiceField(choices=[('customer', 'I need a service'), ('worker', 'I provide services')], label='I am here because')
    def clean_password(self):
        v = self.cleaned_data['password']; validate_password(v); return v
    def clean(self):
        v=super().clean()
        if v.get('password') != v.get('confirm_password'): self.add_error('confirm_password', 'Passwords do not match.')
        return v
class LoginForm(forms.Form):
    email = forms.EmailField(max_length=180)
    password = forms.CharField(widget=forms.PasswordInput)
class ProfileForm(forms.Form):
    category = forms.ChoiceField(choices=CHOICES)
    locality = forms.CharField(max_length=70, label='Service locality')
    bio = forms.CharField(max_length=600, min_length=30, widget=forms.Textarea(attrs={'rows': 4}), label='About your work')
    experience = forms.IntegerField(min_value=0, max_value=60, label='Years of experience')
    rate = forms.IntegerField(min_value=100, max_value=20000, label='Fixed one hour visit price in rupees')
    skills = forms.CharField(max_length=200, help_text='Separate your services with commas.')
    available = forms.BooleanField(required=False, label='I am available for new bookings')
class BookingForm(forms.Form):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    hour = forms.ChoiceField(choices=[(str(x), f'{x:02d}:00 – {x+1:02d}:00') for x in range(9,18)], label='One hour visit slot')
    address = forms.CharField(max_length=300, widget=forms.Textarea(attrs={'rows': 2}), label='Service address')
    description = forms.CharField(min_length=10, max_length=800, widget=forms.Textarea(attrs={'rows': 3}), label='What needs a little care?')
    community = forms.BooleanField(required=False, label='This is for a shared community space')
    def clean_date(self):
        from django.utils import timezone
        from datetime import timedelta
        v=self.cleaned_data['date']; today=timezone.localdate()
        if not today < v <= today + timedelta(days=60): raise ValidationError('Choose a date from tomorrow to 60 days ahead.')
        return v
class ReviewForm(forms.Form):
    rating = forms.ChoiceField(choices=[(str(x), f'{x} / 5') for x in range(5,0,-1)])
    comment = forms.CharField(min_length=10, max_length=500, widget=forms.Textarea(attrs={'rows': 3}))
