"""
Regression tests for the final security audit.

Covers: admin/citizen separation, the admin dashboard citizen KPI,
Google sign-in never opening or linking an administrator account,
support-attachment extension hardening, the admin Help & Support page,
and the password-reset flow's anti-enumeration behaviour.
"""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from . import google_oauth
from .forms import SupportRequestForm

User = get_user_model()

FAKE_SESSION = {
    'state': 'fixed-state-token',
    'nonce': 'fixed-nonce-token',
    'code_verifier': 'fixed-code-verifier',
}


def _fake_start_flow(redirect_uri):
    return 'https://accounts.google.com/o/oauth2/v2/auth?fake=1', dict(
        FAKE_SESSION
    )


def _claims(email, sub):
    return {
        'email': email,
        'email_verified': 'true',
        'given_name': 'A',
        'family_name': 'B',
        'nonce': FAKE_SESSION['nonce'],
        'aud': 'x',
        'iss': 'https://accounts.google.com',
        'sub': sub,
    }


class AdminCitizenSeparationTest(TestCase):

    def setUp(self):
        self.admin = User.objects.create_superuser(
            'boss', 'boss@example.com', 'Str0ng-Pass-123'
        )
        self.citizen = User.objects.create_user(
            'cit', 'cit@example.com', 'Str0ng-Pass-123'
        )

    def test_anonymous_admin_dashboard_redirects_to_admin_login(self):
        response = self.client.get(reverse('admin_dashboard'))
        self.assertRedirects(
            response, reverse('admin_login'), fetch_redirect_response=False
        )

    def test_citizen_cannot_open_admin_dashboard(self):
        self.client.force_login(self.citizen)
        response = self.client.get(reverse('admin_dashboard'))
        self.assertRedirects(
            response, reverse('admin_login'), fetch_redirect_response=False
        )

    def test_admin_is_bounced_from_citizen_portal(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('my_reports'))
        self.assertRedirects(
            response, reverse('admin_dashboard'), fetch_redirect_response=False
        )

    def test_dashboard_citizen_kpi_excludes_staff_and_superusers(self):
        User.objects.create_user(
            'staffer', 'staffer@example.com', 'Str0ng-Pass-123',
            is_staff=True,
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        # 1 superuser + 1 staff + 1 citizen exist; only 1 is a citizen.
        self.assertEqual(response.context['total_citizens'], 1)
        self.assertEqual(response.context['total_users'], 3)

    def test_admin_help_support_page_renders(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin_help_support'))
        self.assertEqual(response.status_code, 200)


@patch.object(google_oauth, 'is_configured', return_value=True)
@patch.object(google_oauth, 'start_flow', side_effect=_fake_start_flow)
class GoogleNeverOpensAdminAccountTest(TestCase):

    def _run_callback(self, claims):
        self.client.get(reverse('google_login'))
        with patch.object(
            google_oauth, 'exchange_code',
            return_value={'id_token': 'fake'},
        ), patch.object(
            google_oauth, 'verify_id_token', return_value=claims
        ):
            return self.client.get(
                reverse('google_callback'),
                {'code': 'c', 'state': FAKE_SESSION['state']},
            )

    def test_email_match_with_superuser_is_refused_and_not_linked(self, *m):
        admin = User.objects.create_superuser(
            'boss', 'boss@example.com', 'Str0ng-Pass-123'
        )
        response = self._run_callback(_claims('boss@example.com', 'sub-1'))
        self.assertRedirects(
            response, reverse('login'), fetch_redirect_response=False
        )
        admin.refresh_from_db()
        self.assertIsNone(admin.google_sub)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_sub_match_with_staff_account_is_refused(self, *m):
        staff = User.objects.create_user(
            'st', 'st@example.com', 'Str0ng-Pass-123', is_staff=True
        )
        staff.google_sub = 'sub-2'
        staff.save(update_fields=['google_sub'])
        response = self._run_callback(_claims('st@example.com', 'sub-2'))
        self.assertRedirects(
            response, reverse('login'), fetch_redirect_response=False
        )
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_normal_citizen_email_match_still_links_and_logs_in(self, *m):
        citizen = User.objects.create_user(
            'cit', 'cit@example.com', 'Str0ng-Pass-123'
        )
        self._run_callback(_claims('cit@example.com', 'sub-3'))
        citizen.refresh_from_db()
        self.assertEqual(citizen.google_sub, 'sub-3')
        self.assertIn('_auth_user_id', self.client.session)


class SupportAttachmentHardeningTest(TestCase):

    def _form(self, upload):
        return SupportRequestForm(
            data={
                'issue_type': 'OTHER',
                'subject': 'Subject here',
                'description': 'A description long enough to pass.',
            },
            files={'attachment': upload},
        )

    def test_html_file_posing_as_pdf_is_rejected(self):
        upload = SimpleUploadedFile(
            'evil.html', b'%PDF-<script>alert(1)</script>',
            content_type='application/pdf',
        )
        form = self._form(upload)
        self.assertFalse(form.is_valid())
        self.assertIn('attachment', form.errors)

    def test_real_pdf_extension_and_header_pass_attachment_check(self):
        upload = SimpleUploadedFile(
            'doc.pdf', b'%PDF-1.4 minimal', content_type='application/pdf'
        )
        form = self._form(upload)
        form.is_valid()
        self.assertNotIn('attachment', form.errors)


class PasswordResetTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            'cit', 'cit@example.com', 'Str0ng-Pass-123'
        )

    def test_known_and_unknown_email_get_same_response(self):
        known = self.client.post(
            reverse('password_reset'), {'email': 'cit@example.com'}
        )
        unknown = self.client.post(
            reverse('password_reset'), {'email': 'nobody@example.com'}
        )
        self.assertEqual(known.status_code, unknown.status_code)
        self.assertEqual(known.url, unknown.url)

    def test_email_sent_only_for_existing_account(self):
        self.client.post(
            reverse('password_reset'), {'email': 'nobody@example.com'}
        )
        self.assertEqual(len(mail.outbox), 0)
        self.client.post(
            reverse('password_reset'), {'email': 'cit@example.com'}
        )
        self.assertEqual(len(mail.outbox), 1)

    def test_invalid_reset_token_is_not_accepted(self):
        response = self.client.get(
            reverse('password_reset_confirm', args=['bad', 'bad-token']),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)