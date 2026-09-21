from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from .legal import TERMS_VERSION

User = get_user_model()


VALID_REGISTRATION = {
    'first_name': 'Consent',
    'last_name': 'Tester',
    'username': 'consenttester',
    'email': 'consent.tester@example.com',
    'phone': '9800000000',
    'password': 'Sturdy-Pass#4821',
    'confirm_password': 'Sturdy-Pass#4821',
}


class LegalPagesTest(TestCase):
    """Terms & Privacy pages are public and reachable by every role."""

    def setUp(self):
        self.client = Client()

    def test_terms_page_loads_for_visitors(self):
        response = self.client.get(reverse('terms'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Terms &amp; Conditions')
        self.assertContains(response, 'Last Updated')
        self.assertContains(response, TERMS_VERSION)

    def test_privacy_page_loads_for_visitors(self):
        response = self.client.get(reverse('privacy'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Privacy Policy')
        self.assertContains(response, 'Last Updated')

    def test_footer_links_to_legal_pages(self):
        response = self.client.get(reverse('terms'))
        self.assertContains(response, 'href="%s"' % reverse('privacy'))
        self.assertContains(response, 'href="%s"' % reverse('terms'))

    def test_admin_is_not_redirected_away_from_legal_pages(self):
        admin = User.objects.create_superuser(
            username='legaladmin',
            email='legaladmin@example.com',
            password='Sturdy-Pass#4821',
        )
        self.client.force_login(admin)

        for name in ('terms', 'privacy'):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200)


class RegistrationConsentTest(TestCase):
    """Registration must fail on the server without consent."""

    def setUp(self):
        self.client = Client()
        self.url = reverse('register')

    def test_register_page_shows_consent_checkbox_and_links(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'name="accept_terms"')
        self.assertContains(response, 'href="%s"' % reverse('terms'))
        self.assertContains(response, 'href="%s"' % reverse('privacy'))

    def test_registration_without_consent_is_rejected(self):
        response = self.client.post(self.url, VALID_REGISTRATION)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please accept the Terms')
        self.assertFalse(
            User.objects.filter(username='consenttester').exists()
        )

    def test_failed_consent_keeps_safe_values_but_never_the_password(self):
        response = self.client.post(self.url, VALID_REGISTRATION)

        self.assertContains(response, 'value="consenttester"')
        self.assertContains(response, 'value="consent.tester@example.com"')
        self.assertNotContains(response, 'Sturdy-Pass#4821')

    def test_registration_with_consent_succeeds_and_is_recorded(self):
        data = dict(VALID_REGISTRATION, accept_terms='on')
        response = self.client.post(self.url, data)

        self.assertRedirects(
            response, reverse('home'), fetch_redirect_response=False
        )

        user = User.objects.get(username='consenttester')
        self.assertIsNotNone(user.terms_accepted_at)
        self.assertEqual(user.terms_version, TERMS_VERSION)
        self.assertEqual(user.role, 'CITIZEN')

    def test_existing_users_have_no_recorded_acceptance_and_can_log_in(self):
        User.objects.create_user(
            username='olduser',
            email='old@example.com',
            password='Sturdy-Pass#4821',
            role='CITIZEN',
        )
        old = User.objects.get(username='olduser')

        self.assertIsNone(old.terms_accepted_at)
        self.assertEqual(old.terms_version, '')
        self.assertTrue(
            self.client.login(
                username='olduser', password='Sturdy-Pass#4821'
            )
        )