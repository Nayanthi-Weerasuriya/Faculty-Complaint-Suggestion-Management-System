from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from authorities.models import Authority
from .forms import FacultyLoginForm, UserProfileForm, PublicRegistrationForm, VerificationResendForm
from .models import User
from .verification import send_verification, verification_user, local_verification_preview
from django.views.decorators.cache import never_cache
from django.db import transaction, IntegrityError
from django.utils import timezone
from django.views.decorators.http import require_http_methods


class FacultyLoginView(LoginView):
    """
    Renders Wireframe 1: Login Screen
    """
    template_name = 'accounts/login.html'
    authentication_form = FacultyLoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        self.request.session.set_expiry(1209600 if self.request.POST.get('remember_me') else 0)
        return super().form_valid(form)

    def get_success_url(self):
        user = self.request.user
        if user.is_system_administrator:
            return '/dashboard/system/'
        elif user.is_administrator:
            return '/dashboard/admin/'
        elif user.is_authority_user:
            return '/dashboard/authority/'
        elif user.is_management_user:
            return '/dashboard/management/'
        return '/home/'


class ComplaintHandlerLoginView(LoginView):
    """Single Authority Portal entry point for operational handler units."""
    template_name = 'accounts/complaint_handler_login.html'
    authentication_form = FacultyLoginForm
    redirect_authenticated_user = True

    @property
    def handler_units(self):
        aliases = {'Maintenance Division': 'maintenance', 'IT Unit': 'it', 'Examination Unit': 'examination'}
        return {aliases.get(unit.name, str(unit.pk)): unit.name for unit in Authority.objects.filter(is_active=True)}

    def get_selected_unit(self):
        return self.request.GET.get('unit') or self.request.POST.get('unit')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_unit = self.get_selected_unit()
        context['handler_units'] = self.handler_units
        context['selected_unit'] = selected_unit
        context['selected_unit_name'] = self.handler_units.get(selected_unit)
        return context

    def form_valid(self, form):
        user = form.get_user()
        selected_unit = self.get_selected_unit()
        expected_authority = self.handler_units.get(selected_unit)
        if not expected_authority or not user.is_authority_user or not user.assigned_authority or user.assigned_authority.name != expected_authority:
            form.add_error(None, "Use the credentials assigned to the selected complaint-handling unit.")
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        return '/dashboard/authority/'


class FacultyLogoutView(LogoutView):
    next_page = 'login'


@login_required
def profile_view(request):
    """User profile management view"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile details have been successfully updated.")
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user)

    return render(request, 'accounts/profile.html', {'form': form})


@require_http_methods(['GET', 'POST'])
def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = PublicRegistrationForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        last_attempt = request.session.get('registration_sent_at', 0)
        if timezone.now().timestamp() - last_attempt < 60:
            form.add_error(None, 'Please wait a minute before registering another account.')
        else:
            try:
                with transaction.atomic():
                    user = form.save()
            except IntegrityError:
                form.add_error(None, 'An account already uses these details. Sign in or recover your existing account.')
            else:
                request.session['registration_sent_at'] = timezone.now().timestamp()
                request.session['registered_user_id'] = user.pk
                if not send_verification(request, user):
                    messages.warning(request, 'Your account was saved, but we could not send the verification email. Please try resending it or contact faculty support.')
                return redirect('registration_done')
    return render(request, 'accounts/register.html', {'form': form})


@never_cache
def registration_done_view(request):
    response = render(request, 'accounts/registration_done.html', {
        'local_verification_url': local_verification_preview(request),
    })
    response['Referrer-Policy'] = 'no-referrer'
    return response


@never_cache
@require_http_methods(['GET', 'POST'])
def verify_email_view(request, token):
    if request.method == 'POST':
        with transaction.atomic():
            user = verification_user(token, lock=True)
            if user:
                user.registration_pending = False
                user.email_verified_at = timezone.now()
                user.is_active = True
                user.save(update_fields=['registration_pending', 'email_verified_at', 'is_active'])
                if request.session.get('registered_user_id') == user.pk:
                    request.session.pop('registered_user_id', None)
                messages.success(request, 'Your university email is verified. You can now sign in.')
                return redirect('login')
    else:
        user = verification_user(token)
    return render(request, 'accounts/verify_email.html', {'valid_link': user is not None})


@require_http_methods(['GET', 'POST'])
def resend_verification_view(request):
    form = VerificationResendForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        now = timezone.now()
        last_attempt = request.session.get('verification_resend_at', 0)
        if now.timestamp() - last_attempt < 60:
            form.add_error(None, 'Please wait a minute before requesting another email.')
        else:
            request.session['verification_resend_at'] = now.timestamp()
            user = User.objects.filter(email__iexact=form.cleaned_data['email'], registration_pending=True, is_active=False).first()
            if user and (not user.verification_sent_at or (now - user.verification_sent_at).total_seconds() >= 60):
                send_verification(request, user)
            messages.info(request, 'If an account is waiting for verification, a link will be sent. Check your inbox and spam folder; allow a minute between requests.')
            return redirect('registration_done')
    return render(request, 'accounts/resend_verification.html', {'form': form})
