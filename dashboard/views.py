from datetime import timedelta
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.db.models import Count, Avg, Q, F

from cases.models import Case, CaseStatus, CasePriority, CaseType
from categories.models import Category
from authorities.models import Authority


@login_required
def admin_dashboard_view(request):
    """
    Renders Wireframe 4: Admin Dashboard.
    Provides operational metrics, multi-faceted filtering,
    and the Not Started Age Report table.
    """
    if not (request.user.is_admin_user or request.user.is_management_user):
        raise PermissionDenied("Access restricted to administrators and management.")

    cases = Case.objects.all()

    # Filters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    category_id = request.GET.get('category')
    authority_id = request.GET.get('authority')
    priority = request.GET.get('priority')
    status = request.GET.get('status')

    if date_from:
        cases = cases.filter(submitted_at__date__gte=date_from)
    if date_to:
        cases = cases.filter(submitted_at__date__lte=date_to)
    if category_id:
        cases = cases.filter(category_id=category_id)
    if authority_id:
        cases = cases.filter(assigned_authority_id=authority_id)
    if priority:
        cases = cases.filter(priority=priority)
    if status == 'attempted':
        cases = cases.filter(status__in=[
            CaseStatus.UNDER_REVIEW, CaseStatus.NOT_STARTED, CaseStatus.ASSIGNED,
            CaseStatus.IN_PROGRESS, CaseStatus.WAITING_FOR_INFO, CaseStatus.SOLVED,
            CaseStatus.CLOSED, CaseStatus.REOPENED
        ])
    elif status == 'not_started':
        cases = cases.filter(status__in=[
            CaseStatus.UNDER_REVIEW, CaseStatus.NOT_STARTED, CaseStatus.ASSIGNED
        ])
    elif status:
        cases = cases.filter(status=status)

    total_cases = cases.count()
    attempted_cases = cases.filter(status__in=[
        CaseStatus.UNDER_REVIEW, CaseStatus.NOT_STARTED, CaseStatus.ASSIGNED,
        CaseStatus.IN_PROGRESS, CaseStatus.WAITING_FOR_INFO, CaseStatus.SOLVED,
        CaseStatus.CLOSED, CaseStatus.REOPENED
    ]).count()
    not_attempted_cases = cases.filter(status=CaseStatus.SUBMITTED).count()
    not_started_cases = cases.filter(status__in=[
        CaseStatus.UNDER_REVIEW, CaseStatus.NOT_STARTED, CaseStatus.ASSIGNED
    ]).count()
    urgent_cases = cases.filter(priority=CasePriority.URGENT).count()

    # Not Started Age Report Table (Wireframe 4)
    not_started_list = cases.filter(
        status__in=[CaseStatus.SUBMITTED, CaseStatus.UNDER_REVIEW, CaseStatus.NOT_STARTED, CaseStatus.ASSIGNED]
    ).order_by('submitted_at')

    context = {
        'total_cases': total_cases,
        'attempted_cases': attempted_cases,
        'not_attempted_cases': not_attempted_cases,
        'not_started_cases': not_started_cases,
        'urgent_cases': urgent_cases,
        'not_started_list': not_started_list,
        'categories': Category.objects.filter(is_active=True),
        'authorities': Authority.objects.filter(is_active=True),
        'priorities': CasePriority.choices,
        'statuses': CaseStatus.choices,
        'selected_category': category_id,
        'selected_authority': authority_id,
        'selected_priority': priority,
        'selected_status': status,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'dashboard/admin_dashboard.html', context)


