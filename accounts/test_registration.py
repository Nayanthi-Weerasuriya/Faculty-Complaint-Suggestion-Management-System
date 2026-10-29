from datetime import timedelta
import re
from unittest.mock import patch
from django.contrib.auth import authenticate
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from .forms import PublicRegistrationForm
from .models import User, UserRole


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', UNIVERSITY_EMAIL_DOMAINS=['sjp.ac.lk'])
class PublicRegistrationTests(TestCase):
    def data(self, **changes):
        data = dict(first_name='Nimali', last_name='Perera', username='nimali', email='nimali@mgt.sjp.ac.lk',
                    reg_or_staff_id='FMSC/2026/3001', department_or_unit='Accounting', role='student',
                    password1='CedarBridge!946', password2='CedarBridge!946')
        data.update(changes)
        return data

    def register(self, **changes):
        return self.client.post(reverse('register'), self.data(**changes))

    def link(self):
        return re.search(r'https?://[^\s]+', mail.outbox[-1].body)[0]

    def test_landing_is_public_and_keeps_case_records_private(self):
        response = self.client.get(reverse('landing'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('register'))
        self.assertContains(response, 'Faculty Complaint &amp;')
        self.assertNotIn('recent_cases', response.context)
        self.assertEqual(self.client.get(reverse('home')).status_code, 302)
        self.assertEqual(self.client.get(reverse('submit_case')).status_code, 302)

    def test_registration_verification_and_login(self):
        self.assertRedirects(self.register(), reverse('registration_done'))
        user = User.objects.get(username='nimali')
        self.assertFalse(user.is_active)
        self.assertTrue(user.registration_pending)
        self.assertFalse(user.is_staff)
        self.assertTrue(user.check_password('CedarBridge!946'))
        self.assertIsNone(authenticate(username='nimali', password='CedarBridge!946'))
        self.assertEqual(len(mail.outbox), 1)
        link = self.link()
        self.assertContains(self.client.get(link), 'Verify email')
        user.refresh_from_db()
        self.assertFalse(user.is_active)  # Email scanners cannot activate by GET.
        self.assertRedirects(self.client.post(link), reverse('login'))
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertFalse(user.registration_pending)
        self.assertIsNotNone(user.email_verified_at)
        self.assertContains(self.client.get(link), 'no longer available')
        response = self.client.post(reverse('login'), {'username':user.email, 'password':'CedarBridge!946'})
        self.assertRedirects(response, reverse('home'))

    def test_lecturer_registration_and_no_privilege_injection(self):
        self.assertEqual(self.register(role='lecturer', is_staff='on', is_superuser='on', is_active='on', assigned_authority='1').status_code, 302)
        user = User.objects.get(username='nimali')
        self.assertEqual(user.role, UserRole.LECTURER)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_active)
        self.assertIsNone(user.assigned_authority)

    def test_privileged_roles_are_rejected(self):
        for role in ['administrator', 'authority', 'faculty_management', 'system_admin']:
            response = self.register(role=role)
            self.assertEqual(response.status_code, 200)
            self.assertIn('role', response.context['form'].errors)
        self.assertFalse(User.objects.exists())

    def test_university_domain_and_subdomain_validation(self):
        for email in ['person@gmail.com', 'person@fakesjp.ac.lk', 'person@sjp.ac.lk.attacker.com']:
            form = PublicRegistrationForm(self.data(email=email))
            self.assertFalse(form.is_valid())
            self.assertIn('email', form.errors)
        for email in ['person@sjp.ac.lk', 'person@std.sjp.ac.lk', 'person@MGT.SJP.AC.LK']:
            self.assertTrue(PublicRegistrationForm(self.data(email=email)).is_valid())

    def test_duplicate_identifiers_are_case_insensitive(self):
        User.objects.create_user('ExistingName', email='existing@sjp.ac.lk', reg_or_staff_id='FMSC/2026/OLD')
        for field, value in [('username','existingname'),('email','EXISTING@SJP.AC.LK'),('reg_or_staff_id','fmsc/2026/old'),('username','existing@sjp.ac.lk')]:
            form = PublicRegistrationForm(self.data(**{field:value}))
            self.assertFalse(form.is_valid())
            self.assertIn(field, form.errors)

    def test_weak_password_and_missing_identity_are_rejected(self):
        form = PublicRegistrationForm(self.data(password1='password', password2='password', reg_or_staff_id=''))
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)
        self.assertIn('reg_or_staff_id', form.errors)

    def test_registration_department_must_be_selected_from_department_list(self):
        form = PublicRegistrationForm(self.data(department_or_unit='Finance'))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['department_or_unit'], 'Finance')

        invalid_form = PublicRegistrationForm(self.data(department_or_unit='Unlisted department'))
        self.assertFalse(invalid_form.is_valid())
        self.assertIn('department_or_unit', invalid_form.errors)

    def test_tampered_and_expired_links_do_not_activate(self):
        self.register()
        link = self.link()
        self.assertContains(self.client.post(link.rstrip('/') + 'broken/'), 'no longer available')
        import time
        with patch('django.core.signing.time.time', return_value=time.time() + 86401):
            self.assertContains(self.client.post(link), 'no longer available')
        self.assertFalse(User.objects.get(username='nimali').is_active)

    def test_resend_replaces_old_link_and_is_throttled(self):
        self.register()
        old_link = self.link()
        user = User.objects.get(username='nimali')
        User.objects.filter(pk=user.pk).update(verification_sent_at=timezone.now()-timedelta(minutes=2))
        self.assertRedirects(self.client.post(reverse('resend_verification'), {'email':user.email}), reverse('registration_done'))
        new_link = self.link()
        self.assertNotEqual(old_link, new_link)
        self.assertContains(self.client.post(old_link), 'no longer available')
        response = self.client.post(reverse('resend_verification'), {'email':user.email})
        self.assertEqual(response.status_code, 200)
        self.assertIn('Please wait', str(response.context['form'].errors))
        self.assertEqual(len(mail.outbox), 2)
        self.assertRedirects(self.client.post(new_link), reverse('login'))

    def test_resend_does_not_reactivate_disabled_existing_accounts(self):
        user = User.objects.create_user('disabled', email='disabled@sjp.ac.lk', is_active=False)
        self.client.post(reverse('resend_verification'), {'email':user.email})
        self.assertEqual(len(mail.outbox), 0)
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    def test_mail_failure_keeps_account_pending_and_gives_recovery(self):
        with patch('accounts.verification.send_mail', side_effect=OSError('Unavailable')):
            with self.assertLogs('accounts.verification', level='ERROR'):
                response = self.register()
        self.assertRedirects(response, reverse('registration_done'), fetch_redirect_response=False)
        self.assertFalse(User.objects.get(username='nimali').is_active)
        self.assertContains(self.client.get(reverse('registration_done')), 'could not send')

    def test_verified_email_cannot_be_replaced_without_verification(self):
        self.register()
        self.client.post(self.link())
        user = User.objects.get(username='nimali')
        self.client.force_login(user)
        self.client.post(reverse('profile'), dict(first_name='Nimali', last_name='Perera', email='replacement@gmail.com', reg_or_staff_id=user.reg_or_staff_id, department_or_unit='Accounting', contact_number=''))
        user.refresh_from_db()
        self.assertEqual(user.email, 'nimali@mgt.sjp.ac.lk')

    def test_authenticated_users_keep_dashboard_and_skip_registration(self):
        user = User.objects.create_user('coordinator', role=UserRole.ADMINISTRATOR)
        self.client.force_login(user)
        self.assertContains(self.client.get(reverse('landing')), 'Go to my dashboard')
        self.assertRedirects(self.client.get(reverse('register')), reverse('home'), fetch_redirect_response=False)
        self.assertRedirects(self.client.get(reverse('home')), reverse('admin_dashboard'))

    def test_verification_requires_csrf_protected_post(self):
        from django.test import Client
        self.register()
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(self.link()).status_code, 403)

    def test_unverified_accounts_cannot_use_password_reset_to_skip_verification(self):
        self.register()
        self.client.post(reverse('password_reset'), {'email':'nimali@mgt.sjp.ac.lk'})
        self.assertEqual(len(mail.outbox), 1)

    def test_email_can_also_be_username_and_login_after_verification(self):
        email = 'nimali@mgt.sjp.ac.lk'
        response = self.register(username=email, email=email)
        self.assertRedirects(response, reverse('registration_done'))
        user = User.objects.get(email=email)
        self.assertEqual(user.username, email)
        self.assertRedirects(self.client.post(self.link()), reverse('login'))
        self.assertEqual(authenticate(username=email, password='CedarBridge!946').pk, user.pk)

    def test_registration_id_can_also_be_username(self):
        form = PublicRegistrationForm(self.data(username='FMSC20263001', reg_or_staff_id='FMSC20263001'))
        self.assertTrue(form.is_valid(), form.errors)


