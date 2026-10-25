from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from .models import Authority
from .forms import AuthorityForm


@login_required
def authority_list_view(request):
    """View and manage authorities (Acceptance Criterion 15)"""
    if not request.user.is_admin_user:
        raise PermissionDenied("Only administrators can manage the authority list.")

    authorities = Authority.objects.all().order_by('name')
    return render(request, 'authorities/authority_list.html', {'authorities': authorities})


@login_required
def authority_create_view(request):
    if not request.user.is_admin_user:
        raise PermissionDenied("Only administrators can add authorities.")

    if request.method == 'POST':
        form = AuthorityForm(request.POST)
        if form.is_valid():
            authority = form.save()
            messages.success(request, f"Authority '{authority.name}' added successfully.")
            return redirect('authority_list')
    else:
        form = AuthorityForm()

    return render(request, 'authorities/authority_form.html', {'form': form, 'title': 'Add New Authority'})


@login_required
def authority_update_view(request, pk):
    if not request.user.is_admin_user:
        raise PermissionDenied("Only administrators can edit authorities.")

    authority = get_object_or_404(Authority, pk=pk)
    if request.method == 'POST':
        form = AuthorityForm(request.POST, instance=authority)
        if form.is_valid():
            form.save()
            messages.success(request, f"Authority '{authority.name}' updated successfully.")
            return redirect('authority_list')
    else:
        form = AuthorityForm(instance=authority)

    return render(request, 'authorities/authority_form.html', {'form': form, 'title': f'Edit Authority: {authority.name}'})


@login_required
def authority_toggle_active_view(request, pk):
    if not request.user.is_admin_user:
        raise PermissionDenied("Only administrators can deactivate authorities.")

    authority = get_object_or_404(Authority, pk=pk)
    authority.is_active = not authority.is_active
    authority.save()
    status_str = "activated" if authority.is_active else "deactivated"
    messages.info(request, f"Authority '{authority.name}' has been {status_str}.")
    return redirect('authority_list')
