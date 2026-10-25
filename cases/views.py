import os
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.db import transaction
from django.http import FileResponse, Http404

from .models import Case, CaseStatus, CaseType, Attachment, AttachmentType, CaseComment, CommentType
from .forms import CaseSubmissionForm, CaseReviewAssignmentForm, CaseProgressUpdateForm, ReporterReplyForm
from .validators import ALLOWED_VIDEO_EXTS
from .permissions import can_view_case
from audit.utils import log_audit
from notifications.utils import create_notification
from accounts.models import User, UserRole


def landing_view(request):
    return render(request, 'landing.html')


@login_required
def home_view(request):
    """
    Renders Wireframe 2: Student / Lecturer Home Screen.
    Displays summary indicators (Submitted, In Progress, Solved),
    and filters cases dynamically when clicking on any status card.
    """
    user = request.user

    # The home summary is only for reporting users. Operational staff have a
    # dedicated role dashboard, avoiding duplicate and confusing dashboards.
    if user.is_administrator:
        return redirect('admin_dashboard')
    if user.is_system_administrator:
        return redirect('system_dashboard')
    if user.is_authority_user:
        return redirect('authority_dashboard')
    if user.role == UserRole.FACULTY_MANAGEMENT:
        return redirect('management_dashboard')

    # Base queryset according to role
    base_cases = Case.objects.filter(submitted_by=user)

    submitted_count = base_cases.filter(status=CaseStatus.SUBMITTED).count()
    in_progress_count = base_cases.filter(
        status__in=[CaseStatus.IN_PROGRESS, CaseStatus.ASSIGNED, CaseStatus.UNDER_REVIEW, CaseStatus.NOT_STARTED, CaseStatus.REOPENED, CaseStatus.WAITING_FOR_INFO]
    ).count()
    solved_count = base_cases.filter(status__in=[CaseStatus.SOLVED, CaseStatus.CLOSED]).count()
    total_count = base_cases.count()

    # Dynamic filter via clicking the analytic cards
    status_filter = request.GET.get('status', 'all').strip().lower()

    if status_filter == 'submitted':
        filtered_cases = base_cases.filter(status=CaseStatus.SUBMITTED)
        filter_label = "Submitted Cases"
    elif status_filter == 'in_progress':
        filtered_cases = base_cases.filter(
            status__in=[CaseStatus.IN_PROGRESS, CaseStatus.ASSIGNED, CaseStatus.UNDER_REVIEW, CaseStatus.NOT_STARTED, CaseStatus.REOPENED, CaseStatus.WAITING_FOR_INFO]
        )
        filter_label = "In Progress Cases"
    elif status_filter == 'solved':
        filtered_cases = base_cases.filter(status__in=[CaseStatus.SOLVED, CaseStatus.CLOSED])
        filter_label = "Solved Cases"
    else:
        filtered_cases = base_cases
        status_filter = 'all'
        filter_label = "All Recent Cases"

    recent_cases = filtered_cases.order_by('-submitted_at')[:25]

    context = {
        'submitted_count': submitted_count,
        'in_progress_count': in_progress_count,
        'solved_count': solved_count,
        'total_count': total_count,
        'recent_cases': recent_cases,
        'current_filter': status_filter,
        'filter_label': filter_label,
    }
    return render(request, 'cases/home.html', context)


@login_required
@transaction.atomic
def submit_case_view(request):
    """
    Renders Wireframe 3: New Case Submission Form.
    Accepts complaints or suggestions with evidence uploads and declaration.
    """
    if not request.user.is_reporting_user:
        raise PermissionDenied("Only students and lecturers can submit cases.")

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
            coordinators = User.objects.filter(role=UserRole.ADMINISTRATOR)
            for admin_user in coordinators:
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
    if not request.user.is_reporting_user:
        raise PermissionDenied("Only students and lecturers can access submitted cases.")

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
    can_view = can_view_case(user, case)
    if not can_view:
        raise PermissionDenied("You do not have permission to view this case.")

    is_reporting_user = user == case.submitted_by and user.is_reporting_user
    comments = case.comments.all()
    if is_reporting_user:
        # Internal staff notes are not part of the reporter-facing conversation.
        comments = comments.exclude(comment_type=CommentType.INTERNAL)

    return render(request, 'cases/case_detail.html', {
        'case': case,
        'comments': comments,
        'reply_form': ReporterReplyForm() if is_reporting_user else None,
        'can_reply': is_reporting_user and case.is_open,
        'show_internal': not is_reporting_user,
    })


