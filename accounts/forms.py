from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.conf import settings
from django.db.models import Q
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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.email_verified_at or self.instance.registration_pending:
            self.fields['email'].disabled = True
            self.fields['email'].help_text = 'Contact the System Administrator if your verified university email needs to change.'

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


class PublicRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField(label='University email')
    reg_or_staff_id = forms.CharField(max_length=50, label='Registration number / Staff ID')
    department_or_unit = forms.CharField(max_length=150, label='Department')
    role = forms.ChoiceField(label='I am a', choices=[(UserRole.STUDENT, 'Student'), (UserRole.LECTURER, 'Lecturer')])

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'reg_or_staff_id', 'role', 'department_or_unit']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
        self.fields['username'].widget.attrs.pop('autofocus', None)
        self.fields['username'].widget.attrs['autocomplete'] = 'username'
        self.fields['username'].help_text = 'Choose a username, or use your university email as your username.'
        self.fields['first_name'].widget.attrs['autofocus'] = True
        self.fields['email'].widget.attrs['autocomplete'] = 'email'
        self.fields['password1'].widget.attrs['autocomplete'] = 'new-password'
        self.fields['password2'].widget.attrs['autocomplete'] = 'new-password'
        self.fields['email'].help_text = 'Use your university email. We will send a verification link before you can sign in.'

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        domain = email.rsplit('@', 1)[-1]
        if not any(domain == allowed or domain.endswith('.' + allowed) for allowed in settings.UNIVERSITY_EMAIL_DOMAINS):
            raise forms.ValidationError('Use an email address issued by the university.')
        return email

    def clean(self):
        cleaned = super().clean()
        for field in ['username', 'email', 'reg_or_staff_id']:
            value = cleaned.get(field)
            if not value:
                continue
            if User.objects.filter(Q(username__iexact=value) | Q(email__iexact=value) | Q(reg_or_staff_id__iexact=value)).exists():
                self.add_error(field, 'This value is already associated with an account. Sign in or recover your existing account.')
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = self.cleaned_data['role']
        user.is_active = False
        user.is_staff = False
        user.is_superuser = False
        user.assigned_authority = None
        user.registration_pending = True
        if commit:
            user.save()
        return user


class VerificationResendForm(forms.Form):
    email = forms.EmailField(label='University email', widget=forms.EmailInput(attrs={'class': 'form-control', 'autocomplete': 'email'}))
