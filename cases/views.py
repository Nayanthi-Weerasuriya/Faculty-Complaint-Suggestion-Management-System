import os
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from django.db.models import Q

from .models import Case, CaseStatus, CaseType, CasePriority, Attachment, AttachmentType, CaseComment
from .forms import CaseSubmissionForm, CaseReviewAssignmentForm, CaseProgressUpdateForm, CaseCommentForm, ALLOWED_VIDEO_EXTS
from audit.utils import log_audit
from notifications.utils import create_notification
from accounts.models import User, UserRole


@login_required
def home_view(request):
    """
    Renders Wireframe 2: Student / Lecturer Home Screen.
    Displays summary indicators (Submitted, In Progress, Solved),
    quick actions, and recent cases.
    """
    user = request.user
    
    # If Admin or Authority or Management, provide quick routing or full view
    if user.is_admin_user:
        user_cases = Case.objects.all()
    elif user.is_authority_user and user.assigned_authority:
        user_cases = Case.objects.filter(assigned_authority=user.assigned_authority)
    else:
        user_cases = Case.objects.filter(submitted_by=user)

    submitted_count = user_cases.filter(status=CaseStatus.SUBMITTED).count()
    in_progress_count = user_cases.filter(status__in=[CaseStatus.IN_PROGRESS, CaseStatus.ASSIGNED, CaseStatus.UNDER_REVIEW]).count()
    solved_count = user_cases.filter(status__in=[CaseStatus.SOLVED, CaseStatus.CLOSED]).count()

    recent_cases = user_cases.order_by('-submitted_at')[:8]

    context = {
        'submitted_count': submitted_count,
        'in_progress_count': in_progress_count,
        'solved_count': solved_count,
        'recent_cases': recent_cases,
    }
    return render(request, 'cases/home.html', context)


@login_required
def submit_case_view(request):
    """
    Renders Wireframe 3: New Case Submission Form.
    Accepts complaints or suggestions with evidence uploads and declaration.
    """
    if request.method == 'POST':
        form = CaseSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            case = form.save(commit=False)
            case.submitted_by = request.user
            case.status = CaseStatus.SUBMITTED
            case.save()

            # Handle optional evidence attachment
            uploaded_file = form.cleaned_data.get('attachment_file')
            if uploaded_file:
                ext = os.path.splitext(uploaded_file.name)[1].lower()
                file_type = AttachmentType.VIDEO if ext in ALLOWED_VIDEO_EXTS else AttachmentType.IMAGE
                Attachment.objects.create(
                    case=case,
                    file=uploaded_file,
                    file_type=file_type,
                    uploaded_by=request.user
                )

            # Record in Audit Log
            log_audit(
                case=case,
                user=request.user,
                action_type="Case Submitted",
                new_value=f"Type: {case.get_case_type_display()}, Priority: {case.get_priority_display()}",
                notes="Initial case submission by user",
                request=request
            )

            # Notify administrators
            admins = User.objects.filter(role__in=[UserRole.ADMINISTRATOR, UserRole.SYSTEM_ADMIN])
            for admin_user in admins:
                create_notification(
                    recipient=admin_user,
                    case=case,
                    title=f"New {case.get_case_type_display()} Submitted ({case.case_number})",
                    message=f"Case '{case.title}' submitted by {request.user.get_full_name() or request.user.username}.",
                    notification_type='new_case'
                )

            messages.success(request, f"Your case has been successfully submitted! Reference No: {case.case_number}")
            return redirect('case_detail', pk=case.pk)
    else:
        form = CaseSubmissionForm()

    return render(request, 'cases/submit_case.html', {'form': form})


@login_required
def my_cases_view(request):
    """List of all cases submitted by current user with filtering"""
    cases_qs = Case.objects.filter(submitted_by=request.user)

    q = request.GET.get('q')
    status_filter = request.GET.get('status')
    type_filter = request.GET.get('type')

    if q:
        cases_qs = cases_qs.filter(Q(case_number__icontains=q) | Q(title__icontains=q) | Q(description__icontains=q))
    if status_filter:
        cases_qs = cases_qs.filter(status=status_filter)
    if type_filter:
        cases_qs = cases_qs.filter(case_type=type_filter)

    return render(request, 'cases/my_cases.html', {
        'cases': cases_qs.order_by('-submitted_at'),
        'status_choices': CaseStatus.choices,
        'type_choices': CaseType.choices,
        'selected_status': status_filter,
        'selected_type': type_filter,
        'search_query': q,
    })