@login_required
def authority_dashboard_view(request):
    """
    Renders Wireframe 6: Authority Work Queue / Dashboard.
    Shows assigned tasks, urgent cases, and work queues for the user's authority unit.
    """
    user = request.user
    if not (user.is_authority_user or user.is_admin_user):
        raise PermissionDenied("Access restricted to authority staff.")

    authority = user.assigned_authority
    if not authority and not user.is_admin_user:
        return render(request, 'dashboard/no_authority.html')

    # If admin, allow switching authority via query parameter
    auth_param = request.GET.get('authority_id')
    if auth_param and user.is_admin_user:
        authority = Authority.objects.filter(id=auth_param).first() or authority

    cases_qs = Case.objects.filter(assigned_authority=authority) if authority else Case.objects.all()

    assigned_count = cases_qs.count()
    urgent_count = cases_qs.filter(priority=CasePriority.URGENT).count()
    in_progress_count = cases_qs.filter(status=CaseStatus.IN_PROGRESS).count()

    # Solved this month
    now = timezone.now()
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    solved_this_month = cases_qs.filter(
        status__in=[CaseStatus.SOLVED, CaseStatus.CLOSED],
        solved_at__gte=first_of_month
    ).count()

    # Dynamic filter parameter via clicking indicator cards
    filter_param = request.GET.get('filter', '').strip().lower()

    if filter_param == 'urgent':
        active_work_queue = cases_qs.filter(priority=CasePriority.URGENT)
        queue_label = "Urgent Cases"
    elif filter_param == 'in_progress':
        active_work_queue = cases_qs.filter(status=CaseStatus.IN_PROGRESS)
        queue_label = "In Progress Cases"
    elif filter_param == 'solved_month':
        active_work_queue = cases_qs.filter(
            status__in=[CaseStatus.SOLVED, CaseStatus.CLOSED],
            solved_at__gte=first_of_month
        )
        queue_label = "Solved Cases (This Month)"
    elif filter_param == 'assigned':
        active_work_queue = cases_qs
        queue_label = "All Assigned Cases"
    else:
        filter_param = 'active'
        active_work_queue = cases_qs.filter(
            status__in=[CaseStatus.ASSIGNED, CaseStatus.NOT_STARTED, CaseStatus.IN_PROGRESS, CaseStatus.WAITING_FOR_INFO]
        )
        queue_label = "Active Work Queue (Pending Action)"

    active_work_queue = active_work_queue.order_by('-priority', 'submitted_at')

    context = {
        'authority': authority,
        'assigned_count': assigned_count,
        'urgent_count': urgent_count,
        'in_progress_count': in_progress_count,
        'solved_this_month': solved_this_month,
        'work_queue': active_work_queue,
        'current_filter': filter_param,
        'queue_label': queue_label,
        'all_authorities': Authority.objects.filter(is_active=True) if user.is_admin_user else None,
    }
    return render(request, 'dashboard/authority_dashboard.html', context)


@login_required
def management_dashboard_view(request):
    """
    Renders Wireframe 8: Management Dashboard.
    Provides high-level strategic intelligence:
    - Complaints vs Suggestions
    - Urgent vs Normal
    - Resolution Rate (%)
    - Average Resolution Days
    - Top Categories
    - Authority-wise Pending Cases breakdown with Average Age
    """
    if not (request.user.is_management_user or request.user.is_admin_user):
        raise PermissionDenied("Access restricted to Faculty Management and Administrators.")

    all_cases = Case.objects.all()
    total_count = all_cases.count()

    complaints_count = all_cases.filter(case_type=CaseType.COMPLAINT).count()
    suggestions_count = all_cases.filter(case_type=CaseType.SUGGESTION).count()

    urgent_count = all_cases.filter(priority=CasePriority.URGENT).count()
    normal_count = all_cases.filter(priority=CasePriority.NORMAL).count()

    solved_or_closed = all_cases.filter(status__in=[CaseStatus.SOLVED, CaseStatus.CLOSED])
    resolution_rate = round((solved_or_closed.count() / total_count * 100), 1) if total_count > 0 else 0

    # Calculate average resolution days
    solved_days_list = [c.age_days for c in solved_or_closed]
    avg_resolution_days = round(sum(solved_days_list) / len(solved_days_list), 1) if solved_days_list else 0

    # Top categories breakdown
    top_categories = Category.objects.annotate(
        case_count=Count('cases')
    ).order_by('-case_count')[:6]

    # Authority-wise breakdown
    authorities = Authority.objects.filter(is_active=True)
    authority_breakdown = []

    for auth in authorities:
        auth_cases = Case.objects.filter(assigned_authority=auth)
        assigned_c = auth_cases.count()
        in_prog_c = auth_cases.filter(status=CaseStatus.IN_PROGRESS).count()
        not_started_c = auth_cases.filter(status__in=[CaseStatus.ASSIGNED, CaseStatus.NOT_STARTED]).count()

        pending_cases = auth_cases.filter(status__in=[CaseStatus.ASSIGNED, CaseStatus.NOT_STARTED, CaseStatus.IN_PROGRESS, CaseStatus.WAITING_FOR_INFO])
        pending_ages = [c.age_days for c in pending_cases]
        avg_age = round(sum(pending_ages) / len(pending_ages), 1) if pending_ages else 0

        authority_breakdown.append({
            'authority': auth,
            'assigned': assigned_c,
            'in_progress': in_prog_c,
            'not_started': not_started_c,
            'average_age': avg_age,
        })

    context = {
        'complaints_count': complaints_count,
        'suggestions_count': suggestions_count,
        'urgent_count': urgent_count,
        'normal_count': normal_count,
        'resolution_rate': resolution_rate,
        'avg_resolution_days': avg_resolution_days,
        'top_categories': top_categories,
        'authority_breakdown': authority_breakdown,
    }
    return render(request, 'dashboard/management_dashboard.html', context)
