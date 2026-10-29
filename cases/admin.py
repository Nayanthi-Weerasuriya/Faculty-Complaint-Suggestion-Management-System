from django.contrib import admin
from config.admin import WorkflowReadOnlyAdmin, WorkflowReadOnlyInline
from django.urls import reverse
from django.utils.html import format_html
from .models import Case, Attachment, CaseComment


class AttachmentInline(WorkflowReadOnlyInline, admin.TabularInline):
    model = Attachment
    extra = 0
    readonly_fields = ('uploaded_at', 'file_size_kb', 'evidence_link')

    @admin.display(description='Evidence')
    def evidence_link(self, obj):
        return format_html('<a href="{}">View evidence</a>', reverse('attachment', args=[obj.pk])) if obj.pk else '-'


class CaseCommentInline(WorkflowReadOnlyInline, admin.StackedInline):
    model = CaseComment
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(Case)
class CaseAdmin(WorkflowReadOnlyAdmin):
    list_display = ('case_number', 'title', 'case_type', 'priority', 'status', 'category', 'assigned_authority', 'submitted_by', 'submitted_at', 'age_days')
    list_filter = ('status', 'priority', 'case_type', 'category', 'assigned_authority', 'submitted_at')
    search_fields = ('case_number', 'title', 'description', 'location', 'submitted_by__username', 'submitted_by__reg_or_staff_id')
    readonly_fields = ('case_number', 'submitted_at', 'updated_at', 'age_days')
    inlines = [AttachmentInline, CaseCommentInline]


@admin.register(Attachment)
class AttachmentAdmin(WorkflowReadOnlyAdmin):
    readonly_fields = ('evidence_link',)

    @admin.display(description='Evidence')
    def evidence_link(self, obj):
        return format_html('<a href="{}">View evidence</a>', reverse('attachment', args=[obj.pk])) if obj.pk else '-'

    list_display = ('case', 'file_name', 'file_type', 'file_size_kb', 'is_completion_evidence', 'uploaded_by', 'uploaded_at')
    list_filter = ('file_type', 'is_completion_evidence', 'uploaded_at')


@admin.register(CaseComment)
class CaseCommentAdmin(WorkflowReadOnlyAdmin):
    list_display = ('case', 'author', 'comment_type', 'created_at')
    list_filter = ('comment_type', 'created_at')
