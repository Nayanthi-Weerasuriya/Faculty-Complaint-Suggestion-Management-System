from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import User, UserRole


class FacultyLoginForm(AuthenticationForm):
    """
    Login form matching Wireframe 1:
    Email / Registration Number / Employee Email and Password
    """
    username = forms.CharField(
        label="Email / Registration Number / Staff ID",
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'e.g. reg_no, email, or username',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter your password'
        })
    )


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'reg_or_staff_id', 'department_or_unit', 'contact_number']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'reg_or_staff_id': forms.TextInput(attrs={'class': 'form-control'}),
            'department_or_unit': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
        }
