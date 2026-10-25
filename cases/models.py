from django.conf import settings
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from .validators import validate_evidence


class CaseType(models.TextChoices):
    COMPLAINT = 'complaint', 'Complaint'
    SUGGESTION = 'suggestion', 'Suggestion'


class CasePriority(models.TextChoices):
    URGENT = 'urgent', 'Urgent'
    NORMAL = 'normal', 'Normal'


class CaseStatus(models.TextChoices):
    SUBMITTED = 'submitted', 'Submitted'
    UNDER_REVIEW = 'under_review', 'Under Review'
    NOT_STARTED = 'not_started', 'Not Started'
    ASSIGNED = 'assigned', 'Assigned'
    IN_PROGRESS = 'in_progress', 'In Progress'
    WAITING_FOR_INFO = 'waiting_for_info', 'Waiting for Information'
    SOLVED = 'solved', 'Solved'
    CLOSED = 'closed', 'Closed'
    REJECTED = 'rejected', 'Rejected'
    REOPENED = 'reopened', 'Reopened'


class Case(models.Model):
    """
    Core Case entity representing a reported complaint or suggestion.
    Implements Section 7, 8, 9, Appendix A.
    """
    case_number = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
        help_text="Unique formatted case identifier (e.g., FMSC-2026-0001)"
    )
    title = models.CharField(max_length=255, help_text="Short title of the issue or suggestion")
    case_type = models.CharField(max_length=20, choices=CaseType.choices, default=CaseType.COMPLAINT)
    priority = models.CharField(max_length=20, choices=CasePriority.choices, default=CasePriority.NORMAL)
    category = models.ForeignKey(
        'categories.Category',
        on_delete=models.PROTECT,
        related_name='cases',
        help_text="Primary classification category"
    )
    location = models.CharField(
        max_length=255,
        help_text="Building, Lecture Hall, Laboratory, Office, or Faculty Area"
    )
    description = models.TextField(help_text="Detailed description of the complaint or suggestion")
    declaration = models.BooleanField(
        default=False,
        help_text="User declaration confirming accuracy of submitted information"
    )

    # Workflow & Lifecycle
    status = models.CharField(
        max_length=30,
        choices=CaseStatus.choices,
        default=CaseStatus.SUBMITTED,
        help_text="Current lifecycle stage"
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='submitted_cases'
    )
    assigned_authority = models.ForeignKey(
        'authorities.Authority',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cases',
        help_text="Responsible authority unit handling this case"
    )
    assigned_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='officer_assigned_cases',
        help_text="Specific staff member within the assigned authority"
    )

    # Administrative & Resolution Notes
    admin_notes = models.TextField(
        blank=True,
        help_text="Internal notes from administrator or rejection justification"
    )
    resolution_notes = models.TextField(
        blank=True,
        help_text="Mandatory summary of actions taken to resolve the issue"
    )

    # Timestamps
    submitted_at = models.DateTimeField(default=timezone.now)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    action_started_at = models.DateTimeField(null=True, blank=True)
    solved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-submitted_at']
        verbose_name = "Case"
        verbose_name_plural = "Cases"

    def __str__(self):
        return f"{self.case_number} - {self.title}"

    def clean(self):
        super().clean()
        if self.status in [CaseStatus.SOLVED, CaseStatus.CLOSED] and not self.resolution_notes.strip():
            raise ValidationError({'resolution_notes': 'A resolution note is required for solved or closed cases.'})

    @transaction.atomic
    def save(self, *args, **kwargs):
        if self.status in [CaseStatus.SOLVED, CaseStatus.CLOSED] and not self.resolution_notes.strip():
            raise ValidationError({'resolution_notes': 'A resolution note is required for solved or closed cases.'})
        # Auto-generate unique case number on creation (FMSC-YYYY-XXXX)
        if not self.case_number:
            year = timezone.now().year
            # A locked yearly counter avoids duplicate numbers on concurrent submissions.
            sequence, _ = CaseSequence.objects.select_for_update().get_or_create(year=year)
            existing = [int(number.rsplit('-', 1)[-1]) for number in
                        Case.objects.filter(case_number__startswith=f'FMSC-{year}-').values_list('case_number', flat=True)
                        if number.rsplit('-', 1)[-1].isdigit()]
            new_num = max([sequence.last_number] + existing) + 1
            sequence.last_number = new_num
            sequence.save(update_fields=['last_number'])
            self.case_number = f"FMSC-{year}-{new_num:04d}"
        super().save(*args, **kwargs)

    @property
    def age_days(self):
        """
        Calculates ageing in number of days from submission to current date
        (or to solved/closed date if already finished).
        """
        end_date = (self.solved_at or self.closed_at or timezone.now()) if self.status in [CaseStatus.SOLVED, CaseStatus.CLOSED] else timezone.now()
        delta = end_date - self.submitted_at
        return max(0, delta.days)

    @property
    def is_open(self):
        return self.status not in [CaseStatus.SOLVED, CaseStatus.CLOSED, CaseStatus.REJECTED]

    @property
    def is_attempted(self):
        """Cases reviewed, assigned, in progress, solved, or closed (Section 9)"""
        return self.status in [
            CaseStatus.UNDER_REVIEW,
            CaseStatus.NOT_STARTED,
            CaseStatus.ASSIGNED,
            CaseStatus.IN_PROGRESS,
            CaseStatus.WAITING_FOR_INFO,
            CaseStatus.SOLVED,
            CaseStatus.CLOSED,
            CaseStatus.REOPENED,
        ]

    @property
    def is_not_attempted(self):
        """Submitted but not yet reviewed or acted upon (Section 9)"""
        return self.status == CaseStatus.SUBMITTED

    @property
    def is_not_started(self):
        """Accepted or assigned, but action has not yet started (Section 9)"""
        return self.status in [CaseStatus.NOT_STARTED, CaseStatus.ASSIGNED]


