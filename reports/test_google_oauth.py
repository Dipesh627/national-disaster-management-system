"""
Tests for "Continue with Google" (reports/google_oauth.py,
reports/views.py's google_login / google_callback /
google_signup_confirm / google_username_check), including
google_sub-based identity linking and the "Complete Your NDMS
Profile" step where a new Google user chooses their own username.

Nothing here makes a real network call to Google: google_oauth's own
network functions (start_flow / exchange_code / _get_json) are
mocked so these tests exercise NDMS's own account-matching,
username-validation and consent logic in isolation, the same way
test_register.py already isolates the local registration form.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse

from . import google_oauth, views
from .legal import TERMS_VERSION

User = get_user_model()


FAKE_SESSION_VALUES = {
    'state': 'fixed-state-token',
    'nonce': 'fixed-nonce-token',
    'code_verifier': 'fixed-code-verifier',
}


def _fake_start_flow(redirect_uri):
    return 'https://accounts.google.com/o/oauth2/v2/auth?fake=1', dict(
        FAKE_SESSION_VALUES
    )


def _fake_claims(email, given_name='Jane', family_name='Doe',
                  sub='fixed-google-sub'):
    return {
        'email': email,
        'email_verified': 'true',
        'given_name': given_name,
        'family_name': family_name,
        'nonce': FAKE_SESSION_VALUES['nonce'],
        'aud': 'fake-client-id',
        'iss': 'https://accounts.google.com',
        'sub': sub,
    }


# =========================================================
# reports/google_oauth.py -- verify_id_token() itself
#
# These mock only the HTTP call to Google's tokeninfo endpoint
# (_get_json), so the actual audience/issuer/nonce/email_verified/
# sub checks in verify_id_token() run for real.
# =========================================================

@override_settings(GOOGLE_OAUTH_CLIENT_ID='test-client-id')
class VerifyIdTokenTest(TestCase):

    def _tokeninfo(self, **overrides):
        base = {
            'aud': 'test-client-id',
            'iss': 'https://accounts.google.com',
            'sub': '1234567890',
            'email': 'jane@example.com',
            'email_verified': 'true',
            'nonce': 'expected-nonce',
        }
        base.update(overrides)
        return base

    @patch.object(google_oauth, '_get_json')
    def test_valid_token_returns_claims(self, mock_get_json):
        mock_get_json.return_value = self._tokeninfo()
        claims = google_oauth.verify_id_token('fake-id-token', 'expected-nonce')
        self.assertEqual(claims['sub'], '1234567890')
        self.assertEqual(claims['email'], 'jane@example.com')

    @patch.object(google_oauth, '_get_json')
    def test_wrong_audience_is_rejected(self, mock_get_json):
        mock_get_json.return_value = self._tokeninfo(
            aud='someone-elses-client-id'
        )
        with self.assertRaises(google_oauth.GoogleOAuthError) as ctx:
            google_oauth.verify_id_token('fake-id-token', 'expected-nonce')
        self.assertEqual(ctx.exception.reason, 'invalid_token')

    @patch.object(google_oauth, '_get_json')
    def test_wrong_issuer_is_rejected(self, mock_get_json):
        mock_get_json.return_value = self._tokeninfo(
            iss='https://not-google.example'
        )
        with self.assertRaises(google_oauth.GoogleOAuthError) as ctx:
            google_oauth.verify_id_token('fake-id-token', 'expected-nonce')
        self.assertEqual(ctx.exception.reason, 'invalid_token')

    @patch.object(google_oauth, '_get_json')
    def test_wrong_nonce_is_rejected(self, mock_get_json):
        mock_get_json.return_value = self._tokeninfo(nonce='someone-elses-nonce')
        with self.assertRaises(google_oauth.GoogleOAuthError) as ctx:
            google_oauth.verify_id_token('fake-id-token', 'expected-nonce')
        self.assertEqual(ctx.exception.reason, 'invalid_token')

    @patch.object(google_oauth, '_get_json')
    def test_unverified_email_is_rejected(self, mock_get_json):
        mock_get_json.return_value = self._tokeninfo(email_verified='false')
        with self.assertRaises(google_oauth.GoogleOAuthError) as ctx:
            google_oauth.verify_id_token('fake-id-token', 'expected-nonce')
        self.assertEqual(ctx.exception.reason, 'email_not_verified')

    @patch.object(google_oauth, '_get_json')
    def test_missing_sub_is_rejected(self, mock_get_json):
        info = self._tokeninfo()
        del info['sub']
        mock_get_json.return_value = info
        with self.assertRaises(google_oauth.GoogleOAuthError) as ctx:
            google_oauth.verify_id_token('fake-id-token', 'expected-nonce')
        self.assertEqual(ctx.exception.reason, 'invalid_token')


class CheckNewUsernameTest(TestCase):
    """
    views._check_new_username -- the ONE validator shared by the
    profile-completion form POST and the live availability check.
    """

    def test_empty_and_blank(self):
        self.assertEqual(views._check_new_username('')[1], 'empty')
        self.assertEqual(views._check_new_username('   ')[1], 'empty')
        self.assertEqual(views._check_new_username(None)[1], 'empty')

    def test_invalid_usernames(self):
        for bad in ('ab', 'has space', 'a@b.com', 'semi;colon',
                    'x' * 31, 'na\u00efve_name', 'slash/name'):
            with self.subTest(username=bad):
                self.assertEqual(
                    views._check_new_username(bad)[1], 'invalid'
                )

    def test_valid_and_available(self):
        for good in ('abc', 'jane.doe', 'jane_doe-7', 'X' * 30):
            with self.subTest(username=good):
                self.assertEqual(
                    views._check_new_username(good)[1], 'available'
                )

    def test_input_is_stripped(self):
        self.assertEqual(
            views._check_new_username('  janedoe  '),
            ('janedoe', 'available'),
        )

    def test_taken_is_case_insensitive(self):
        User.objects.create_user(
            username='JaneDoe', email='x@example.com', password='unusable-x',
        )
        self.assertEqual(views._check_new_username('janedoe')[1], 'taken')
        self.assertEqual(views._check_new_username('JANEDOE')[1], 'taken')


class GoogleDisplayNamesTest(TestCase):

    def test_uses_given_and_family_name(self):
        self.assertEqual(
            views._google_display_names(
                {'given_name': 'Jane', 'family_name': 'Doe'}
            ),
            ('Jane', 'Doe'),
        )

    def test_falls_back_to_full_name_claim(self):
        self.assertEqual(
            views._google_display_names({'name': 'Jane Q Doe'}),
            ('Jane', 'Q Doe'),
        )

    def test_single_word_name(self):
        self.assertEqual(
            views._google_display_names({'name': 'Prince'}),
            ('Prince', ''),
        )

    def test_missing_everything_is_blank_not_an_error(self):
        self.assertEqual(views._google_display_names({}), ('', ''))

    def test_trimmed_to_model_limit(self):
        given, family = views._google_display_names(
            {'given_name': 'G' * 400, 'family_name': 'F' * 400}
        )
        self.assertEqual((len(given), len(family)), (150, 150))


@override_settings(GOOGLE_OAUTH_CLIENT_ID='test-client-id',
                   GOOGLE_OAUTH_CLIENT_SECRET='test-client-secret')
class GoogleFlowParametersTest(TestCase):
    """
    PKCE / state / nonce are actually sent to Google and the code
    verifier actually goes to the token endpoint.
    """

    def test_start_flow_sends_state_nonce_and_s256_challenge(self):
        url, values = google_oauth.start_flow('https://ndms.test/cb/')
        self.assertIn('code_challenge_method=S256', url)
        self.assertIn('code_challenge=', url)
        self.assertIn('state=' + values['state'], url)
        self.assertIn('nonce=' + values['nonce'], url)
        self.assertNotIn(values['code_verifier'], url)

    @patch.object(google_oauth, '_post_form')
    def test_exchange_code_sends_code_verifier(self, mock_post):
        mock_post.return_value = {'id_token': 'tok'}
        google_oauth.exchange_code('the-code', 'https://ndms.test/cb/', 'ver')
        sent = mock_post.call_args[0][1]
        self.assertEqual(sent['code_verifier'], 'ver')
        self.assertEqual(sent['grant_type'], 'authorization_code')

    @patch.object(google_oauth, '_post_form')
    def test_exchange_without_id_token_is_rejected(self, mock_post):
        mock_post.return_value = {'access_token': 'only-this'}
        with self.assertRaises(google_oauth.GoogleOAuthError) as ctx:
            google_oauth.exchange_code('c', 'https://ndms.test/cb/', 'ver')
        self.assertEqual(ctx.exception.reason, 'token_exchange_failed')


@patch.object(google_oauth, 'is_configured', return_value=True)
@patch.object(google_oauth, 'start_flow', side_effect=_fake_start_flow)
class GoogleLoginStartTest(TestCase):

    def test_redirects_to_google(self, mock_start, mock_configured):
        response = self.client.get(reverse('google_login'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            response['Location'].startswith('https://accounts.google.com/')
        )

    def test_already_authenticated_skips_google(self, mock_start, mock_configured):
        user = User.objects.create_user(
            username='already', email='already@example.com',
            password='Sturdy-Pass#4821',
        )
        self.client.force_login(user)
        response = self.client.get(reverse('google_login'))
        self.assertRedirects(response, reverse('home'))
        mock_start.assert_not_called()


class GoogleLoginNotConfiguredTest(TestCase):

    @patch.object(google_oauth, 'is_configured', return_value=False)
    def test_shows_configuration_error_not_fake_login(self, mock_configured):
        # Explicitly simulate "Google OAuth not configured" rather
        # than relying on GOOGLE_OAUTH_CLIENT_ID/SECRET being blank:
        # a real .env (as in this dev environment) may actually set
        # them, which must not make this test silently pass/fail on
        # environment state. This must fail cleanly, never fake a
        # sign-in.
        response = self.client.get(reverse('google_login'), follow=True)
        self.assertRedirects(response, reverse('login'))
        self.assertFalse(
            response.wsgi_request.user.is_authenticated
        )


# =========================================================
# reports/views.py -- google_callback() account matching
#
# exchange_code / verify_id_token are mocked per-test to hand back
# whatever claims that scenario needs; everything downstream (sub
# matching, email matching/linking, conflict handling, new-account
# routing) runs for real.
# =========================================================

@patch.object(google_oauth, 'is_configured', return_value=True)
@patch.object(google_oauth, 'start_flow', side_effect=_fake_start_flow)
class GoogleCallbackTest(TestCase):

    def _start(self):
        self.client.get(reverse('google_login'))

    def _callback(self):
        return self.client.get(
            reverse('google_callback'),
            {'code': 'fake-code', 'state': FAKE_SESSION_VALUES['state']},
        )

    def test_cancel_returns_to_login_without_account(self, *mocks):
        self._start()
        response = self.client.get(
            reverse('google_callback'), {'error': 'access_denied'},
        )
        self.assertRedirects(response, reverse('login'))
        self.assertEqual(User.objects.count(), 0)

    def test_callback_without_a_started_flow_is_rejected(self, *mocks):
        # No google_login() first -> no state/nonce/verifier in the
        # session -> nothing to validate against.
        response = self.client.get(
            reverse('google_callback'),
            {'code': 'fake-code', 'state': FAKE_SESSION_VALUES['state']},
        )
        self.assertRedirects(response, reverse('login'))
        self.assertEqual(User.objects.count(), 0)

    def test_missing_code_is_rejected(self, *mocks):
        self._start()
        response = self.client.get(
            reverse('google_callback'),
            {'state': FAKE_SESSION_VALUES['state']},
        )
        self.assertRedirects(response, reverse('login'))
        self.assertEqual(User.objects.count(), 0)

    def test_state_mismatch_is_rejected(self, *mocks):
        self._start()
        response = self.client.get(
            reverse('google_callback'),
            {'code': 'fake-code', 'state': 'wrong-state'},
        )
        self.assertRedirects(response, reverse('login'))
        self.assertEqual(User.objects.count(), 0)

    @patch.object(google_oauth, 'exchange_code')
    @patch.object(google_oauth, 'verify_id_token')
    def test_matching_google_sub_logs_in_directly(
        self, mock_verify, mock_exchange, *mocks
    ):
        # Account already linked to this exact Google identity, even
        # though the email Google now reports differs from what's on
        # file -- sub is authoritative once linked.
        existing = User.objects.create_user(
            username='janedoe', email='old-address@example.com',
            password='Sturdy-Pass#4821', role='CITIZEN',
            google_sub='already-linked-sub',
        )

        mock_exchange.return_value = {'id_token': 'fake-id-token'}
        mock_verify.return_value = _fake_claims(
            'new-address@example.com', sub='already-linked-sub',
        )

        self._start()
        response = self._callback()

        # Direct login: the profile-completion page is skipped.
        self.assertRedirects(response, reverse('home'))
        self.assertNotIn('google_pending_signup', self.client.session)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(
            int(self.client.session['_auth_user_id']), existing.pk
        )

    @patch.object(google_oauth, 'exchange_code')
    @patch.object(google_oauth, 'verify_id_token')
    def test_existing_email_without_sub_gets_linked(
        self, mock_verify, mock_exchange, *mocks
    ):
        # Legacy username/password account trying Google for the
        # first time: controlled, one-time linking -- not a blind
        # duplicate.
        existing = User.objects.create_user(
            username='janedoe', email='jane@example.com',
            password='Sturdy-Pass#4821', role='CITIZEN',
        )
        self.assertIsNone(existing.google_sub)

        mock_exchange.return_value = {'id_token': 'fake-id-token'}
        mock_verify.return_value = _fake_claims(
            'jane@example.com', sub='newly-seen-sub',
        )

        self._start()
        response = self._callback()

        self.assertRedirects(response, reverse('home'))
        self.assertEqual(User.objects.count(), 1)

        existing.refresh_from_db()
        self.assertEqual(existing.google_sub, 'newly-seen-sub')
        self.assertEqual(
            int(self.client.session['_auth_user_id']), existing.pk
        )

    @patch.object(google_oauth, 'exchange_code')
    @patch.object(google_oauth, 'verify_id_token')
    def test_existing_email_match_is_case_insensitive(
        self, mock_verify, mock_exchange, *mocks
    ):
        User.objects.create_user(
            username='janedoe', email='Jane@Example.com',
            password='Sturdy-Pass#4821', role='CITIZEN',
        )

        mock_exchange.return_value = {'id_token': 'fake-id-token'}
        mock_verify.return_value = _fake_claims('jane@example.com')

        self._start()
        self._callback()

        self.assertEqual(User.objects.count(), 1)

    @patch.object(google_oauth, 'exchange_code')
    @patch.object(google_oauth, 'verify_id_token')
    def test_existing_email_with_different_sub_is_refused(
        self, mock_verify, mock_exchange, *mocks
    ):
        # Account already linked to a DIFFERENT Google identity than
        # the one presenting now, even though email matches -- must
        # not silently relink.
        existing = User.objects.create_user(
            username='janedoe', email='jane@example.com',
            password='Sturdy-Pass#4821', role='CITIZEN',
            google_sub='original-sub',
        )

        mock_exchange.return_value = {'id_token': 'fake-id-token'}
        mock_verify.return_value = _fake_claims(
            'jane@example.com', sub='a-completely-different-sub',
        )

        self._start()
        response = self._callback()

        self.assertRedirects(response, reverse('login'))
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(User.objects.count(), 1)

        existing.refresh_from_db()
        self.assertEqual(existing.google_sub, 'original-sub')

    @patch.object(google_oauth, 'exchange_code')
    @patch.object(google_oauth, 'verify_id_token')
    def test_deactivated_existing_account_is_refused(
        self, mock_verify, mock_exchange, *mocks
    ):
        User.objects.create_user(
            username='janedoe', email='jane@example.com',
            password='Sturdy-Pass#4821', role='CITIZEN',
            is_active=False,
        )

        mock_exchange.return_value = {'id_token': 'fake-id-token'}
        mock_verify.return_value = _fake_claims('jane@example.com')

        self._start()
        response = self._callback()

        self.assertRedirects(response, reverse('login'))
        self.assertNotIn('_auth_user_id', self.client.session)

    @patch.object(google_oauth, 'exchange_code')
    @patch.object(google_oauth, 'verify_id_token')
    def test_new_email_goes_to_consent_page_not_instant_account(
        self, mock_verify, mock_exchange, *mocks
    ):
        mock_exchange.return_value = {'id_token': 'fake-id-token'}
        mock_verify.return_value = _fake_claims('new.citizen@example.com')

        self._start()
        response = self._callback()

        self.assertRedirects(response, reverse('google_signup_confirm'))
        # No account created yet -- the person has not chosen a
        # username or given consent.
        self.assertEqual(User.objects.count(), 0)
        self.assertNotIn('_auth_user_id', self.client.session)

        # The verified identity waits in the server-side session.
        pending = self.client.session['google_pending_signup']
        self.assertEqual(pending['email'], 'new.citizen@example.com')
        self.assertEqual(pending['google_sub'], 'fixed-google-sub')
        self.assertEqual(pending['given_name'], 'Jane')
        self.assertEqual(pending['family_name'], 'Doe')

    @patch.object(google_oauth, 'exchange_code')
    @patch.object(google_oauth, 'verify_id_token')
    def test_pending_names_fall_back_to_name_claim(
        self, mock_verify, mock_exchange, *mocks
    ):
        claims = _fake_claims(
            'no.split@example.com', given_name='', family_name='',
        )
        claims['name'] = 'Sita Kumari Rai'

        mock_exchange.return_value = {'id_token': 'fake-id-token'}
        mock_verify.return_value = claims

        self._start()
        self._callback()

        pending = self.client.session['google_pending_signup']
        self.assertEqual(pending['given_name'], 'Sita')
        self.assertEqual(pending['family_name'], 'Kumari Rai')

    @patch.object(google_oauth, 'exchange_code')
    @patch.object(google_oauth, 'verify_id_token')
    def test_provider_error_shows_clean_message(
        self, mock_verify, mock_exchange, *mocks
    ):
        mock_exchange.side_effect = google_oauth.GoogleOAuthError(
            'provider_unavailable'
        )

        self._start()
        response = self._callback()

        self.assertRedirects(response, reverse('login'))
        self.assertEqual(User.objects.count(), 0)


@patch.object(google_oauth, 'is_configured', return_value=True)
@patch.object(google_oauth, 'start_flow', side_effect=_fake_start_flow)
class GoogleSignupConfirmTest(TestCase):
    """
    The "Complete Your NDMS Profile" page: the person chooses only a
    username and accepts Terms & Privacy; everything else comes from
    the verified Google identity.
    """

    def _reach_confirm_page(self, email='new.citizen@example.com',
                             sub='fixed-google-sub', given_name='Jane',
                             family_name='Doe'):
        with patch.object(google_oauth, 'exchange_code') as mock_exchange, \
                patch.object(google_oauth, 'verify_id_token') as mock_verify:

            mock_exchange.return_value = {'id_token': 'fake-id-token'}
            mock_verify.return_value = _fake_claims(
                email, given_name=given_name, family_name=family_name,
                sub=sub,
            )

            self.client.get(reverse('google_login'))
            self.client.get(
                reverse('google_callback'),
                {
                    'code': 'fake-code',
                    'state': FAKE_SESSION_VALUES['state'],
                },
            )

    def _submit(self, username='janedoe', accept=True, **extra):
        data = {'username': username}
        if accept:
            data['accept_terms'] = 'on'
        data.update(extra)
        return self.client.post(reverse('google_signup_confirm'), data)

    # ---- the page itself ---------------------------------------

    def test_no_pending_signup_redirects_to_login(self, *mocks):
        response = self.client.get(reverse('google_signup_confirm'))
        self.assertRedirects(response, reverse('login'))

    def test_page_shows_verified_email_and_only_a_username_field(
        self, *mocks
    ):
        self._reach_confirm_page(email='verified.person@example.com')

        response = self.client.get(reverse('google_signup_confirm'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Complete Your NDMS Profile')
        self.assertContains(
            response,
            'Choose a username to finish setting up your account.',
        )
        self.assertContains(response, 'Google Account Verified')
        self.assertContains(response, 'verified.person@example.com')
        self.assertContains(response, 'Choose a username')
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="accept_terms"')
        self.assertContains(response, 'Create Account')
        self.assertContains(response, 'Back to sign in')
        # Live availability indicator (filled in by google-signup.js).
        self.assertContains(response, 'google-input-state')
        self.assertContains(response, 'google-signup.js')

        # Terms & Privacy reuse the project's existing pages.
        self.assertContains(response, reverse('terms'))
        self.assertContains(response, reverse('privacy'))

        # Same NDMS logo/shell as login + register (auth_base.html).
        self.assertContains(response, 'ndms-logo.png')
        self.assertContains(response, 'National Disaster Management System')

        # Nothing else is asked of the person, and the verified email
        # is text, not an editable input.
        for forbidden in ('name="first_name"', 'name="last_name"',
                          'name="password"', 'name="confirm_password"',
                          'name="phone"', 'name="email"',
                          'type="password"', 'readonly'):
            with self.subTest(forbidden=forbidden):
                self.assertNotContains(response, forbidden)

    def test_username_field_starts_empty_not_prefilled(self, *mocks):
        self._reach_confirm_page(email='jane.doe@example.com')

        response = self.client.get(reverse('google_signup_confirm'))

        self.assertContains(response, 'value=""')
        self.assertNotContains(response, 'value="jane.doe"')

    def test_authenticated_user_is_sent_home(self, *mocks):
        user = User.objects.create_user(
            username='already', email='already@example.com',
            password='Sturdy-Pass#4821',
        )
        self.client.force_login(user)
        response = self.client.get(reverse('google_signup_confirm'))
        self.assertRedirects(response, reverse('home'))

    # ---- successful sign-up ------------------------------------

    def test_valid_username_creates_citizen_account(self, *mocks):
        self._reach_confirm_page(
            email='new.citizen@example.com', sub='brand-new-sub',
            given_name='Jane', family_name='Doe',
        )

        response = self._submit(username='jane_citizen')

        self.assertRedirects(response, reverse('home'))
        self.assertEqual(User.objects.count(), 1)

        user = User.objects.get(google_sub='brand-new-sub')
        self.assertEqual(user.username, 'jane_citizen')
        self.assertEqual(user.first_name, 'Jane')
        self.assertEqual(user.last_name, 'Doe')
        self.assertEqual(user.email, 'new.citizen@example.com')
        self.assertEqual(user.role, 'CITIZEN')
        self.assertIsNotNone(user.terms_accepted_at)
        self.assertEqual(user.terms_version, TERMS_VERSION)

        # No NDMS password is created or asked for.
        self.assertFalse(user.has_usable_password())

        # Automatically signed in, and the pending identity is gone.
        self.assertEqual(
            int(self.client.session['_auth_user_id']), user.pk
        )
        self.assertNotIn('google_pending_signup', self.client.session)

    def test_username_is_stripped_before_saving(self, *mocks):
        self._reach_confirm_page()
        self._submit(username='  spaced.name  ')
        self.assertTrue(User.objects.filter(username='spaced.name').exists())

    def test_identity_comes_from_session_not_from_the_form(self, *mocks):
        self._reach_confirm_page(
            email='real.person@example.com', sub='real-sub',
            given_name='Real', family_name='Person',
        )

        # A tampered POST tries to smuggle in a different identity.
        self._submit(
            username='honest_name',
            email='evil@example.com',
            first_name='Evil',
            last_name='Hacker',
            google_sub='someone-elses-sub',
            role='ADMIN',
            password='Sturdy-Pass#4821',
        )

        user = User.objects.get(username='honest_name')
        self.assertEqual(user.email, 'real.person@example.com')
        self.assertEqual(user.first_name, 'Real')
        self.assertEqual(user.last_name, 'Person')
        self.assertEqual(user.google_sub, 'real-sub')
        self.assertEqual(user.role, 'CITIZEN')
        self.assertFalse(user.has_usable_password())

    def test_safe_next_url_is_followed_after_signup(self, *mocks):
        self._reach_confirm_page()
        session = self.client.session
        session['google_oauth_next'] = '/somewhere/'
        session.save()

        response = self._submit()

        self.assertRedirects(
            response, '/somewhere/', fetch_redirect_response=False
        )

    # ---- username validation -----------------------------------

    def test_missing_username_is_rejected(self, *mocks):
        self._reach_confirm_page()
        response = self._submit(username='')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please enter a valid username.')
        self.assertEqual(User.objects.count(), 0)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_invalid_usernames_are_rejected(self, *mocks):
        self._reach_confirm_page()
        for bad in ('ab', 'has space', 'a@b.com', 'x' * 31, 'bad!name'):
            with self.subTest(username=bad):
                response = self._submit(username=bad)
                self.assertEqual(response.status_code, 200)
                self.assertContains(
                    response, 'Please enter a valid username.'
                )
                self.assertEqual(User.objects.count(), 0)

    def test_duplicate_username_is_rejected_not_replaced(self, *mocks):
        User.objects.create_user(
            username='taken.name', email='other@example.com',
            password='Sturdy-Pass#4821', role='CITIZEN',
        )
        self._reach_confirm_page()

        response = self._submit(username='taken.name')

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, 'Username already taken. Please choose another.'
        )
        # Nothing created, nothing silently renamed, still not signed in.
        self.assertEqual(User.objects.count(), 1)
        self.assertNotIn('_auth_user_id', self.client.session)
        # The rejected name is shown again so it can be edited.
        self.assertContains(response, 'value="taken.name"')
        # The verified Google identity is still waiting.
        self.assertIn('google_pending_signup', self.client.session)

    def test_duplicate_username_check_is_case_insensitive(self, *mocks):
        User.objects.create_user(
            username='JaneDoe', email='other@example.com',
            password='Sturdy-Pass#4821', role='CITIZEN',
        )
        self._reach_confirm_page()

        response = self._submit(username='janedoe')

        self.assertContains(
            response, 'Username already taken. Please choose another.'
        )
        self.assertEqual(User.objects.count(), 1)

    def test_person_can_retry_after_a_rejected_username(self, *mocks):
        User.objects.create_user(
            username='taken.name', email='other@example.com',
            password='Sturdy-Pass#4821', role='CITIZEN',
        )
        self._reach_confirm_page()

        self._submit(username='taken.name')
        response = self._submit(username='free.name')

        self.assertRedirects(response, reverse('home'))
        self.assertTrue(User.objects.filter(username='free.name').exists())

    # ---- Terms & Privacy ---------------------------------------

    def test_requires_terms_acceptance(self, *mocks):
        self._reach_confirm_page()

        response = self._submit(username='janedoe', accept=False)

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, 'Please accept the Terms &amp; Conditions'
        )
        self.assertEqual(User.objects.count(), 0)
        self.assertNotIn('_auth_user_id', self.client.session)
        # The username the person typed is kept.
        self.assertContains(response, 'value="janedoe"')

    def test_username_and_terms_errors_are_reported_together(self, *mocks):
        self._reach_confirm_page()
        response = self._submit(username='', accept=False)
        self.assertContains(response, 'Please enter a valid username.')
        self.assertContains(
            response, 'Please accept the Terms &amp; Conditions'
        )
        self.assertEqual(User.objects.count(), 0)

    def test_terms_checkbox_is_never_preticked(self, *mocks):
        self._reach_confirm_page()
        response = self._submit(username='janedoe', accept=False)
        self.assertNotContains(response, 'checked')

    # ---- cancel -------------------------------------------------

    def test_cancel_discards_pending_signup(self, *mocks):
        self._reach_confirm_page()

        response = self.client.post(
            reverse('google_signup_confirm'), {'cancel': '1'},
        )

        self.assertRedirects(response, reverse('login'))
        self.assertEqual(User.objects.count(), 0)
        self.assertNotIn('google_pending_signup', self.client.session)

    # ---- duplicate identities / races --------------------------

    def test_same_sub_cannot_belong_to_two_users(self, *mocks):
        # Someone already holds this Google identity.
        User.objects.create_user(
            username='firstuser', email='first@example.com',
            password='Sturdy-Pass#4821', role='CITIZEN',
            google_sub='shared-sub',
        )

        # In normal traffic google_callback's sub-first lookup routes
        # a returning Google user straight to their account. A
        # duplicate can only be attempted here if two requests for a
        # genuinely new sub interleave (double-click, second tab), so
        # simulate that by reaching this step with a pending signup
        # that carries an already-claimed sub.
        session = self.client.session
        session['google_pending_signup'] = {
            'email': 'second.person@example.com',
            'given_name': 'Second',
            'family_name': 'Person',
            'google_sub': 'shared-sub',
        }
        session.save()

        response = self._submit(username='second.person')

        self.assertRedirects(response, reverse('login'))
        self.assertEqual(User.objects.count(), 1)
        self.assertFalse(
            User.objects.filter(email='second.person@example.com').exists()
        )
        self.assertEqual(
            User.objects.get(username='firstuser').google_sub, 'shared-sub'
        )

    def test_sub_claimed_between_check_and_insert_is_stopped_by_db(
        self, *mocks
    ):
        # The precheck saw the sub as free, but another request
        # claimed it before our insert: the database's UNIQUE
        # constraint raises IntegrityError, which must end in a clean
        # redirect -- never a 500, a second account, or an overwrite.
        # Reach the page first (a sub that is not yet linked to
        # anyone), THEN let the competing request win.
        self._reach_confirm_page(
            email='loser@example.com', sub='contested-sub',
        )
        User.objects.create_user(
            username='winner', email='winner@example.com',
            password='Sturdy-Pass#4821', role='CITIZEN',
            google_sub='contested-sub',
        )

        # 1st call = the precheck (says "free"); 2nd = the check made
        # after the IntegrityError (now sees the winner).
        with patch.object(
            views, '_google_sub_taken', side_effect=[False, True]
        ):
            response = self._submit(username='loser.name')

        self.assertRedirects(response, reverse('login'))
        self.assertEqual(User.objects.count(), 1)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(
            User.objects.get(username='winner').google_sub, 'contested-sub'
        )

    def test_username_claimed_between_check_and_insert_is_stopped_by_db(
        self, *mocks
    ):
        # Same race for the username: the availability check said
        # "free", but the name was taken before our insert.
        User.objects.create_user(
            username='racer', email='racer@example.com',
            password='Sturdy-Pass#4821', role='CITIZEN',
        )
        self._reach_confirm_page()

        with patch.object(
            views, '_check_new_username',
            return_value=('racer', 'available'),
        ):
            response = self._submit(username='racer')

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, 'Username already taken. Please choose another.'
        )
        self.assertEqual(User.objects.count(), 1)
        self.assertNotIn('_auth_user_id', self.client.session)
        # The verified identity is kept so they can pick another name.
        self.assertIn('google_pending_signup', self.client.session)

    def test_unexplained_integrity_error_fails_cleanly(self, *mocks):
        self._reach_confirm_page()

        with patch.object(
            User.objects, 'create_user',
            side_effect=IntegrityError('unexpected'),
        ):
            response = self._submit(username='janedoe')

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, 'We could not create your account'
        )
        self.assertEqual(User.objects.count(), 0)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_email_registered_meanwhile_does_not_create_duplicate(
        self, *mocks
    ):
        self._reach_confirm_page(email='new.citizen@example.com')

        # The same email gets a normal account in another tab.
        existing = User.objects.create_user(
            username='localuser', email='New.Citizen@example.com',
            password='Sturdy-Pass#4821', role='CITIZEN',
        )

        response = self._submit(username='janedoe')

        self.assertRedirects(response, reverse('login'))
        self.assertEqual(User.objects.count(), 1)
        existing.refresh_from_db()
        self.assertIsNone(existing.google_sub)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_database_enforces_unique_google_sub_and_username(self, *mocks):
        from django.db import transaction

        User.objects.create_user(
            username='one', email='one@example.com',
            password='Sturdy-Pass#4821', google_sub='dup-sub',
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(
                    username='two', email='two@example.com',
                    password='Sturdy-Pass#4821', google_sub='dup-sub',
                )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(
                    username='one', email='three@example.com',
                    password='Sturdy-Pass#4821', google_sub='other-sub',
                )

        self.assertEqual(User.objects.count(), 1)

    # ---- existing accounts are unaffected ----------------------

    def test_existing_password_user_still_logs_in_normally(self, *mocks):
        User.objects.create_user(
            username='localuser', email='local@example.com',
            password='Sturdy-Pass#4821', role='CITIZEN',
        )
        self.assertTrue(
            self.client.login(
                username='localuser', password='Sturdy-Pass#4821'
            )
        )


@patch.object(google_oauth, 'is_configured', return_value=True)
@patch.object(google_oauth, 'start_flow', side_effect=_fake_start_flow)
class GoogleUsernameCheckTest(TestCase):
    """
    The JSON hint behind the live "Username available" message.
    Advisory only, and only for a browser midway through a Google
    sign-up.
    """

    def _pending(self):
        session = self.client.session
        session['google_pending_signup'] = {
            'email': 'new.citizen@example.com',
            'given_name': 'Jane',
            'family_name': 'Doe',
            'google_sub': 'fixed-google-sub',
        }
        session.save()

    def _check(self, username):
        return self.client.get(
            reverse('google_username_check'), {'username': username}
        )

    def test_forbidden_without_a_verified_google_signup(self, *mocks):
        response = self._check('janedoe')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['status'], 'unauthorized')

    def test_forbidden_for_a_signed_in_user(self, *mocks):
        user = User.objects.create_user(
            username='already', email='already@example.com',
            password='Sturdy-Pass#4821',
        )
        self.client.force_login(user)
        self._pending()
        self.assertEqual(self._check('janedoe').status_code, 403)

    def test_available(self, *mocks):
        self._pending()
        data = self._check('free.name').json()
        self.assertEqual(data['status'], 'available')
        self.assertEqual(data['message'], 'Username available')

    def test_taken(self, *mocks):
        User.objects.create_user(
            username='taken.name', email='other@example.com',
            password='Sturdy-Pass#4821',
        )
        self._pending()
        data = self._check('TAKEN.name').json()
        self.assertEqual(data['status'], 'taken')
        self.assertEqual(
            data['message'], 'Username already taken. Please choose another.'
        )

    def test_invalid(self, *mocks):
        self._pending()
        data = self._check('bad name!').json()
        self.assertEqual(data['status'], 'invalid')
        self.assertEqual(data['message'], 'Please enter a valid username.')

    def test_empty(self, *mocks):
        self._pending()
        data = self._check('').json()
        self.assertEqual(data['status'], 'empty')
        self.assertEqual(data['message'], '')

    def test_only_get_is_allowed(self, *mocks):
        self._pending()
        response = self.client.post(
            reverse('google_username_check'), {'username': 'free.name'}
        )
        self.assertEqual(response.status_code, 405)

    def test_answers_are_not_cached(self, *mocks):
        self._pending()
        self.assertIn('no-cache', self._check('free.name')['Cache-Control'])

    def test_check_never_creates_or_changes_anything(self, *mocks):
        self._pending()
        self._check('free.name')
        self.assertEqual(User.objects.count(), 0)