@login_required
@transaction.atomic
def admin_review_case_view(request, pk):
    """
    Renders Wireframe 5: Admin Case Review and Assignment.
    Allows administrators to assign authority, change priority/category, or reject case.
    """
    if not request.user.is_administrator:
        raise PermissionDenied("Only administrators can review and assign cases.")

    case = get_object_or_404(Case, pk=pk)
    if case.status in [CaseStatus.SOLVED, CaseStatus.CLOSED, CaseStatus.REJECTED]:
        raise PermissionDenied('Reopen a resolved case before reviewing it again.')
    old_status = case.status
    old_authority = case.assigned_authority
    old_category = case.category.name
    old_priority = case.priority

    if request.method == 'POST':
        form = CaseReviewAssignmentForm(request.POST, instance=case)
        if form.is_valid():
            updated_case = form.save(commit=False)

            updated_case.reviewed_at = updated_case.reviewed_at or timezone.now()
            if old_authority != updated_case.assigned_authority:
                updated_case.assigned_at = timezone.now() if updated_case.assigned_authority else None
                updated_case.action_started_at = None
            # reviewed_at is already initialized above; fill an unset assignment date.
            if updated_case.status in [CaseStatus.ASSIGNED, CaseStatus.NOT_STARTED] and not updated_case.assigned_at:
                updated_case.assigned_at = timezone.now()

            updated_case.save()

            # Audit log
            log_audit(
                case=updated_case,
                user=request.user,
                action_type=f"Admin Review: {updated_case.get_status_display()}",
                old_value=f"Status: {old_status}, Authority: {old_authority.name if old_authority else 'None'}, Category: {old_category}, Priority: {old_priority}",
                new_value=f"Status: {updated_case.status}, Authority: {updated_case.assigned_authority.name if updated_case.assigned_authority else 'None'}, Category: {updated_case.category.name}, Priority: {updated_case.priority}",
                notes=updated_case.admin_notes,
                request=request
            )

            # Notifications
            if updated_case.assigned_authority and updated_case.status in [CaseStatus.ASSIGNED, CaseStatus.NOT_STARTED]:
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

            if updated_case.status != CaseStatus.REJECTED:
                create_notification(updated_case.submitted_by, f'Case update: {updated_case.case_number}',
                                    f'Your case is {updated_case.get_status_display().lower()}.', case=updated_case)
            messages.success(request, f"Case {updated_case.case_number} reviewed and updated successfully.")
            return redirect('admin_dashboard')
    else:
        form = CaseReviewAssignmentForm(instance=case)

    return render(request, 'cases/admin_review.html', {'form': form, 'case': case})


@login_required
@transaction.atomic
def authority_update_case_view(request, pk):
    """
    Renders Wireframe 7: Case Progress Update and Closure.
    Used by assigned authorities to log progress, upload completion proof,
    and mark as solved (Acceptance Criteria 16, 17, 18).
    """
    case = get_object_or_404(Case, pk=pk)

    # Progress updates are performed by staff in the assigned authority.
    is_authorized_staff = request.user.is_authority_user and (request.user.assigned_authority_id is not None and request.user.assigned_authority_id == case.assigned_authority_id)
    if not is_authorized_staff:
        raise PermissionDenied("Only the assigned authority can update case progress.")

    if case.status not in [CaseStatus.ASSIGNED, CaseStatus.NOT_STARTED, CaseStatus.IN_PROGRESS, CaseStatus.WAITING_FOR_INFO]:
        raise PermissionDenied('This case is not available for authority progress updates.')
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
                    comment_type=CommentType.INFO_REQUEST if updated_case.status == CaseStatus.WAITING_FOR_INFO else CommentType.PROGRESS_UPDATE,
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
            if updated_case.status in [CaseStatus.IN_PROGRESS, CaseStatus.WAITING_FOR_INFO, CaseStatus.SOLVED] and not updated_case.action_started_at:
                updated_case.action_started_at = timezone.now()
            if updated_case.status == CaseStatus.SOLVED and not updated_case.solved_at:
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

            if updated_case.status != CaseStatus.SOLVED:
                create_notification(updated_case.submitted_by, f'Case update: {updated_case.case_number}',
                                    f'{updated_case.get_status_display()}: {progress_comment_text or updated_case.resolution_notes}', case=updated_case)

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
            return redirect('authority_dashboard')
    else:
        form = CaseProgressUpdateForm(instance=case)

    return render(request, 'cases/authority_update.html', {'form': form, 'case': case})


