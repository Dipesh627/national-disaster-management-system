from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()

DATA = {
    'first_name': 'Reg', 'last_name': 'Tester',
    'username': 'regtester', 'email': 'reg.tester@example.com',
    'phone': '9800000000',
    'password': 'Sturdy-Pass#4821', 'confirm_password': 'Sturdy-Pass#4821',
    'accept_terms': 'on',
}


class RegisterFieldErrorsTest(TestCase):

    def setUp(self):
        self.url = reverse('register')

    def post(self, **changes):
        return self.client.post(self.url, dict(DATA, **changes))

    def test_empty_post_reports_every_required_field(self):
        response = self.client.post(self.url, {})
        errors = response.context['errors']
        for field in ('first_name', 'last_name', 'username', 'email',
                      'password', 'accept_terms'):
            self.assertIn(field, errors)
        self.assertEqual(User.objects.count(), 0)

    def test_password_mismatch_is_on_confirm_field(self):
        response = self.post(confirm_password='different')
        self.assertIn('confirm_password', response.context['errors'])

    def test_invalid_email(self):
        response = self.post(email='not-an-email')
        self.assertIn('email', response.context['errors'])

    def test_duplicate_username_and_email(self):
        User.objects.create_user(
            username='regtester', email='reg.tester@example.com',
            password='Sturdy-Pass#4821', role='CITIZEN')
        errors = self.post().context['errors']
        self.assertIn('username', errors)
        self.assertIn('email', errors)

    def test_values_are_kept_but_never_the_password(self):
        response = self.post(confirm_password='different')
        self.assertContains(response, 'value="regtester"')
        self.assertNotContains(response, 'Sturdy-Pass#4821')

    def test_valid_registration_still_works(self):
        response = self.post()
        self.assertRedirects(response, reverse('home'),
                             fetch_redirect_response=False)
        self.assertTrue(User.objects.filter(username='regtester').exists())

    def test_email_cannot_be_used_as_username(self):
        response = self.post(username='reg@example.com')
        self.assertIn('username', response.context['errors'])
        self.assertFalse(User.objects.filter(username='reg@example.com').exists())

    def test_phone_with_letters_is_rejected(self):
        response = self.post(phone='98abc12345')
        self.assertIn('phone', response.context['errors'])
        self.assertEqual(User.objects.count(), 0)

    def test_phone_is_optional_and_plus_is_allowed(self):
        self.assertEqual(self.post(phone='').status_code, 302)
        User.objects.all().delete()
        self.assertEqual(self.post(phone='+977 9800000000').status_code, 302)

    def test_password_must_not_contain_username_or_name(self):
        for pw in ('regtester', 'Regtester#9182', 'xxTesterxx#9182'):
            response = self.post(password=pw, confirm_password=pw)
            self.assertIn('password', response.context['errors'], pw)

    def test_no_remember_me_on_register_page(self):
        self.assertNotContains(self.client.get(self.url), 'remember_me')