@login_required
def case_detail_view(request, pk):
    """
    Detailed view showing case lifecycle status, attachments,
    progress timeline, and audit logs.
    """
    case = get_object_or_404(Case, pk=pk)

    # Permission check: reporting user, admin, assigned authority staff, or management
    user = request.user
    can_view = (
        user == case.submitted_by or
        user.is_admin_user or
        user.is_management_user or
        (user.is_authority_user and user.assigned_authority == case.assigned_authority)
    )
    if not can_view:
        raise PermissionDenied("You do not have permission to view this case.")

    comment_form = CaseCommentForm()
    return render(request, 'cases/case_detail.html', {
        'case': case,
        'comment_form': comment_form,
    })


@login_required
def admin_review_case_view(request, pk):
    """
    Renders Wireframe 5: Admin Case Review and Assignment.
    Allows administrators to assign authority, change priority/category, or reject case.
    """
    if not request.user.is_admin_user:
        raise PermissionDenied("Only administrators can review and assign cases.")

    case = get_object_or_404(Case, pk=pk)
    old_status = case.status
    old_authority = case.assigned_authority

    if request.method == 'POST':
        form = CaseReviewAssignmentForm(request.POST, instance=case)
        if form.is_valid():
            updated_case = form.save(commit=False)
            
            # Timestamp bookkeeping
            if updated_case.status == CaseStatus.UNDER_REVIEW and not updated_case.reviewed_at:
                updated_case.reviewed_at = timezone.now()
            elif updated_case.status == CaseStatus.ASSIGNED and not updated_case.assigned_at:
                updated_case.assigned_at = timezone.now()

            updated_case.save()

            # Audit log
            log_audit(
                case=updated_case,
                user=request.user,
                action_type=f"Admin Review: {updated_case.get_status_display()}",
                old_value=f"Status: {old_status}, Authority: {old_authority.name if old_authority else 'None'}",
                new_value=f"Status: {updated_case.status}, Authority: {updated_case.assigned_authority.name if updated_case.assigned_authority else 'None'}",
                notes=updated_case.admin_notes,
                request=request
            )

            # Notifications
            if updated_case.assigned_authority and updated_case.status == CaseStatus.ASSIGNED:
                # Notify authority officers
                authority_officers = User.objects.filter(assigned_authority=updated_case.assigned_authority)
                for officer in authority_officers:
                    create_notification(
                        recipient=officer,
                        case=updated_case,
                        title=f"New Case Assigned: {updated_case.case_number}",
                        message=f"Case '{updated_case.title}' assigned to {updated_case.assigned_authority.name}. Priority: {updated_case.get_priority_display()}.",
                        notification_type='assigned'
                    )

            if updated_case.status == CaseStatus.REJECTED:
                create_notification(
                    recipient=updated_case.submitted_by,
                    case=updated_case,
                    title=f"Case {updated_case.case_number} Rejected",
                    message=f"Your case '{updated_case.title}' was rejected by the administrator. Reason: {updated_case.admin_notes}",
                    notification_type='status_update'
                )

            messages.success(request, f"Case {updated_case.case_number} updated successfully.")
            return redirect('case_detail', pk=updated_case.pk)
    else:
        form = CaseReviewAssignmentForm(instance=case)

    return render(request, 'cases/admin_review.html', {'form': form, 'case': case})