@login_required
@transaction.atomic
def admin_close_case_view(request, pk):
    """Closes case after confirming completion (Lifecycle Step 8)"""
    if not request.user.is_administrator:
        raise PermissionDenied("Only administrators can close cases.")
    if request.method != 'POST':
        raise PermissionDenied("Closing a case requires confirmation.")

    case = get_object_or_404(Case, pk=pk)
    if case.status != CaseStatus.SOLVED:
        raise PermissionDenied("Only solved cases can be closed.")
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
@transaction.atomic
def reopen_case_view(request, pk):
    """Reopens case if resolution is not satisfactory (Lifecycle Step 10)"""
    case = get_object_or_404(Case, pk=pk)
    if not (request.user == case.submitted_by or request.user.is_administrator):
        raise PermissionDenied("Only the case author or an admin can reopen this case.")
    if request.method != 'POST':
        raise PermissionDenied("Reopening a case requires confirmation.")

    if case.status not in [CaseStatus.SOLVED, CaseStatus.CLOSED]:
        raise PermissionDenied('Only solved or closed cases can be reopened.')
    old_status = case.status
    case.solved_at = None
    case.closed_at = None
    case.action_started_at = None
    case.resolution_notes = ''
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

    for coordinator in User.objects.filter(role=UserRole.ADMINISTRATOR, is_active=True):
        create_notification(coordinator, f'Case reopened: {case.case_number}',
                            'The resolution requires further review.', case=case)
    messages.warning(request, f"Case {case.case_number} has been reopened.")
    return redirect('case_detail', pk=case.pk)


@login_required
@transaction.atomic
def add_comment_view(request, pk):
    """Allow the reporting user to send a clarification reply on their own case."""
    case = get_object_or_404(Case, pk=pk)
    if request.user != case.submitted_by or not request.user.is_reporting_user:
        raise PermissionDenied("Only the reporting user can reply through this form.")
    if not case.is_open:
        raise PermissionDenied('Replies are available only on active cases.')
    if request.method == 'POST':
        form = ReporterReplyForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.case = case
            comment.author = request.user
            comment.comment_type = CommentType.REPORTER_REPLY
            comment.save()

            log_audit(
                case=case,
                user=request.user,
                action_type="Comment Added",
                notes=comment.comment_text[:100],
                request=request
            )
            recipients = User.objects.filter(Q(role=UserRole.ADMINISTRATOR) | Q(role=UserRole.AUTHORITY, assigned_authority_id=case.assigned_authority_id), is_active=True)
            if not case.assigned_authority_id:
                recipients = recipients.filter(role=UserRole.ADMINISTRATOR)
            for recipient in recipients:
                create_notification(recipient, f'Reporter reply: {case.case_number}', comment.comment_text, case=case)
            messages.success(request, "Comment added successfully.")
        else:
            messages.error(request, "Enter a reply before sending.")
    return redirect('case_detail', pk=case.pk)


@login_required
def attachment_view(request, pk):
    attachment = get_object_or_404(Attachment.objects.select_related('case'), pk=pk)
    if not can_view_case(request.user, attachment.case):
        raise PermissionDenied('You do not have permission to access this evidence.')
    try:
        response = FileResponse(attachment.file.open('rb'), filename=attachment.file_name)
    except FileNotFoundError:
        raise Http404('This evidence file is unavailable.')
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    return response
