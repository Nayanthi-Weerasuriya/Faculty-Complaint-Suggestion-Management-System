from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import FacultyLoginForm, UserProfileForm


class FacultyLoginView(LoginView):
    """
    Renders Wireframe 1: Login Screen
    """
    template_name = 'accounts/login.html'
    authentication_form = FacultyLoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        if user.is_admin_user:
            return '/dashboard/admin/'
        elif user.is_authority_user:
            return '/dashboard/authority/'
        elif user.is_management_user:
            return '/dashboard/management/'
        return '/'


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
