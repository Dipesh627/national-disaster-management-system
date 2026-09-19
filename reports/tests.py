import base64
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from .models import (
    UserSettings,
    DisasterType,
    Disaster,
    Notification,
    NotificationRead,
    SupportRequest,
)
from .forms import CitizenSettingsForm, AdminSettingsForm

User = get_user_model()


class CitizenSettingsPhase1Test(TestCase):

    def setUp(self):
        self.client = Client()
        self.citizen = User.objects.create_user(
            username="testcitizen",
            email="citizen@example.com",
            password="TestPassword123!",
            role="CITIZEN",
            full_name="Test Citizen"
        )
        self.admin = User.objects.create_superuser(
            username="testadmin",
            email="admin@example.com",
            password="AdminPassword123!",
            role="ADMIN"
        )
        self.disaster_type = DisasterType.objects.create(
            name="Flood",
            description="Flooding incident",
            is_active=True
        )

    def test_user_settings_model_defaults(self):
        """Verify UserSettings model has theme and preserved defaults."""
        settings = UserSettings.objects.create(user=self.citizen)
        self.assertEqual(settings.date_format, 'DMY')
        self.assertEqual(settings.time_zone, 'Asia/Kathmandu')
        self.assertEqual(settings.theme, 'SYSTEM')
        self.assertEqual(settings.font_size, 'STANDARD')
        self.assertFalse(settings.reduce_motion)
        self.assertFalse(settings.high_contrast)
        self.assertIsNone(settings.default_disaster_type)

    def test_citizen_settings_form_valid(self):
        """Verify CitizenSettingsForm validates and persists supported fields."""
        settings = UserSettings.objects.create(user=self.citizen)
        form_data = {
            'date_format': 'YMD',
            'time_zone': 'Asia/Kolkata',
            'theme': 'DARK',
            'font_size': 'LARGE',
            'reduce_motion': True,
            'high_contrast': True,
            'default_disaster_type': self.disaster_type.pk,
        }
        form = CitizenSettingsForm(data=form_data, instance=settings)
        self.assertTrue(form.is_valid(), form.errors)
        saved = form.save()
        self.assertEqual(saved.date_format, 'YMD')
        self.assertEqual(saved.time_zone, 'Asia/Kolkata')
        self.assertEqual(saved.theme, 'DARK')
        self.assertEqual(saved.font_size, 'LARGE')
        self.assertTrue(saved.reduce_motion)
        self.assertTrue(saved.high_contrast)
        self.assertEqual(saved.default_disaster_type, self.disaster_type)

    def test_settings_view_get_authenticated(self):
        """Verify citizen can view settings page with all required sections."""
        self.client.force_login(self.citizen)
        response = self.client.get(reverse('settings'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "General Preferences")
        self.assertContains(response, "Appearance")
        self.assertContains(response, "Accessibility")
        self.assertContains(response, "Reporting Preferences")
        self.assertContains(response, "Account Security")
        self.assertContains(response, "Help &amp; Support")
        self.assertContains(response, "About NDMS")
        self.assertContains(response, "id_date_format")
        self.assertContains(response, "id_time_zone")
        self.assertContains(response, "id_default_disaster_type")
        self.assertContains(response, "id_reduce_motion")
        self.assertContains(response, "id_high_contrast")

    def test_settings_view_post_success(self):
        """Verify citizen can save settings with PRG redirect and success message."""
        self.client.force_login(self.citizen)
        post_data = {
            'date_format': 'MDY',
            'time_zone': 'UTC',
            'theme': 'LIGHT',
            'font_size': 'LARGE',
            'reduce_motion': 'on',
            'high_contrast': 'on',
            'default_disaster_type': self.disaster_type.pk,
        }
        response = self.client.post(reverse('settings'), post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your settings have been saved successfully.")

        settings = UserSettings.objects.get(user=self.citizen)
        self.assertEqual(settings.date_format, 'MDY')
        self.assertEqual(settings.time_zone, 'UTC')
        self.assertEqual(settings.theme, 'LIGHT')
        self.assertEqual(settings.font_size, 'LARGE')
        self.assertTrue(settings.reduce_motion)
        self.assertTrue(settings.high_contrast)
        self.assertEqual(settings.default_disaster_type, self.disaster_type)

    def test_create_disaster_report_preselects_default_disaster_type(self):
        """Verify create_disaster_report preselects default_disaster_type if configured."""
        UserSettings.objects.create(
            user=self.citizen,
            default_disaster_type=self.disaster_type
        )
        self.client.force_login(self.citizen)
        response = self.client.get(reverse('create_disaster_report'))
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertEqual(form.initial.get('disaster_type'), self.disaster_type)

    def test_admin_settings_remains_independent(self):
        """Verify Admin Settings page is completely unaffected."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin_settings'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SYSTEM SETTINGS")
        self.assertContains(response, "General Preferences")
        self.assertContains(response, "Accessibility")


class SupportRequestAdminNotificationTest(TestCase):
    """
    Citizen submits Support Request -> eligible Admins receive a
    Notification via the existing Notification/NotificationRead
    system -- see create_support_request_notification() and
    reports.views.help_support().
    """

    def setUp(self):
        self.client = Client()

        self.citizen = User.objects.create_user(
            username="notifycitizen",
            email="notifycitizen@example.com",
            password="TestPassword123!",
            role="CITIZEN",
            full_name="Notify Citizen",
        )

        self.other_citizen = User.objects.create_user(
            username="othercitizen",
            email="othercitizen@example.com",
            password="TestPassword123!",
            role="CITIZEN",
            full_name="Other Citizen",
        )

        self.admin = User.objects.create_superuser(
            username="notifyadmin",
            email="notifyadmin@example.com",
            password="AdminPassword123!",
        )

        self.staff_admin = User.objects.create_user(
            username="staffadmin",
            email="staffadmin@example.com",
            password="AdminPassword123!",
            is_staff=True,
        )

    def _submit(self, subject="Cannot upload photo"):
        self.client.force_login(self.citizen)
        return self.client.post(
            reverse('help_support'),
            {
                'issue_type': 'TECHNICAL',
                'subject': subject,
                'description': 'Details about the problem.',
            },
        )

    def test_valid_submission_creates_one_notification_per_admin(self):
        """
        #31/#41: successful submission -> exactly one Notification
        per eligible admin (superuser + staff), pointing at the
        right SupportRequest, citizen NOT among the recipients.
        """
        response = self._submit(subject="Road blockage")

        self.assertRedirects(response, reverse('help_support'))

        support_request = SupportRequest.objects.get()
        self.assertEqual(support_request.subject, "Road blockage")
        self.assertEqual(support_request.user, self.citizen)

        notifications = Notification.objects.filter(
            support_request=support_request
        )

        self.assertEqual(notifications.count(), 2)

        recipients = set(
            notifications.values_list('recipient_id', flat=True)
        )
        self.assertEqual(
            recipients,
            {self.admin.id, self.staff_admin.id},
        )

        for notification in notifications:
            self.assertEqual(notification.notification_type, 'GENERAL')
            self.assertEqual(notification.title, 'New Support Request')
            self.assertIn('Road blockage', notification.message)
            self.assertEqual(notification.published_by, self.citizen)

        # #34: citizen isolation -- neither citizen received one.
        self.assertFalse(
            Notification.objects.filter(
                support_request=support_request,
                recipient__in=[self.citizen, self.other_citizen],
            ).exists()
        )

    def test_invalid_submission_creates_no_notification(self):
        """#32: a validation failure creates neither a SupportRequest
        nor a Notification."""
        self.client.force_login(self.citizen)

        response = self.client.post(
            reverse('help_support'),
            {
                'issue_type': 'TECHNICAL',
                'subject': '',  # required field left blank
                'description': '',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(SupportRequest.objects.exists())
        self.assertFalse(Notification.objects.exists())

    def test_refresh_does_not_duplicate_notification(self):
        """#33: re-GETting the redirect target after submission never
        creates a second notification for the same request."""
        self._submit()

        self.assertEqual(
            Notification.objects.filter(
                support_request=SupportRequest.objects.get()
            ).count(),
            2,
        )

        for _ in range(3):
            self.client.get(reverse('help_support'))

        self.assertEqual(SupportRequest.objects.count(), 1)
        self.assertEqual(
            Notification.objects.filter(
                support_request=SupportRequest.objects.get()
            ).count(),
            2,
        )

    def test_multiple_requests_create_correctly_linked_notifications(self):
        """#35: three separate submissions -> each admin has three
        notifications, each pointing at the correct SupportRequest."""
        self._submit(subject="Issue A")
        self._submit(subject="Issue B")
        self._submit(subject="Issue C")

        self.assertEqual(SupportRequest.objects.count(), 3)
        self.assertEqual(
            Notification.objects.filter(recipient=self.admin).count(), 3
        )
        self.assertEqual(
            Notification.objects.filter(recipient=self.staff_admin).count(),
            3,
        )

        for support_request in SupportRequest.objects.all():
            self.assertEqual(
                Notification.objects.filter(
                    support_request=support_request
                ).count(),
                2,
            )

    def test_admin_bell_surfaces_unread_support_notification(self):
        """#31 (admin half): the notification appears in the admin
        shell's unread support-notification context, is included in
        the combined bell count, and disappears from "unread" once
        marked read -- all via the real Notification/NotificationRead
        models, no separate counter."""
        self._submit(subject="App keeps crashing")
        support_request = SupportRequest.objects.get()
        notification = Notification.objects.get(recipient=self.admin)

        self.client.force_login(self.admin)

        dashboard_response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(
            dashboard_response.context['admin_support_notifications_count'],
            1,
        )
        self.assertIn(
            notification,
            list(dashboard_response.context['admin_support_notifications']),
        )
        self.assertGreaterEqual(
            dashboard_response.context['admin_alerts_total_count'], 1
        )

        # Clicking it marks it read (existing NotificationRead
        # mechanism) and routes to the existing Support Request
        # Detail page -- and never touches SupportRequest itself.
        read_response = self.client.post(
            reverse(
                'admin_mark_support_notification_read',
                args=[notification.id],
            )
        )
        self.assertRedirects(
            read_response,
            reverse(
                'admin_support_request_detail',
                args=[support_request.id],
            ),
        )

        self.assertTrue(
            NotificationRead.objects.filter(
                user=self.admin, notification=notification
            ).exists()
        )

        support_request.refresh_from_db()
        # SupportRequest has no status field to begin with, so this
        # simply confirms nothing new was added/changed on it.
        self.assertEqual(support_request.subject, "App keeps crashing")

        dashboard_response_after = self.client.get(
            reverse('admin_dashboard')
        )
        self.assertEqual(
            dashboard_response_after.context[
                'admin_support_notifications_count'
            ],
            0,
        )

    def test_other_admin_cannot_mark_notification_read(self):
        """#21: a notification is personal to the admin it was
        created for -- another admin cannot mark it read or be
        redirected via it."""
        self._submit()
        notification = Notification.objects.get(recipient=self.admin)

        self.client.force_login(self.staff_admin)

        response = self.client.post(
            reverse(
                'admin_mark_support_notification_read',
                args=[notification.id],
            )
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            NotificationRead.objects.filter(
                user=self.staff_admin, notification=notification
            ).exists()
        )

    def test_citizen_notification_bell_unaffected(self):
        """#18/#36: the citizen's own notification dropdown never
        includes the admin-facing support-request notification."""
        self._submit()

        self.client.force_login(self.citizen)
        response = self.client.get(reverse('dashboard'))

        citizen_notifications = list(response.context['notifications'])
        self.assertFalse(
            any(
                n.support_request_id is not None
                for n in citizen_notifications
            )
        )


class SupportRequestNotificationTemplateSmokeTest(TestCase):
    """Renders every touched/adjacent admin+citizen template end to
    end to catch any template error the unit tests above wouldn't
    (e.g. a bad {% url %} tag or undefined variable in base.html)."""

    def setUp(self):
        self.client = Client()

        self.citizen = User.objects.create_user(
            username="smokecitizen",
            email="smokecitizen@example.com",
            password="TestPassword123!",
            role="CITIZEN",
            full_name="Smoke Citizen",
        )

        self.admin = User.objects.create_superuser(
            username="smokeadmin",
            email="smokeadmin@example.com",
            password="AdminPassword123!",
        )

        self.client.force_login(self.citizen)
        self.client.post(
            reverse('help_support'),
            {
                'issue_type': 'OTHER',
                'subject': 'Smoke test subject',
                'description': 'Smoke test description.',
            },
        )
        self.support_request = SupportRequest.objects.get()
        self.notification = Notification.objects.get(recipient=self.admin)

    def test_citizen_pages_render(self):
        self.client.force_login(self.citizen)
        for name in ['dashboard', 'alerts', 'help_support']:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200, name)

    def test_admin_pages_render(self):
        self.client.force_login(self.admin)

        for name in [
            'admin_dashboard',
            'admin_support_requests',
            'admin_notifications',
        ]:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200, name)
            self.assertContains(response, 'New Support Request')

        detail_response = self.client.get(
            reverse(
                'admin_support_request_detail',
                args=[self.support_request.id],
            )
        )
        self.assertEqual(detail_response.status_code, 200)

        notif_detail_response = self.client.get(
            reverse(
                'admin_notification_detail',
                args=[self.notification.id],
            )
        )
        self.assertEqual(notif_detail_response.status_code, 200)

# =========================================================
# PHASE A FINAL VERIFICATION
# =========================================================
#
# Covers the three Phase A behaviours that had model/view code
# but no dedicated automated coverage yet:
#   1. Disaster.resolved_date lifecycle (admin_disaster_update_status)
#   2. SupportRequest status + admin_response loop (admin_support_request_respond)
#   3. The citizen-facing "response changed" Notification + its
#      de-duplication rules (create_support_response_notification)
#
# Plus a small regression class for existing behaviour these
# Phase A views sit next to (attachment upload, admin support
# list/detail, disaster lifecycle end to end).
# =========================================================


class DisasterResolvedDateLifecycleTest(TestCase):
    """
    Disaster.status is a strictly forward-only chain (see
    DISASTER_STATUS_TRANSITIONS in reports.admin_views):
    ACTIVE -> UNDER_CONTROL -> RESOLVED -> CLOSED.
    resolved_date is set automatically, exactly once, the first
    time a Disaster reaches RESOLVED, and must never be
    overwritten by the later RESOLVED -> CLOSED transition.
    """

    def setUp(self):
        self.client = Client()

        self.admin = User.objects.create_superuser(
            username="lifecycleadmin",
            email="lifecycleadmin@example.com",
            password="AdminPassword123!",
        )

        self.citizen = User.objects.create_user(
            username="lifecyclecitizen",
            email="lifecyclecitizen@example.com",
            password="TestPassword123!",
            role="CITIZEN",
            full_name="Lifecycle Citizen",
        )

        self.disaster_type = DisasterType.objects.create(
            name="Landslide",
            description="Landslide incident",
            is_active=True,
        )

        self.disaster = Disaster.objects.create(
            disaster_type=self.disaster_type,
            title="Hillside Landslide",
            description="Ongoing landslide response.",
            severity="HIGH",
            status="ACTIVE",
            start_date=timezone.now(),
        )

    def _update_status(self, new_status):
        self.client.force_login(self.admin)
        return self.client.post(
            reverse(
                "admin_disaster_update_status",
                args=[self.disaster.id],
            ),
            {"status": new_status},
        )

    def test_active_to_under_control_leaves_resolved_date_unset(self):
        response = self._update_status("UNDER_CONTROL")
        self.disaster.refresh_from_db()

        self.assertRedirects(
            response,
            reverse("admin_disaster_detail", args=[self.disaster.id]),
        )
        self.assertEqual(self.disaster.status, "UNDER_CONTROL")
        self.assertIsNone(self.disaster.resolved_date)

    def test_under_control_to_resolved_sets_resolved_date(self):
        self._update_status("UNDER_CONTROL")

        self._update_status("RESOLVED")
        self.disaster.refresh_from_db()

        self.assertEqual(self.disaster.status, "RESOLVED")
        self.assertIsNotNone(self.disaster.resolved_date)

    def test_resolved_to_closed_does_not_overwrite_resolved_date(self):
        self._update_status("UNDER_CONTROL")
        self._update_status("RESOLVED")

        self.disaster.refresh_from_db()
        original_resolved_date = self.disaster.resolved_date
        self.assertIsNotNone(original_resolved_date)

        self._update_status("CLOSED")
        self.disaster.refresh_from_db()

        self.assertEqual(self.disaster.status, "CLOSED")
        self.assertEqual(self.disaster.resolved_date, original_resolved_date)

    def test_invalid_transition_is_blocked(self):
        """ACTIVE cannot jump straight to RESOLVED, and status/
        resolved_date are both left completely untouched."""
        response = self._update_status("RESOLVED")
        self.disaster.refresh_from_db()

        self.assertRedirects(
            response,
            reverse("admin_disaster_detail", args=[self.disaster.id]),
        )
        self.assertEqual(self.disaster.status, "ACTIVE")
        self.assertIsNone(self.disaster.resolved_date)

    def test_invalid_backwards_transition_is_blocked(self):
        """Once UNDER_CONTROL, moving back to ACTIVE is rejected."""
        self._update_status("UNDER_CONTROL")

        response = self._update_status("ACTIVE")
        self.disaster.refresh_from_db()

        self.assertRedirects(
            response,
            reverse("admin_disaster_detail", args=[self.disaster.id]),
        )
        self.assertEqual(self.disaster.status, "UNDER_CONTROL")

    def test_closed_has_no_further_transitions(self):
        self._update_status("UNDER_CONTROL")
        self._update_status("RESOLVED")
        self._update_status("CLOSED")

        response = self._update_status("ACTIVE")
        self.disaster.refresh_from_db()

        self.assertEqual(self.disaster.status, "CLOSED")

    def test_unauthorized_citizen_cannot_update_disaster_status(self):
        """A logged-in Citizen (not staff/superuser) is rejected by
        admin_required -- the disaster is left completely unchanged."""
        self.client.force_login(self.citizen)

        response = self.client.post(
            reverse(
                "admin_disaster_update_status",
                args=[self.disaster.id],
            ),
            {"status": "UNDER_CONTROL"},
        )

        self.assertRedirects(response, reverse("admin_login"))

        self.disaster.refresh_from_db()
        self.assertEqual(self.disaster.status, "ACTIVE")
        self.assertIsNone(self.disaster.resolved_date)

    def test_anonymous_user_cannot_update_disaster_status(self):
        response = self.client.post(
            reverse(
                "admin_disaster_update_status",
                args=[self.disaster.id],
            ),
            {"status": "UNDER_CONTROL"},
        )

        self.assertRedirects(response, reverse("admin_login"))

        self.disaster.refresh_from_db()
        self.assertEqual(self.disaster.status, "ACTIVE")


class SupportRequestAdminResponseTest(TestCase):
    """
    Covers the admin response loop added on top of SupportRequest
    in Phase A: status transitions, admin_response persistence,
    responded_at semantics, citizen-side visibility/isolation, and
    the citizen-facing Notification + its de-duplication rules
    (see reports.admin_views.admin_support_request_respond and
    reports.models.create_support_response_notification).
    """

    def setUp(self):
        self.client = Client()

        self.citizen = User.objects.create_user(
            username="respondcitizen",
            email="respondcitizen@example.com",
            password="TestPassword123!",
            role="CITIZEN",
            full_name="Respond Citizen",
        )

        self.other_citizen = User.objects.create_user(
            username="otherrespondcitizen",
            email="otherrespondcitizen@example.com",
            password="TestPassword123!",
            role="CITIZEN",
            full_name="Other Respond Citizen",
        )

        self.admin = User.objects.create_superuser(
            username="respondadmin",
            email="respondadmin@example.com",
            password="AdminPassword123!",
        )

        self.support_request = SupportRequest.objects.create(
            user=self.citizen,
            issue_type="TECHNICAL",
            subject="App crashes on submit",
            description="The app crashes every time I submit a report.",
        )

    def _respond(self, status, admin_response):
        self.client.force_login(self.admin)
        return self.client.post(
            reverse(
                "admin_support_request_respond",
                args=[self.support_request.id],
            ),
            {
                "status": status,
                "admin_response": admin_response,
            },
        )

    # ---- status / default -------------------------------------------

    def test_default_status_is_open(self):
        self.assertEqual(self.support_request.status, "OPEN")

    def test_open_to_in_progress(self):
        response = self._respond("IN_PROGRESS", "")
        self.support_request.refresh_from_db()

        self.assertRedirects(
            response,
            reverse(
                "admin_support_request_detail",
                args=[self.support_request.id],
            ),
        )
        self.assertEqual(self.support_request.status, "IN_PROGRESS")

    def test_in_progress_to_resolved(self):
        self._respond("IN_PROGRESS", "")

        # RESOLVED requires a non-empty response (see
        # AdminSupportRequestResponseForm.clean()) -- a request can
        # never be marked Resolved with nothing explaining why.
        self._respond("RESOLVED", "This has been fixed.")
        self.support_request.refresh_from_db()

        self.assertEqual(self.support_request.status, "RESOLVED")

    def test_resolved_requires_a_non_empty_response(self):
        """Marking RESOLVED with a blank response is rejected by
        form validation -- status is left unchanged."""
        response = self._respond("RESOLVED", "")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["response_form"].is_valid())

        self.support_request.refresh_from_db()
        self.assertEqual(self.support_request.status, "OPEN")
        self.assertIsNone(self.support_request.responded_at)

    # ---- admin_response / responded_at --------------------------------

    def test_admin_response_is_saved(self):
        self._respond("IN_PROGRESS", "We are looking into this now.")
        self.support_request.refresh_from_db()

        self.assertEqual(
            self.support_request.admin_response,
            "We are looking into this now.",
        )

    def test_responded_at_set_when_real_response_posted(self):
        self.assertIsNone(self.support_request.responded_at)

        self._respond("IN_PROGRESS", "We are looking into this now.")
        self.support_request.refresh_from_db()

        self.assertIsNotNone(self.support_request.responded_at)

    def test_status_only_change_does_not_set_responded_at(self):
        """Changing only status (no reply text yet) must not set
        responded_at or fire a citizen-facing notification."""
        self._respond("IN_PROGRESS", "")
        self.support_request.refresh_from_db()

        self.assertIsNone(self.support_request.responded_at)
        self.assertFalse(
            Notification.objects.filter(
                support_request=self.support_request,
                recipient=self.citizen,
            ).exists()
        )

    def test_resubmitting_identical_response_does_not_update_responded_at(self):
        self._respond("IN_PROGRESS", "Please try reinstalling the app.")
        self.support_request.refresh_from_db()
        first_responded_at = self.support_request.responded_at
        self.assertIsNotNone(first_responded_at)

        # Same status, exact same response text -- e.g. a duplicate
        # form submission / page reload.
        self._respond("IN_PROGRESS", "Please try reinstalling the app.")
        self.support_request.refresh_from_db()

        self.assertEqual(
            self.support_request.responded_at, first_responded_at
        )

    def test_changing_response_text_updates_responded_at(self):
        self._respond("IN_PROGRESS", "Please try reinstalling the app.")
        self.support_request.refresh_from_db()
        first_responded_at = self.support_request.responded_at

        self._respond(
            "RESOLVED",
            "Reinstalling fixed a known bug -- confirmed resolved.",
        )
        self.support_request.refresh_from_db()

        self.assertGreaterEqual(
            self.support_request.responded_at, first_responded_at
        )
        self.assertEqual(
            self.support_request.admin_response,
            "Reinstalling fixed a known bug -- confirmed resolved.",
        )

    # ---- notifications --------------------------------------------------

    def test_admin_reply_creates_notification_for_correct_citizen(self):
        self._respond("IN_PROGRESS", "We are on it.")

        notification = Notification.objects.get(
            support_request=self.support_request
        )

        self.assertEqual(notification.recipient, self.citizen)
        self.assertNotEqual(notification.recipient, self.other_citizen)

    def test_notification_points_to_correct_support_request(self):
        other_request = SupportRequest.objects.create(
            user=self.citizen,
            issue_type="OTHER",
            subject="A second, unrelated request",
            description="Different issue entirely.",
        )

        self._respond("IN_PROGRESS", "Replying to the first request.")

        notification = Notification.objects.get(
            support_request=self.support_request
        )

        self.assertEqual(notification.support_request, self.support_request)
        self.assertNotEqual(notification.support_request, other_request)
        self.assertFalse(
            Notification.objects.filter(
                support_request=other_request
            ).exists()
        )

    def test_status_only_change_creates_no_notification(self):
        self._respond("IN_PROGRESS", "")

        self.assertFalse(
            Notification.objects.filter(
                support_request=self.support_request
            ).exists()
        )

    def test_duplicate_response_does_not_create_second_notification(self):
        self._respond("IN_PROGRESS", "Please try reinstalling the app.")
        self.assertEqual(
            Notification.objects.filter(
                support_request=self.support_request
            ).count(),
            1,
        )

        self._respond("IN_PROGRESS", "Please try reinstalling the app.")
        self.assertEqual(
            Notification.objects.filter(
                support_request=self.support_request
            ).count(),
            1,
        )

    def test_changed_response_creates_a_new_notification(self):
        self._respond("IN_PROGRESS", "Please try reinstalling the app.")
        self.assertEqual(
            Notification.objects.filter(
                support_request=self.support_request
            ).count(),
            1,
        )

        self._respond("RESOLVED", "Confirmed fixed in the latest update.")
        self.assertEqual(
            Notification.objects.filter(
                support_request=self.support_request
            ).count(),
            2,
        )

    def test_admin_facing_support_notification_unaffected_by_reply(self):
        """The original admin-facing "New Support Request"
        notification created at submission time is untouched by an
        admin later responding to that same request."""
        admin_notification = Notification.objects.create(
            recipient=self.admin,
            support_request=self.support_request,
            notification_type=Notification.TYPE_GENERAL,
            title="New Support Request",
            message="A citizen has submitted a new support request.",
            published_by=self.citizen,
        )

        self._respond("RESOLVED", "All set, thanks for reporting this.")

        admin_notification.refresh_from_db()
        self.assertEqual(admin_notification.title, "New Support Request")
        self.assertEqual(admin_notification.recipient, self.admin)
        self.assertEqual(
            Notification.objects.filter(
                support_request=self.support_request
            ).count(),
            2,  # original admin-facing one + the new citizen-facing reply
        )

    # ---- citizen-side visibility / isolation -----------------------------

    def test_citizen_sees_own_status_and_response(self):
        self._respond("RESOLVED", "This has been fixed, please update.")

        self.client.force_login(self.citizen)
        response = self.client.get(reverse("help_support"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "App crashes on submit")
        self.assertContains(response, "This has been fixed, please update.")

        my_requests = list(response.context["my_support_requests"])
        self.assertEqual(len(my_requests), 1)
        self.assertEqual(my_requests[0].status, "RESOLVED")

    def test_citizen_cannot_see_another_citizens_support_request(self):
        self._respond("RESOLVED", "This has been fixed, please update.")

        self.client.force_login(self.other_citizen)
        response = self.client.get(reverse("help_support"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "App crashes on submit")
        self.assertNotContains(
            response, "This has been fixed, please update."
        )

        my_requests = list(response.context["my_support_requests"])
        self.assertEqual(len(my_requests), 0)

    def test_unauthorized_citizen_cannot_respond_to_support_request(self):
        """A logged-in Citizen hitting the admin respond endpoint
        directly is rejected by admin_required, and the request is
        left completely unchanged."""
        self.client.force_login(self.citizen)

        response = self.client.post(
            reverse(
                "admin_support_request_respond",
                args=[self.support_request.id],
            ),
            {
                "status": "RESOLVED",
                "admin_response": "Pretending to be an admin.",
            },
        )

        self.assertRedirects(response, reverse("admin_login"))

        self.support_request.refresh_from_db()
        self.assertEqual(self.support_request.status, "OPEN")
        self.assertEqual(self.support_request.admin_response, "")
        self.assertIsNone(self.support_request.responded_at)
        self.assertFalse(
            Notification.objects.filter(
                support_request=self.support_request
            ).exists()
        )

    def test_anonymous_user_cannot_respond_to_support_request(self):
        response = self.client.post(
            reverse(
                "admin_support_request_respond",
                args=[self.support_request.id],
            ),
            {
                "status": "RESOLVED",
                "admin_response": "Pretending to be an admin.",
            },
        )

        self.assertRedirects(response, reverse("admin_login"))

        self.support_request.refresh_from_db()
        self.assertEqual(self.support_request.status, "OPEN")


class PhaseARegressionTest(TestCase):
    """
    Small regression sweep for existing behaviour that sits next
    to (and shares models/views with) the Phase A changes above:
    support submission, attachment upload, the admin support
    list/detail pages, and the full disaster lifecycle end to end.
    """

    def setUp(self):
        self.client = Client()

        self.citizen = User.objects.create_user(
            username="regressioncitizen",
            email="regressioncitizen@example.com",
            password="TestPassword123!",
            role="CITIZEN",
            full_name="Regression Citizen",
        )

        self.admin = User.objects.create_superuser(
            username="regressionadmin",
            email="regressionadmin@example.com",
            password="AdminPassword123!",
        )

        self.disaster_type = DisasterType.objects.create(
            name="Fire",
            description="Fire incident",
            is_active=True,
        )

    def test_support_submission_still_works(self):
        self.client.force_login(self.citizen)

        response = self.client.post(
            reverse("help_support"),
            {
                "issue_type": "ACCOUNT",
                "subject": "Cannot change my password",
                "description": "The change-password form errors out.",
            },
        )

        self.assertRedirects(response, reverse("help_support"))

        support_request = SupportRequest.objects.get()
        self.assertEqual(support_request.user, self.citizen)
        self.assertEqual(support_request.status, "OPEN")
        self.assertEqual(support_request.admin_response, "")

    def test_support_attachment_upload_still_works(self):
        self.client.force_login(self.citizen)

        # A genuine 1x1 PNG (not arbitrary bytes) -- clean_attachment()
        # runs a real Pillow decode on any declared image upload, so
        # the fixture has to be a real, decodable PNG to exercise the
        # "valid image attaches successfully" path this test covers.
        attachment = SimpleUploadedFile(
            "screenshot.png",
            base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4"
                "nGP4z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC"
            ),
            content_type="image/png",
        )

        response = self.client.post(
            reverse("help_support"),
            {
                "issue_type": "TECHNICAL",
                "subject": "Error with screenshot attached",
                "description": "See attached screenshot.",
                "attachment": attachment,
            },
        )

        self.assertRedirects(response, reverse("help_support"))

        support_request = SupportRequest.objects.get()
        self.assertTrue(bool(support_request.attachment))
        self.assertIn("screenshot", support_request.attachment.name)

    def test_admin_support_list_and_detail_still_work(self):
        support_request = SupportRequest.objects.create(
            user=self.citizen,
            issue_type="OTHER",
            subject="Regression check request",
            description="Checking the admin list/detail pages.",
        )

        self.client.force_login(self.admin)

        list_response = self.client.get(reverse("admin_support_requests"))
        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, "Regression check request")

        detail_response = self.client.get(
            reverse(
                "admin_support_request_detail",
                args=[support_request.id],
            )
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "Regression check request")

    def test_full_disaster_lifecycle_end_to_end(self):
        disaster = Disaster.objects.create(
            disaster_type=self.disaster_type,
            title="Warehouse Fire",
            description="Fire response in progress.",
            severity="CRITICAL",
            status="ACTIVE",
            start_date=timezone.now(),
        )

        self.client.force_login(self.admin)

        for target_status in ("UNDER_CONTROL", "RESOLVED", "CLOSED"):
            response = self.client.post(
                reverse(
                    "admin_disaster_update_status",
                    args=[disaster.id],
                ),
                {"status": target_status},
            )
            self.assertRedirects(
                response,
                reverse("admin_disaster_detail", args=[disaster.id]),
            )
            disaster.refresh_from_db()
            self.assertEqual(disaster.status, target_status)

        self.assertIsNotNone(disaster.resolved_date)

    def test_notification_system_still_works(self):
        """Existing broadcast disaster-alert Notification creation
        (unrelated to SupportRequest) is unaffected by the Phase A
        additions to the Notification model."""
        from .models import create_disaster_alert_notification

        disaster = Disaster.objects.create(
            disaster_type=self.disaster_type,
            title="Flash Flood",
            description="Broadcast alert regression check.",
            severity="HIGH",
            status="ACTIVE",
            start_date=timezone.now(),
        )

        notification = create_disaster_alert_notification(
            disaster, self.admin
        )

        self.assertIsNone(notification.recipient)
        self.assertEqual(notification.disaster, disaster)
        self.assertEqual(
            notification.notification_type,
            Notification.TYPE_DISASTER_ALERT,
        )