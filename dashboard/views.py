import shutil
import tempfile
from pathlib import Path
from django.shortcuts import render
from django.http import FileResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.db.models import Count, Q
from cases.filters import ReportFilterForm, DateRangeFilterForm
from config.backups import snapshot_database

from cases.models import Case, CaseStatus, CasePriority, CaseType
from categories.models import Category
from authorities.models import Authority
from accounts.models import User, UserRole


@login_required
def admin_dashboard_view(request):
    """
    Renders Unified Admin Dashboard & Case Operations Center.
    Provides operational metrics, responsive filtering, age calculation,
    and departmental performance breakdown.
    """
    if not request.user.is_administrator:
        raise PermissionDenied("Access restricted to operational administrators.")

    all_cases_qs = Case.objects.all()

    date_filters = DateRangeFilterForm(request.GET)
    if date_filters.is_valid():
        for field, lookup in [('date_from', 'submitted_at__date__gte'), ('date_to', 'submitted_at__date__lte')]:
            if date_filters.cleaned_data.get(field):
                all_cases_qs = all_cases_qs.filter(**{lookup: date_filters.cleaned_data[field]})
    else:
        all_cases_qs = all_cases_qs.none()
    # Period KPI counts (always reflects entire faculty status)
    total_count = all_cases_qs.count()
    attempted_count = all_cases_qs.filter(status__in=[
        CaseStatus.UNDER_REVIEW, CaseStatus.NOT_STARTED, CaseStatus.ASSIGNED,
        CaseStatus.IN_PROGRESS, CaseStatus.WAITING_FOR_INFO, CaseStatus.SOLVED,
        CaseStatus.CLOSED, CaseStatus.REOPENED
    ]).count()
    not_started_count = all_cases_qs.filter(status__in=[
        CaseStatus.NOT_STARTED, CaseStatus.ASSIGNED
    ]).count()
    urgent_count = all_cases_qs.filter(priority=CasePriority.URGENT).count()
    resolved_count = all_cases_qs.filter(status__in=[CaseStatus.SOLVED, CaseStatus.CLOSED]).count()

    # Queryset for display table
    cases = all_cases_qs

    q = request.GET.get('q', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    category_id = request.GET.get('category', '').strip()
    authority_id = request.GET.get('authority', '').strip()
    priority = request.GET.get('priority', '').strip()
    status = request.GET.get('status', '').strip().lower()

    filter_label = "All Faculty Cases"

    # Search keyword
    if q:
        cases = cases.filter(
            Q(case_number__icontains=q) |
            Q(title__icontains=q) |
            Q(location__icontains=q) |
            Q(description__icontains=q) |
            Q(submitted_by__username__icontains=q) |
            Q(submitted_by__reg_or_staff_id__icontains=q)
        )
        filter_label = f"Search: '{q}'"

    # Date bounds were validated and applied to the base queryset above.

    # Category filter
    if category_id:
        cases = cases.filter(category_id=category_id) if category_id.isdigit() else cases.none()

    # Authority filter
    if authority_id:
        cases = cases.filter(assigned_authority_id=authority_id) if authority_id.isdigit() else cases.none()

    # Priority filter
    if priority:
        cases = cases.filter(priority=priority)
        filter_label = f"Priority: {priority.capitalize()}"

    # Status filter logic from clicking KPI cards or dropdown
    if status == 'attempted':
        cases = cases.filter(status__in=[
            CaseStatus.UNDER_REVIEW, CaseStatus.NOT_STARTED, CaseStatus.ASSIGNED,
            CaseStatus.IN_PROGRESS, CaseStatus.WAITING_FOR_INFO, CaseStatus.SOLVED,
            CaseStatus.CLOSED, CaseStatus.REOPENED
        ])
        filter_label = "Attempted Cases (Reviewed & Active)"
    elif status == 'not_attempted' or status == 'submitted':
        cases = cases.filter(status=CaseStatus.SUBMITTED)
        filter_label = "Not Attempted Cases (Submitted, Awaiting Review)"
    elif status == 'not_started':
        cases = cases.filter(status__in=[
            CaseStatus.NOT_STARTED, CaseStatus.ASSIGNED
        ])
        filter_label = "Not Started Cases (Age Report)"
    elif status == 'urgent':
        cases = cases.filter(priority=CasePriority.URGENT)
        filter_label = "Urgent Priority Cases"
    elif status == 'open':
        cases = cases.exclude(status=CaseStatus.CLOSED)
        filter_label = 'Open Cases'
    elif status == 'resolved':
        cases = cases.filter(status__in=[CaseStatus.SOLVED, CaseStatus.CLOSED])
        filter_label = 'Solved & Closed Cases'
    elif status == 'solved':
        cases = cases.filter(status=CaseStatus.SOLVED)
        filter_label = 'Solved Cases'
    elif status and status != 'all':
        cases = cases.filter(status=status)
        filter_label = f"Status: {status.replace('_', ' ').capitalize()}"

    # Ordered table cases (urgent and oldest first)
    table_cases = cases.order_by('-priority', 'submitted_at')

    context = {
        'total_cases': total_count,
        'attempted_cases': attempted_count,
        'not_started_cases': not_started_count,
        'urgent_cases': urgent_count,
        'resolved_cases': resolved_count,
        'table_cases': table_cases,
        'categories': Category.objects.filter(is_active=True),
        'authorities': Authority.objects.filter(is_active=True),
        'priorities': CasePriority.choices,
        'statuses': CaseStatus.choices,
        'selected_category': category_id,
        'selected_authority': authority_id,
        'selected_priority': priority,
        'selected_status': status,
        'search_query': q,
        'date_from': date_from,
        'date_to': date_to,
        'date_filters': date_filters,
        'filter_label': filter_label,
    }
    return render(request, 'dashboard/admin_dashboard.html', context)


@login_required
def authority_dashboard_view(request):
    """
    Renders Wireframe 6: Authority Work Queue / Dashboard.
    Shows assigned tasks, urgent cases, and work queues for the user's authority unit.
    """
    user = request.user
    if not user.is_authority_user:
        raise PermissionDenied("Access restricted to authority staff.")

    authority = user.assigned_authority
    if not authority:
        return render(request, 'dashboard/no_authority.html')

    cases_qs = Case.objects.filter(assigned_authority=authority)

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
    if request.user.role != 'faculty_management':
        raise PermissionDenied("Access restricted to Faculty Management.")

    report_filters = ReportFilterForm(request.GET)
    all_cases = report_filters.apply(Case.objects.select_related('category', 'assigned_authority'))
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
        case_count=Count('cases', filter=Q(cases__in=all_cases))
    ).order_by('-case_count')[:6]

    # Authority-wise breakdown
    authorities = Authority.objects.all()
    authority_breakdown = []

    for auth in authorities:
        auth_cases = all_cases.filter(assigned_authority=auth)
        pending_cases = auth_cases.filter(status__in=[CaseStatus.ASSIGNED, CaseStatus.NOT_STARTED, CaseStatus.IN_PROGRESS, CaseStatus.WAITING_FOR_INFO])
        assigned_c = pending_cases.count()
        if not assigned_c:
            continue
        in_prog_c = auth_cases.filter(status=CaseStatus.IN_PROGRESS).count()
        not_started_c = auth_cases.filter(status__in=[CaseStatus.ASSIGNED, CaseStatus.NOT_STARTED]).count()

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
        'report_filters': report_filters,
        'complaints_count': complaints_count,
        'complaints_percentage': round(complaints_count / total_count * 100, 2) if total_count else 0,
        'suggestions_percentage': round(suggestions_count / total_count * 100, 2) if total_count else 0,
        'urgent_percentage': round(urgent_count / total_count * 100, 2) if total_count else 0,
        'normal_percentage': round(normal_count / total_count * 100, 2) if total_count else 0,

        'suggestions_count': suggestions_count,
        'urgent_count': urgent_count,
        'normal_count': normal_count,
        'resolution_rate': resolution_rate,
        'avg_resolution_days': avg_resolution_days,
        'top_categories': top_categories,
        'authority_breakdown': authority_breakdown,
    }
    return render(request, 'dashboard/management_dashboard.html', context)


