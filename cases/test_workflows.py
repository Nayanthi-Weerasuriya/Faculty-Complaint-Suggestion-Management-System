from datetime import timedelta
from io import BytesIO, StringIO
import tempfile
from contextlib import closing
from pathlib import Path
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from accounts.models import User, UserRole
from authorities.models import Authority
from categories.models import Category
from cases.models import Case, CaseStatus, Attachment
from cases.forms import CaseSubmissionForm, CaseProgressUpdateForm
from cases.filters import ReportFilterForm
from cases.validators import validate_evidence
from notifications.models import Notification
from notifications.utils import create_notification


class WorkflowRegressionTests(TransactionTestCase):
    def setUp(self):
        self.media = tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.override = override_settings(MEDIA_ROOT=self.media.name, EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.student = User.objects.create_user('reporter', password='test-pass', role=UserRole.STUDENT, email='reporter@example.com')
        self.other = User.objects.create_user('other', role=UserRole.STUDENT)
        self.coordinator = User.objects.create_user('coordinator', role=UserRole.ADMINISTRATOR)
        self.manager = User.objects.create_user('manager', role=UserRole.FACULTY_MANAGEMENT)
        self.system = User.objects.create_user('system', role=UserRole.SYSTEM_ADMIN)
        self.authority = Authority.objects.create(name='Maintenance Division')
        self.officer = User.objects.create_user('officer', role=UserRole.AUTHORITY, assigned_authority=self.authority)
        self.category = Category.objects.create(name='Maintenance')
        self.case = Case.objects.create(title='Leak', category=self.category, location='Hall A', description='Leaking pipe', declaration=True, submitted_by=self.student)

    def login(self, user):
        self.client.force_login(user)

    def image(self):
        stream = BytesIO()
        Image.new('RGB', (2, 2)).save(stream, format='PNG')
        return SimpleUploadedFile('evidence.png', stream.getvalue(), content_type='image/png')

    def test_full_submission_to_closure_and_reopening(self):
        self.login(self.student)
        response = self.client.post(reverse('submit_case'), dict(case_type='suggestion', priority='urgent', category=self.category.pk,
            location='Lab', title='Improve lighting', description='Add lighting', declaration='on', attachment_file=self.image()))
        self.assertEqual(response.status_code, 302)
        case = Case.objects.get(title='Improve lighting')
        self.assertEqual(case.attachments.count(), 1)
        self.assertEqual(case.audit_logs.count(), 1)
        self.login(self.coordinator)
        response = self.client.post(reverse('admin_review_case', args=[case.pk]), dict(category=self.category.pk,
            priority='urgent', assigned_authority=self.authority.pk, status='assigned', admin_notes='Internal instructions'))
        self.assertEqual(response.status_code, 302)
        self.login(self.officer)
        response = self.client.post(reverse('authority_update_case', args=[case.pk]), dict(status='waiting_for_info', progress_comment='Which room?', resolution_notes=''))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(case.comments.get().comment_type, 'info_request')
        self.login(self.student)
        self.client.post(reverse('add_comment', args=[case.pk]), {'comment_text': 'Room A'})
        self.assertTrue(Notification.objects.filter(recipient=self.officer, title__startswith='Reporter reply').exists())
        self.login(self.officer)
        response = self.client.post(reverse('authority_update_case', args=[case.pk]), dict(status='solved', progress_comment='Installed', resolution_notes='New lighting installed', completion_evidence=self.image()))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Notification.objects.filter(case=case, recipient=self.student, notification_type='solved').exists())
        self.login(self.coordinator)
        self.assertEqual(self.client.post(reverse('admin_close_case', args=[case.pk])).status_code, 302)
        self.login(self.student)
        self.assertEqual(self.client.post(reverse('reopen_case', args=[case.pk])).status_code, 302)
        case.refresh_from_db()
        self.assertEqual(case.status, CaseStatus.REOPENED)
        self.assertIsNone(case.solved_at)
        self.assertIsNone(case.closed_at)
        self.assertEqual(case.resolution_notes, '')
        self.assertGreaterEqual(case.audit_logs.count(), 6)

    def test_attachment_access_matches_case_access(self):
        attachment = Attachment.objects.create(case=self.case, file=self.image(), uploaded_by=self.student)
        url = reverse('attachment', args=[attachment.pk])
        self.assertEqual(self.client.get(url).status_code, 302)
        for user, expected in [(self.other,403), (self.officer,403), (self.student,200), (self.manager,200), (self.system,200)]:
            self.login(user)
            response = self.client.get(url)
            self.assertEqual(response.status_code, expected)
            response.close()
        self.assertEqual(self.client.get(attachment.file.url).status_code, 404)

    def test_unassigned_authority_cannot_view_unassigned_case(self):
        officer = User.objects.create_user('unassigned', role=UserRole.AUTHORITY)
        self.login(officer)
        self.assertEqual(self.client.get(reverse('case_detail', args=[self.case.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse('authority_update_case', args=[self.case.pk]), {}).status_code, 403)

    def test_internal_notes_are_private(self):
        self.case.admin_notes = 'Private staff instructions'
        self.case.save()
        self.case.audit_logs.create(action_type='Admin review', notes='Private staff instructions')
        self.login(self.student)
        response = self.client.get(reverse('case_detail', args=[self.case.pk]))
        self.assertNotContains(response, 'Private staff instructions')
        self.login(self.coordinator)
        self.assertContains(self.client.get(reverse('case_detail', args=[self.case.pk])), 'Private staff instructions')

    def test_terminal_cases_cannot_be_updated(self):
        self.case.status = CaseStatus.CLOSED
        self.case.resolution_notes = 'Fixed'
        self.case.assigned_authority = self.authority
        self.case.save()
        self.login(self.officer)
        self.assertEqual(self.client.post(reverse('authority_update_case', args=[self.case.pk]), {'status':'in_progress', 'progress_comment':'Again'}).status_code,403)
        self.login(self.coordinator)
        self.assertEqual(self.client.get(reverse('admin_review_case', args=[self.case.pk])).status_code,403)

    def test_active_case_cannot_be_reopened(self):
        self.login(self.student)
        self.assertEqual(self.client.post(reverse('reopen_case', args=[self.case.pk])).status_code,403)

    def test_resolution_note_enforced_outside_forms(self):
        self.case.status = CaseStatus.SOLVED
        self.case.resolution_notes = '   '
        with self.assertRaises(ValidationError):
            self.case.save()

    def test_forged_image_and_completion_files_rejected(self):
        with self.assertRaises(ValidationError):
            validate_evidence(SimpleUploadedFile('fake.png', b'not a real image'))
        form = CaseProgressUpdateForm(data={'status':'solved','resolution_notes':'Fixed'}, files={'completion_evidence':SimpleUploadedFile('script.html',b'<script>')}, instance=self.case)
        self.assertFalse(form.is_valid())
        self.assertIn('completion_evidence',form.errors)

    def test_valid_image_accepted_and_rewound(self):
        file = self.image()
        self.assertIs(validate_evidence(file), file)
        self.assertEqual(file.tell(),0)

    def test_management_filters_and_invalid_input(self):
        self.login(self.manager)
        for name in ['management_dashboard','management_reports']:
            response = self.client.get(reverse(name), {'date_from':'bad','authority':'not-a-number'})
            self.assertEqual(response.status_code,200)
            self.assertFalse(response.context['report_filters'].is_valid())
        self.assertFalse(ReportFilterForm({'date_from':'2026-10-10','date_to':'2026-10-01'}).is_valid())
        self.assertEqual(ReportFilterForm({'priority':'urgent'}).apply(Case.objects.all()).count(),0)
        self.assertEqual(ReportFilterForm({'category':str(self.category.pk)}).apply(Case.objects.all()).count(),1)

    def test_admin_filters_do_not_crash(self):
        self.login(self.coordinator)
        self.assertEqual(self.client.get(reverse('admin_dashboard'),{'date_from':'nonsense','category':'bad','authority':'bad'}).status_code,200)

    def test_reminders_are_daily_and_skip_terminal_cases(self):
        Case.objects.filter(pk=self.case.pk).update(updated_at=timezone.now()-timedelta(days=10))
        call_command('send_pending_reminders',stdout=StringIO())
        call_command('send_pending_reminders',stdout=StringIO())
        self.assertEqual(Notification.objects.filter(case=self.case,notification_type='reminder').count(),1)
        self.case.status=CaseStatus.REJECTED
        self.case.save()
        Notification.objects.all().delete()
        call_command('send_pending_reminders',stdout=StringIO())
        self.assertFalse(Notification.objects.exists())

    def test_email_is_queued_after_commit(self):
        from django.core import mail
        create_notification(self.student,'Case update','Work has started',case=self.case)
        self.assertEqual(len(mail.outbox),1)
        self.assertEqual(mail.outbox[0].to,['reporter@example.com'])

    def test_system_role_has_configuration_permissions(self):
        self.assertTrue(self.system.has_perm('accounts.change_user'))
        self.login(self.system)
        self.assertEqual(self.client.get('/admin/accounts/user/').status_code,200)
        self.assertEqual(self.client.get('/admin/categories/category/').status_code,200)

    def test_backup_is_valid_sqlite(self):
        import sqlite3
        self.login(self.system)
        response=self.client.post(reverse('system_backup'))
        self.assertEqual(response.status_code,200)
        content=b''.join(response.streaming_content)
        response.close()
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'backup.sqlite3'
            path.write_bytes(content)
            with closing(sqlite3.connect(path)) as connection:
                self.assertEqual(connection.execute('PRAGMA integrity_check').fetchone()[0],'ok')

    def test_password_reset_and_login_have_no_demo_credentials(self):
        self.assertEqual(self.client.get(reverse('password_reset')).status_code,200)
        self.assertNotContains(self.client.get(reverse('login')),'password123')

    def test_inactive_categories_not_submittable(self):
        self.category.is_active=False
        self.category.save()
        self.assertNotIn(self.category, CaseSubmissionForm().fields['category'].queryset)

    def test_new_authority_appears_at_login(self):
        Authority.objects.create(name='Library Services')
        self.assertContains(self.client.get(reverse('complaint_handler_login')),'Library Services')

    def test_case_number_survives_deleted_highest_record(self):
        number=self.case.case_number
        self.case.delete()
        replacement=Case.objects.create(title='Replacement',category=self.category,location='Hall',description='Issue',submitted_by=self.student)
        self.assertNotEqual(replacement.case_number,number)

    def test_video_duration_and_real_container_validation(self):
        import subprocess
        import imageio_ffmpeg
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'clip.mp4'
            subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-f', 'lavfi', '-i', 'color=c=black:s=16x16:d=2', '-c:v', 'libx264', str(path)], check=True, capture_output=True)
            content=path.read_bytes()
            validate_evidence(SimpleUploadedFile('clip.mp4',content))
            with override_settings(MAX_VIDEO_DURATION_SECONDS=1):
                with self.assertRaises(ValidationError):
                    validate_evidence(SimpleUploadedFile('clip.mp4',content))
            with self.assertRaises(ValidationError):
                validate_evidence(SimpleUploadedFile('fake.mp4', b'0000ftyp' + b'0'*100))

    def test_backup_archive_contains_database_and_evidence(self):
        from zipfile import ZipFile
        Attachment.objects.create(case=self.case,file=self.image(),uploaded_by=self.student)
        with tempfile.TemporaryDirectory() as directory:
            call_command('backup_portal',directory=directory,stdout=StringIO())
            archive=next(Path(directory).glob('*.zip'))
            with ZipFile(archive) as saved:
                self.assertIn('db.sqlite3',saved.namelist())
                self.assertTrue(any(name.startswith('media/') for name in saved.namelist()))

    def test_notification_changes_require_post(self):
        notification=Notification.objects.create(recipient=self.student,title='Update',message='Update')
        self.login(self.student)
        self.assertEqual(self.client.get(reverse('mark_notification_read',args=[notification.pk])).status_code,405)
        self.assertEqual(self.client.post(reverse('mark_notification_read',args=[notification.pk])).status_code,302)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    @override_settings(DEBUG=True)
    def test_demo_seeding_is_repeatable_without_password_resets(self):
        call_command('seed_data',stdout=StringIO())
        student=User.objects.get(username='student1')
        self.assertTrue(student.check_password('password123'))
        student.set_password('changed-password')
        student.save()
        count=Case.objects.count()
        call_command('seed_data',stdout=StringIO())
        student.refresh_from_db()
        self.assertTrue(student.check_password('changed-password'))
        self.assertEqual(Case.objects.count(),count)

    def test_reassignment_preserves_audit_and_resets_start_time(self):
        self.case.assigned_authority=self.authority
        self.case.status=CaseStatus.IN_PROGRESS
        self.case.action_started_at=timezone.now()-timedelta(days=3)
        self.case.save()
        new_authority=Authority.objects.create(name='IT Unit')
        self.login(self.coordinator)
        response=self.client.post(reverse('admin_review_case',args=[self.case.pk]), dict(category=self.category.pk,
            priority='urgent',status='assigned',assigned_authority=new_authority.pk,admin_notes='Rerouted'))
        self.assertEqual(response.status_code,302)
        self.case.refresh_from_db()
        self.assertEqual(self.case.assigned_authority,new_authority)
        self.assertIsNone(self.case.action_started_at)
        self.assertIsNotNone(self.case.reviewed_at)
        self.assertIn('Priority: urgent',self.case.audit_logs.first().new_value)
