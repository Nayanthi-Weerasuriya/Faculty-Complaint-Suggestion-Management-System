from django import forms
from django.core.exceptions import ValidationError
from .models import Case, CaseStatus, CaseComment
from authorities.models import Authority
from accounts.models import UserRole


from .validators import validate_evidence


class CaseSubmissionForm(forms.ModelForm):
    """
    Renders Wireframe 3: New Case Submission Form.
    Includes case type, priority, category, location, title, description,
    optional file attachments (images or videos) with validation, and declaration checkbox.
    """
    attachment_file = forms.FileField(
        required=False,
        label="Attach Image or Video Evidence",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*,video/*'})
    )

    class Meta:
        model = Case
        fields = ['case_type', 'priority', 'category', 'location', 'title', 'description', 'declaration']
        widgets = {
            'case_type': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Hall A, 2nd Floor IT Lab, Dean Office Corridor'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Brief title of the complaint or suggestion'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Provide detailed explanation of the issue or improvement suggestion'}),
            'declaration': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'declaration': "I confirm that the information submitted is accurate to the best of my knowledge."
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = self.fields['category'].queryset.filter(is_active=True)

    def clean_declaration(self):
        declaration = self.cleaned_data.get('declaration')
        if not declaration:
            raise ValidationError("You must check the declaration box to submit a case.")
        return declaration

    def clean_attachment_file(self):
        return validate_evidence(self.cleaned_data.get('attachment_file'))


class CaseReviewAssignmentForm(forms.ModelForm):
    """
    Renders Wireframe 5: Admin Case Review and Assignment.
    Allows administrators to verify/adjust category and priority,
    assign responsible authority, add internal note, or reject the case.
    """
    STATUS_CHOICES = [
        (CaseStatus.UNDER_REVIEW, 'Under Review'),
        (CaseStatus.NOT_STARTED, 'Not Started'),
        (CaseStatus.ASSIGNED, 'Assigned'),
        (CaseStatus.REJECTED, 'Rejected'),
    ]
    status = forms.ChoiceField(choices=STATUS_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta:
        model = Case
        fields = ['category', 'priority', 'assigned_authority', 'status', 'admin_notes']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'assigned_authority': forms.Select(attrs={'class': 'form-select'}),
            'admin_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Internal instructions for authority or justification if rejecting'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only active action-taking units can receive a case assignment.
        self.fields['assigned_authority'].queryset = Authority.objects.filter(is_active=True).order_by('name')

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        authority = cleaned_data.get('assigned_authority')
        admin_notes = cleaned_data.get('admin_notes')

        if authority and status != CaseStatus.REJECTED and not authority.assigned_staff.filter(
            is_active=True, role=UserRole.AUTHORITY
        ).exists():
            self.add_error('assigned_authority', 'This authority has no active officer account. Ask the System Administrator to create or activate an Authority user assigned to this unit.')

        if status in [CaseStatus.ASSIGNED, CaseStatus.NOT_STARTED] and not authority:
            self.add_error('assigned_authority', "Please select a responsible authority before accepting or assigning this case.")

        if status == CaseStatus.REJECTED and not admin_notes:
            self.add_error('admin_notes', "A rejection reason/note is required when rejecting a case.")

        return cleaned_data


class CaseProgressUpdateForm(forms.ModelForm):
    """
    Renders Wireframe 7: Case Progress Update and Closure.
    Used by authorities to update status, post progress comments,
    upload completion proof, and mark case as solved.
    Acceptance Criterion 17: A case cannot be marked solved without a resolution note!
    """
    AUTHORITY_STATUS_CHOICES = [
        (CaseStatus.IN_PROGRESS, 'In Progress'),
        (CaseStatus.WAITING_FOR_INFO, 'Waiting for Information'),
        (CaseStatus.SOLVED, 'Solved'),
    ]
    status = forms.ChoiceField(choices=AUTHORITY_STATUS_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    progress_comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Action taken / current progress update'}),
        label="Progress Comment"
    )
    completion_evidence = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*,video/*'}),
        label="Upload Completion Evidence (Optional Image/Video)"
    )

    class Meta:
        model = Case
        fields = ['status', 'resolution_notes']
        widgets = {
            'resolution_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Required when marking case as solved: Describe full resolution details.'}),
        }

    def clean_completion_evidence(self):
        return validate_evidence(self.cleaned_data.get('completion_evidence'))

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        resolution_notes = cleaned_data.get('resolution_notes')
        progress_comment = cleaned_data.get('progress_comment')

        # Acceptance Criterion 17
        if status == CaseStatus.SOLVED:
            if not resolution_notes or not resolution_notes.strip():
                self.add_error('resolution_notes', "Resolution Note is strictly required when marking a case as solved.")
        elif not progress_comment and not resolution_notes:
            self.add_error('progress_comment', "Please add a progress comment to update the case.")

        return cleaned_data


class ReporterReplyForm(forms.ModelForm):
    """A reporting user may only send a clarification/reply, never a progress update."""
    class Meta:
        model = CaseComment
        fields = ['comment_text']
        widgets = {
            'comment_text': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Reply to the case update or provide requested clarification...'
            }),
        }