@login_required
def management_reports_view(request):
    """Read-only detailed case reporting for Faculty Management."""
    if request.user.role != UserRole.FACULTY_MANAGEMENT:
        raise PermissionDenied("Access restricted to Faculty Management.")

    cases = Case.objects.select_related('category', 'assigned_authority', 'submitted_by').all()
    report_filters = ReportFilterForm(request.GET)
    cases = report_filters.apply(cases)

    return render(request, 'dashboard/management_reports.html', {
        'cases': cases.order_by('-submitted_at'),
        'report_filters': report_filters,
    })


@login_required
def system_dashboard_view(request):
    """System Administrator workspace for platform configuration and maintenance."""
    if not request.user.is_system_administrator:
        raise PermissionDenied("Access restricted to System Administrators.")

    context = {
        'user_count': User.objects.count(),
        'system_admin_count': User.objects.filter(role=UserRole.SYSTEM_ADMIN).count(),
        'category_count': Category.objects.count(),
        'authority_count': Authority.objects.count(),
        'active_authority_count': Authority.objects.filter(is_active=True).count(),
        'database_name': Path(settings.DATABASES['default']['NAME']).name,
        'debug_mode': settings.DEBUG,
    }
    return render(request, 'dashboard/system_dashboard.html', context)


@login_required
def system_backup_view(request):
    """Download the current SQLite database as a System Administrator backup."""
    if not request.user.is_system_administrator:
        raise PermissionDenied("Access restricted to System Administrators.")
    if request.method != 'POST':
        raise PermissionDenied("Database backup requires confirmation.")

    backup_file = tempfile.TemporaryFile()
    with tempfile.TemporaryDirectory() as directory:
        backup_path = str(Path(directory) / 'backup.sqlite3')
        snapshot_database(backup_path)
        with open(backup_path, 'rb') as saved:
            shutil.copyfileobj(saved, backup_file)
    backup_file.seek(0)
    return FileResponse(backup_file, as_attachment=True, filename='fmsc-portal-backup.sqlite3')
