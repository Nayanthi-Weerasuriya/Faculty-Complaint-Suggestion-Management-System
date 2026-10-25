import os
from django import forms
from django.core.exceptions import ValidationError
from .models import Case, CaseType, CasePriority, CaseStatus, Attachment, AttachmentType, CaseComment, CommentType
from categories.models import Category
from authorities.models import Authority


ALLOWED_IMAGE_EXTS = ['.jpg', '.jpeg', '.png', '.webp']
ALLOWED_VIDEO_EXTS = ['.mp4', '.mov', '.avi', '.mkv']
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB


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

    def clean_declaration(self):
        declaration = self.cleaned_data.get('declaration')
        if not declaration:
            raise ValidationError("You must check the declaration box to submit a case.")
        return declaration

    def clean_attachment_file(self):
        file = self.cleaned_data.get('attachment_file')
        if file:
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in ALLOWED_IMAGE_EXTS and ext not in ALLOWED_VIDEO_EXTS:
                raise ValidationError(f"Unsupported file format '{ext}'. Allowed formats: JPG, PNG, WEBP, MP4, MOV.")
            if file.size > MAX_FILE_SIZE:
                raise ValidationError(f"File size exceeds 25 MB limit ({file.size / (1024*1024):.1f} MB uploaded).")
        return file


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

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        authority = cleaned_data.get('assigned_authority')
        admin_notes = cleaned_data.get('admin_notes')

        if status == CaseStatus.ASSIGNED and not authority:
            self.add_error('assigned_authority', "Please select a responsible authority to assign this case to.")

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

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        resolution_notes = cleaned_data.get('resolution_notes')
        progress_comment = cleaned_data.get('progress_comment')

        # Acceptance Criterion 17
        if status == CaseStatus.SOLVED:
            if not resolution_notes or not resolution_notes.strip():
                self.add_error('resolution_notes', "Resolution Note is strictly required when marking a case as solved (Criterion 17).")
        elif not progress_comment and not resolution_notes:
            self.add_error('progress_comment', "Please add a progress comment to update the case.")

        return cleaned_data


class CaseCommentForm(forms.ModelForm):
    class Meta:
        model = CaseComment
        fields = ['comment_type', 'comment_text']
        widgets = {
            'comment_type': forms.Select(attrs={'class': 'form-select'}),
            'comment_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Write your comment or update here...'}),
        }