@override_settings(DEBUG=True, LOCAL_EMAIL_PREVIEW_ENABLED=True, EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend')
class LocalVerificationPreviewTests(TestCase):
    data = PublicRegistrationTests.data
    register = PublicRegistrationTests.register

    def setUp(self):
        self.client.defaults['HTTP_HOST'] = 'localhost'
        self.sender = patch('accounts.verification.send_mail', return_value=1)
        self.sender.start()
        self.addCleanup(self.sender.stop)

    def test_own_registration_can_be_verified_using_demo_link(self):
        self.assertRedirects(self.register(), reverse('registration_done'))
        response = self.client.get(reverse('registration_done'))
        self.assertContains(response, 'Open verification link')
        self.assertContains(response, 'No email will arrive')
        self.assertIn('no-store', response['Cache-Control'])
        link = response.context['local_verification_url']
        user = User.objects.get(username='nimali')
        self.assertFalse(user.is_active)
        self.assertRedirects(self.client.post(link), reverse('login'))
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertNotContains(self.client.get(reverse('registration_done')), 'Open verification link')
        self.assertEqual(authenticate(username=user.email, password='CedarBridge!946').pk, user.pk)

    def test_other_browser_and_query_parameters_cannot_access_demo_link(self):
        from django.test import Client
        self.register()
        other = Client(HTTP_HOST='localhost')
        response = other.get(reverse('registration_done'), {'email':'nimali@mgt.sjp.ac.lk','user_id':User.objects.get().pk})
        self.assertIsNone(response.context['local_verification_url'])
        other.post(reverse('resend_verification'), {'email':'nimali@mgt.sjp.ac.lk'})
        self.assertIsNone(other.get(reverse('registration_done')).context['local_verification_url'])

    @override_settings(DEBUG=False)
    def test_preview_hidden_in_production_even_when_flag_is_enabled(self):
        self.register()
        self.assertIsNone(self.client.get(reverse('registration_done')).context['local_verification_url'])

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_preview_hidden_for_non_console_email(self):
        self.register()
        self.assertIsNone(self.client.get(reverse('registration_done')).context['local_verification_url'])

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend')
    def test_preview_hidden_with_smtp_email(self):
        self.register()
        self.assertIsNone(self.client.get(reverse('registration_done')).context['local_verification_url'])

    @override_settings(LOCAL_EMAIL_PREVIEW_ENABLED=False)
    def test_preview_can_be_disabled_explicitly(self):
        self.register()
        self.assertIsNone(self.client.get(reverse('registration_done')).context['local_verification_url'])

    @override_settings(ALLOWED_HOSTS=['localhost', 'portal.example.com'])
    def test_preview_hidden_on_nonlocal_hostname(self):
        self.register()
        response = self.client.get(reverse('registration_done'), HTTP_HOST='portal.example.com')
        self.assertIsNone(response.context['local_verification_url'])

    def test_expired_registration_does_not_get_a_fresh_demo_token(self):
        self.register()
        User.objects.update(verification_sent_at=timezone.now()-timedelta(days=2))
        self.assertIsNone(self.client.get(reverse('registration_done')).context['local_verification_url'])

    def test_existing_disabled_user_cannot_receive_a_demo_link(self):
        user = User.objects.create_user('disabled', email='disabled@sjp.ac.lk', is_active=False)
        session = self.client.session
        session['registered_user_id'] = user.pk
        session.save()
        self.assertIsNone(self.client.get(reverse('registration_done')).context['local_verification_url'])