@login_required
def authority_update_case_view(request, pk):
    """
    Renders Wireframe 7: Case Progress Update and Closure.
    Used by assigned authorities to log progress, upload completion proof,
    and mark as solved (Acceptance Criteria 16, 17, 18).
    """
    case = get_object_or_404(Case, pk=pk)

    # Permission check: must be staff of assigned authority or admin
    is_authorized_staff = request.user.is_authority_user and (request.user.assigned_authority == case.assigned_authority)
    if not (is_authorized_staff or request.user.is_admin_user):
        raise PermissionDenied("Only the assigned authority or administrator can update case progress.")

    old_status = case.status

    if request.method == 'POST':
        form = CaseProgressUpdateForm(request.POST, request.FILES, instance=case)
        if form.is_valid():
            updated_case = form.save(commit=False)

            progress_comment_text = form.cleaned_data.get('progress_comment')
            if progress_comment_text:
                CaseComment.objects.create(
                    case=updated_case,
                    author=request.user,
                    comment_type='progress',
                    comment_text=progress_comment_text
                )

            # Upload completion evidence if provided
            evidence_file = form.cleaned_data.get('completion_evidence')
            if evidence_file:
                ext = os.path.splitext(evidence_file.name)[1].lower()
                file_type = AttachmentType.VIDEO if ext in ALLOWED_VIDEO_EXTS else AttachmentType.IMAGE
                Attachment.objects.create(
                    case=updated_case,
                    file=evidence_file,
                    file_type=file_type,
                    uploaded_by=request.user,
                    is_completion_evidence=True
                )

            # Bookkeeping timestamps
            if updated_case.status == CaseStatus.IN_PROGRESS and not updated_case.action_started_at:
                updated_case.action_started_at = timezone.now()
            elif updated_case.status == CaseStatus.SOLVED and not updated_case.solved_at:
                updated_case.solved_at = timezone.now()

            updated_case.save()

            # Audit Log
            log_audit(
                case=updated_case,
                user=request.user,
                action_type=f"Authority Progress Update: {updated_case.get_status_display()}",
                old_value=old_status,
                new_value=updated_case.status,
                notes=f"Progress: {progress_comment_text or 'Status update'}. Resolution: {updated_case.resolution_notes}",
                request=request
            )

            # Acceptance Criterion 18: The informed user receives a message when the case is solved!
            if updated_case.status == CaseStatus.SOLVED:
                create_notification(
                    recipient=updated_case.submitted_by,
                    case=updated_case,
                    title=f"Case Solved: {updated_case.case_number}",
                    message=f"Your case '{updated_case.title}' has been solved by {updated_case.assigned_authority.name if updated_case.assigned_authority else 'the assigned team'}. Resolution note: {updated_case.resolution_notes}",
                    notification_type='solved'
                )

            messages.success(request, f"Case {updated_case.case_number} progress updated successfully.")
            return redirect('case_detail', pk=updated_case.pk)
    else:
        form = CaseProgressUpdateForm(instance=case)

    return render(request, 'cases/authority_update.html', {'form': form, 'case': case})


@login_required
def admin_close_case_view(request, pk):
    """Closes case after confirming completion (Lifecycle Step 8)"""
    if not request.user.is_admin_user:
        raise PermissionDenied("Only administrators can close cases.")

    case = get_object_or_404(Case, pk=pk)
    old_status = case.status
    case.status = CaseStatus.CLOSED
    case.closed_at = timezone.now()
    case.save()

    log_audit(
        case=case,
        user=request.user,
        action_type="Case Closed",
        old_value=old_status,
        new_value=CaseStatus.CLOSED,
        notes="Administrator confirmed completion and closed the case.",
        request=request
    )

    create_notification(
        recipient=case.submitted_by,
        case=case,
        title=f"Case Closed: {case.case_number}",
        message=f"Your case '{case.title}' has been officially verified and closed.",
        notification_type='closed'
    )

    messages.success(request, f"Case {case.case_number} has been closed.")
    return redirect('case_detail', pk=case.pk)


@login_required
def reopen_case_view(request, pk):
    """Reopens case if resolution is not satisfactory (Lifecycle Step 10)"""
    case = get_object_or_404(Case, pk=pk)
    if not (request.user == case.submitted_by or request.user.is_admin_user):
        raise PermissionDenied("Only the case author or an admin can reopen this case.")

    old_status = case.status
    case.status = CaseStatus.REOPENED
    case.save()

    log_audit(
        case=case,
        user=request.user,
        action_type="Case Reopened",
        old_value=old_status,
        new_value=CaseStatus.REOPENED,
        notes="Resolution was not satisfactory; case reopened for further review.",
        request=request
    )

    messages.warning(request, f"Case {case.case_number} has been reopened.")
    return redirect('case_detail', pk=case.pk)


@login_required
def add_comment_view(request, pk):
    """Add comment or inquiry to case"""
    case = get_object_or_404(Case, pk=pk)
    if request.method == 'POST':
        form = CaseCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.case = case
            comment.author = request.user
            comment.save()

            log_audit(
                case=case,
                user=request.user,
                action_type="Comment Added",
                notes=comment.comment_text[:100],
                request=request
            )
            messages.success(request, "Comment added successfully.")
    return redirect('case_detail', pk=case.pk)