class AttachmentType(models.TextChoices):
    IMAGE = 'image', 'Image'
    VIDEO = 'video', 'Video'


class Attachment(models.Model):
    """
    Evidence uploaded by reporting user or completion proof uploaded by authority.
    Appendix A & Section 7.
    """
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='cases/evidence/%Y/%m/', validators=[validate_evidence])
    file_type = models.CharField(max_length=10, choices=AttachmentType.choices, default=AttachmentType.IMAGE)
    file_name = models.CharField(max_length=255, blank=True)
    file_size_kb = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_completion_evidence = models.BooleanField(
        default=False,
        help_text="Flag indicating evidence uploaded by authority verifying issue resolution"
    )

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f"{self.case.case_number} - {self.file_name or self.file.name}"

    def save(self, *args, **kwargs):
        if self.file and not self.file_name:
            self.file_name = self.file.name.split('/')[-1].split('\\')[-1]
        if self.file and hasattr(self.file, 'size') and not self.file_size_kb:
            self.file_size_kb = int(self.file.size / 1024)
        super().save(*args, **kwargs)


class CommentType(models.TextChoices):
    INTERNAL = 'internal', 'Internal Authority Note'
    PROGRESS_UPDATE = 'progress', 'Progress Update'
    INFO_REQUEST = 'info_request', 'Information Request'
    REPORTER_REPLY = 'reporter_reply', 'Reporter Reply / Clarification'


class CaseComment(models.Model):
    """
    Progress notes, requests for clarification, or administrative feedback on a case.
    Appendix A: Preliminary Data Entities.
    """
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comment_type = models.CharField(max_length=20, choices=CommentType.choices, default=CommentType.PROGRESS_UPDATE)
    comment_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.username} on {self.case.case_number}"


class CaseSequence(models.Model):
    year = models.PositiveIntegerField(primary_key=True)
    last_number = models.PositiveIntegerField(default=0)
