from django.db.models import Count, Q
from cases.models import CaseStatus, CasePriority


def status_summary(cases):
    """Proposal reporting definitions; open means every status except closed."""
    counts = cases.aggregate(
        total=Count('pk'),
        attempted=Count('pk', filter=~Q(status__in=[CaseStatus.SUBMITTED, CaseStatus.REJECTED])),
        not_attempted=Count('pk', filter=Q(status=CaseStatus.SUBMITTED)),
        open=Count('pk', filter=~Q(status=CaseStatus.CLOSED)),
        not_started=Count('pk', filter=Q(status__in=[CaseStatus.ASSIGNED, CaseStatus.NOT_STARTED])),
        urgent=Count('pk', filter=Q(priority=CasePriority.URGENT)),
        normal=Count('pk', filter=Q(priority=CasePriority.NORMAL)),
        solved=Count('pk', filter=Q(status=CaseStatus.SOLVED)),
        closed=Count('pk', filter=Q(status=CaseStatus.CLOSED)),
        rejected=Count('pk', filter=Q(status=CaseStatus.REJECTED)),
    )
    labels = [('total', 'Total'), ('attempted', 'Attempted'), ('not_attempted', 'Not attempted'),
              ('open', 'Open'), ('not_started', 'Not started'), ('urgent', 'Urgent'),
              ('normal', 'Normal'), ('solved', 'Solved'), ('closed', 'Closed'), ('rejected', 'Rejected')]
    return [(label, counts[key]) for key, label in labels]
