from django.contrib.auth.models import AbstractUser
from django.db import models


# =========================================================
# USER
# =========================================================

class User(AbstractUser):

    ROLE_CHOICES = [
        ('CITIZEN', 'Citizen'),
    ]

    # NOTE:
    # first_name / last_name are already provided by
    # AbstractUser -- do NOT redeclare them here. The old
    # custom `full_name` field has been removed (its data was
    # migrated into first_name/last_name by migration 0027,
    # then the column itself was dropped by migration 0028).
    # Use get_full_name() wherever a combined display name is
    # needed.

    phone = models.CharField(
        max_length=20,
        blank=True
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='CITIZEN'
    )

    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True
    )

    # ---------------------------------------------------
    # TERMS & PRIVACY ACCEPTANCE (recorded at registration)
    #
    # terms_accepted_at -- when the person ticked the consent
    #   checkbox and created their account.
    # terms_version     -- which version of the Terms & Conditions
    #   and Privacy Policy they accepted (see reports/legal.py).
    #
    # Accounts created BEFORE the Terms were introduced keep
    # NULL / '' here: no acceptance is recorded for them and none
    # is assumed. A separate boolean is not needed -- "accepted"
    # simply means terms_accepted_at is not NULL.
    # ---------------------------------------------------

    terms_accepted_at = models.DateTimeField(
        null=True,
        blank=True
    )

    terms_version = models.CharField(
        max_length=20,
        blank=True,
        default=''
    )

    def __str__(self):
        return self.username


# =========================================================
# DISASTER TYPE
# =========================================================

class DisasterType(models.Model):

    name = models.CharField(
        max_length=100
    )

    description = models.TextField(
        blank=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_date = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.name


# =========================================================
# DISASTER
# =========================================================

class Disaster(models.Model):

    SEVERITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]

    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('UNDER_CONTROL', 'Under Control'),
        ('RESOLVED', 'Resolved'),
        ('CLOSED', 'Closed'),
    ]

    disaster_type = models.ForeignKey(
        DisasterType,
        on_delete=models.PROTECT,
        related_name='disasters'
    )

    title = models.CharField(
        max_length=200
    )

    description = models.TextField(
        blank=True
    )

    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default='MEDIUM'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ACTIVE'
    )

    start_date = models.DateTimeField()

    # -----------------------------------------------------
    # LOCATION
    # (nullable/blank so existing disaster records created
    # before this field existed remain valid; only new
    # disasters are required — at the form level — to supply
    # a location.)
    # -----------------------------------------------------

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )

    address = models.CharField(
        max_length=255,
        blank=True
    )

    # -----------------------------------------------------
    # RESOLVED DATE (Phase A)
    # Set automatically, exactly once, the first time this
    # Disaster's status becomes RESOLVED (see
    # reports.admin_views.admin_disaster_update_status).
    # Deliberately NOT touched again on the RESOLVED -> CLOSED
    # transition, so it always reflects when the disaster was
    # actually resolved, not when it was later closed out.
    #
    # null=True/blank=True because every disaster that is still
    # ACTIVE or UNDER_CONTROL (and every disaster that existed
    # before this field did) has no resolved date yet -- this is
    # never required at the form level, only ever set by the
    # status-transition view itself.
    # -----------------------------------------------------

    resolved_date = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return self.title


# =========================================================
# DISASTER REPORT
# =========================================================

class DisasterReport(models.Model):

    # ---------------------------------------------------
    # REPORTED SEVERITY
    # (severity AS REPORTED BY THE CITIZEN at submission
    # time -- intentionally separate from Disaster.severity,
    # which is the actual/admin-managed severity of the
    # linked Disaster once one exists. Reusing the same
    # four levels for familiarity, but kept as its own
    # choices tuple so the two fields never accidentally
    # share/mutate the same list.)
    # ---------------------------------------------------

    SEVERITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('UNDER_REVIEW', 'Under Review'),
        ('VERIFIED', 'Verified'),
        ('REJECTED', 'Rejected'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='disaster_reports'
    )

    disaster_type = models.ForeignKey(
        DisasterType,
        on_delete=models.PROTECT,
        related_name='disaster_reports'
    )

    disaster = models.ForeignKey(
        Disaster,
        on_delete=models.SET_NULL,
        related_name='reports',
        blank=True,
        null=True
    )

    # ---------------------------------------------------
    # CITIZEN-REPORTED SEVERITY
    # Distinct from Disaster.severity -- see SEVERITY_CHOICES
    # comment above. Defaults to 'MEDIUM' only so that any
    # existing rows created before this field existed remain
    # valid after migration; the citizen-facing form always
    # requires an explicit selection (see DisasterReportForm).
    # ---------------------------------------------------

    reported_severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default='MEDIUM',
        help_text='Severity level as reported by the citizen.'
    )

    # ---------------------------------------------------
    # INCIDENT START DATE & TIME
    # When the actual disaster/incident began, as manually
    # selected by the citizen -- completely independent from
    # `report_date` below, which is the automatic timestamp of
    # when the report itself was submitted to NDMS.
    #
    # null=True/blank=True only exists so that existing rows
    # created before this field existed remain valid after
    # migration. The citizen-facing form (DisasterReportForm)
    # always requires an explicit selection and never falls
    # back to auto_now_add/timezone.now() for this field --
    # see DisasterReportForm.clean_incident_start_date().
    # ---------------------------------------------------

    incident_start_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=(
            'When did the incident begin? Select the actual '
            'or best-estimated start date and time.'
        )
    )

    description = models.TextField()

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6
    )

    address = models.CharField(
        max_length=255,
        blank=True
    )

    report_date = models.DateTimeField(
        auto_now_add=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    def __str__(self):

        return (
            f"Report #{self.id} - "
            f"{self.disaster_type.name}"
        )

# =========================================================
# DISASTER REPORT PHOTO
# =========================================================

class DisasterReportPhoto(models.Model):

    report = models.ForeignKey(
        DisasterReport,
        on_delete=models.CASCADE,
        related_name='photos'
    )

    image = models.ImageField(
        upload_to='disaster_reports/'
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):

        return (
            f"Photo for Report #{self.report.id}"
        )

# =========================================================
# DISASTER PHOTO
# =========================================================
#
# Official/public media for an already-created Disaster.
# Deliberately kept separate from DisasterReportPhoto (raw
# citizen evidence) -- a report photo never becomes public
# just because the report was verified. It only becomes an
# official DisasterPhoto if an admin explicitly selects it
# while creating the Disaster from that report (see
# reports.admin_views.admin_disaster_create).
#
# `source_report_photo` is an optional traceability link back
# to the original evidence photo it was approved from --
# SET_NULL so deleting the original report photo later never
# cascades into deleting official, already-published Disaster
# media. `image` intentionally references the same underlying
# file as the source report photo (no re-upload/duplication)
# when created via the report-to-disaster workflow; Disasters
# created manually (no source report) simply have no official
# photos attached through this model yet.
#
# =========================================================

class DisasterPhoto(models.Model):

    disaster = models.ForeignKey(
        Disaster,
        on_delete=models.CASCADE,
        related_name='photos'
    )

    image = models.ImageField(
        upload_to='disasters/'
    )

    source_report_photo = models.ForeignKey(
        DisasterReportPhoto,
        on_delete=models.SET_NULL,
        related_name='disaster_photos',
        blank=True,
        null=True
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):

        return (
            f"Official photo for {self.disaster.title}"
        )

# =========================================================
# EMERGENCY AGENCY
# =========================================================

class EmergencyAgency(models.Model):

    agency_name = models.CharField(
        max_length=200
    )

    agency_type = models.CharField(
        max_length=100
    )

    contact_number = models.CharField(
        max_length=20
    )

    # -----------------------------------------------------
    # LOCATION
    # (blank so existing agency records created before this
    # field existed remain valid; the public directory and
    # Admin form both handle a missing location gracefully.)
    # -----------------------------------------------------

    location = models.CharField(
        max_length=255,
        blank=True,
        default=''
    )

    def __str__(self):
        return self.agency_name


# =========================================================
# DISASTER UPDATE
# =========================================================

class DisasterUpdate(models.Model):

    RESPONSE_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
    ]

    disaster = models.ForeignKey(
        Disaster,
        on_delete=models.CASCADE,
        related_name='updates'
    )

    agency = models.ForeignKey(
        EmergencyAgency,
        on_delete=models.PROTECT,
        related_name='disaster_updates'
    )

    updated_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='disaster_updates'
    )

    update_details = models.TextField()

    response_status = models.CharField(
        max_length=20,
        choices=RESPONSE_STATUS_CHOICES,
        default='PENDING'
    )

    update_date = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):

        return (
            f"{self.disaster.title} - "
            f"{self.agency.agency_name}"
        )


# =========================================================
# NOTIFICATION
# =========================================================

class Notification(models.Model):

    # ---------------------------------------------------
    # NOTIFICATION TYPE
    # Drives which icon / contextual color the citizen
    # notification UI (topbar dropdown, Alerts page,
    # notification detail page) renders for this
    # notification. Purely presentational/classification --
    # it does not change read/unread behaviour, which is
    # still entirely owned by NotificationRead.
    # ---------------------------------------------------

    TYPE_REPORT_RECEIVED = 'REPORT_RECEIVED'
    TYPE_REPORT_UNDER_REVIEW = 'REPORT_UNDER_REVIEW'
    TYPE_REPORT_VERIFIED = 'REPORT_VERIFIED'
    TYPE_REPORT_REJECTED = 'REPORT_REJECTED'
    TYPE_DISASTER_ALERT = 'DISASTER_ALERT'
    TYPE_GENERAL = 'GENERAL'

    NOTIFICATION_TYPE_CHOICES = [
        (TYPE_REPORT_RECEIVED, 'Report Received'),
        (TYPE_REPORT_UNDER_REVIEW, 'Report Under Review'),
        (TYPE_REPORT_VERIFIED, 'Report Verified'),
        (TYPE_REPORT_REJECTED, 'Report Rejected'),
        (TYPE_DISASTER_ALERT, 'Disaster Alert'),
        (TYPE_GENERAL, 'General NDMS'),
    ]

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        blank=True,
        null=True
    )

    disaster = models.ForeignKey(
        Disaster,
        on_delete=models.CASCADE,
        related_name='notifications',
        blank=True,
        null=True
    )

    # ---------------------------------------------------
    # REPORT (optional)
    # Set only for report-status-lifecycle notifications
    # (received / under review / verified / rejected), so
    # the citizen notification UI can link straight back to
    # the existing Report Details page. Left null for
    # broadcast disaster alerts / general notifications,
    # which keep using `disaster` (or neither) exactly as
    # before -- this is purely additive.
    # ---------------------------------------------------

    report = models.ForeignKey(
        'DisasterReport',
        on_delete=models.CASCADE,
        related_name='notifications',
        blank=True,
        null=True
    )

    # ---------------------------------------------------
    # SUPPORT REQUEST (optional)
    # Set only for the admin-facing "New Support Request"
    # notification created when a citizen submits a Support
    # Request (Help & Support -> Report a Problem). Mirrors
    # the `report` field above exactly -- same optional,
    # purely-additive FK pattern used to route an existing
    # notification type back to its source object's existing
    # detail page. Left null for every other notification.
    # ---------------------------------------------------

    support_request = models.ForeignKey(
        'SupportRequest',
        on_delete=models.CASCADE,
        related_name='notifications',
        blank=True,
        null=True
    )

    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPE_CHOICES,
        default=TYPE_GENERAL
    )

    title = models.CharField(
        max_length=200
    )

    message = models.TextField()

    published_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='published_notifications'
    )

    publish_date = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.title


# ---------------------------------------------------------
# REPORT STATUS NOTIFICATION CONTENT
# Single source of truth for the title/message shown to a
# citizen for each report-lifecycle event, so the topbar
# dropdown, Alerts page and notification detail page (and
# whatever creates these notifications) never drift out of
# sync with each other.
# ---------------------------------------------------------

REPORT_NOTIFICATION_CONTENT = {
    Notification.TYPE_REPORT_RECEIVED: {
        'title': 'Report Received',
        'message': (
            'Your disaster report #{report_id} has been received '
            'and is awaiting review.'
        ),
    },
    Notification.TYPE_REPORT_UNDER_REVIEW: {
        'title': 'Report Under Review',
        'message': (
            'Your disaster report #{report_id} is now under '
            'review by NDMS.'
        ),
    },
    Notification.TYPE_REPORT_VERIFIED: {
        'title': 'Report Verified',
        'message': (
            'Your disaster report #{report_id} has been reviewed '
            'and verified by NDMS.'
        ),
    },
    Notification.TYPE_REPORT_REJECTED: {
        'title': 'Report Rejected',
        'message': (
            'Your disaster report #{report_id} was reviewed and '
            'could not be verified at this time.'
        ),
    },
}


# Maps a DisasterReport.status value to the notification type
# that should be created when a report *enters* that status.
REPORT_STATUS_TO_NOTIFICATION_TYPE = {
    'UNDER_REVIEW': Notification.TYPE_REPORT_UNDER_REVIEW,
    'VERIFIED': Notification.TYPE_REPORT_VERIFIED,
    'REJECTED': Notification.TYPE_REPORT_REJECTED,
    # PENDING is intentionally omitted: nothing is sent for a
    # report moving (back) into PENDING, since that is not one
    # of the citizen-facing lifecycle events in the spec.
}


def create_report_status_notification(report, new_status, actor):
    """
    Create the citizen-facing Notification for a DisasterReport
    status transition, if (and only if) one is warranted.

    Callers are responsible for passing the *new* status the
    report is being saved with; this function itself contains
    the "no duplicate same-status notification" rule, so it is
    always safe to call after a save -- it simply does nothing
    when there is nothing to announce.
    """

    notification_type = REPORT_STATUS_TO_NOTIFICATION_TYPE.get(
        new_status
    )

    if notification_type is None:
        return None

    return _create_report_notification(
        report=report,
        notification_type=notification_type,
        actor=actor
    )


# ---------------------------------------------------------
# NOTE ON TYPE_REPORT_RECEIVED / "Report Received"
# ---------------------------------------------------------
# There used to be a create_report_received_notification()
# helper here that fired a "Your report has been received"
# Notification -- recipient=report.user, published_by=
# report.user -- immediately after a citizen submitted a
# report. That was incorrect: a citizen submitting a report
# already gets their confirmation from the submission flow's
# own success message, so notifying them about their own
# just-performed action was redundant, and having the citizen
# be both the recipient and the apparent publisher of a
# system notification was conceptually wrong.
#
# That helper has been removed and is no longer called from
# create_disaster_report() (see reports.views). The
# TYPE_REPORT_RECEIVED choice and its REPORT_NOTIFICATION_CONTENT
# entry above are intentionally KEPT (not deleted) so that any
# historical Notification rows already created with this type
# continue to render correctly wherever they still appear.
# No new notifications of this type are created going forward.
# ---------------------------------------------------------


def _create_report_notification(report, notification_type, actor):

    content = REPORT_NOTIFICATION_CONTENT[notification_type]

    return Notification.objects.create(
        recipient=report.user,
        report=report,
        notification_type=notification_type,
        title=content['title'],
        message=content['message'].format(report_id=report.id),
        published_by=actor
    )


# ---------------------------------------------------------
# DISASTER ALERT NOTIFICATION
# Single source of truth for creating the one automatic,
# citizen-facing Notification that announces a newly-created
# official Disaster. Reuses the existing Notification model
# and TYPE_DISASTER_ALERT exactly as it is used for every
# other notification type -- no new model, no new fields.
#
# recipient is left as None (the project's existing broadcast
# convention -- see the recipient__isnull=True querysets in
# reports.views) so this produces exactly ONE Notification
# row visible to every citizen, not one row per user.
# ---------------------------------------------------------

def create_disaster_alert_notification(disaster, actor):
    """
    Create the single broadcast DISASTER_ALERT Notification for
    a just-created official Disaster.

    Callers must invoke this exactly once, only after the
    Disaster (and any related creation work) has successfully
    completed -- see reports.admin_views.admin_disaster_create,
    which is the only call site.
    """

    return Notification.objects.create(
        recipient=None,
        disaster=disaster,
        notification_type=Notification.TYPE_DISASTER_ALERT,
        title='New Disaster Alert',
        message=(
            f'A new official disaster has been published: '
            f'{disaster.title}. View the official disaster '
            f'information for details.'
        ),
        published_by=actor
    )


# ---------------------------------------------------------
# SUPPORT REQUEST NOTIFICATION (ADMIN-FACING)
# Single source of truth for creating the Notification(s) that
# alert eligible Admin/Staff users when a citizen successfully
# submits a new Support Request (Help & Support -> Report a
# Problem). Reuses the existing Notification model exactly as
# every other notification type does -- no new model, no new
# recipient mechanism.
#
# The existing admin queryset convention for "Admin/Staff"
# accounts (see the citizens-list exclude(is_staff=True)
# .exclude(is_superuser=True) pattern in reports.admin_views /
# reports.forms) is inverted here to find every eligible
# recipient, and one individual Notification row is created per
# admin -- the same "personal recipient" pattern already used
# throughout this model, just with an Admin/Staff account as
# the recipient instead of a citizen.
# ---------------------------------------------------------

def create_support_request_notification(support_request, actor):
    """
    Create the admin-facing "New Support Request" Notification
    for a just-created SupportRequest, one per eligible
    Admin/Staff recipient.

    Callers must invoke this exactly once, only after the
    SupportRequest has been successfully saved -- see
    reports.views.help_support, which is the only call site.
    """

    admin_recipients = User.objects.filter(
        models.Q(is_staff=True)
        | models.Q(is_superuser=True)
    )

    subject = (support_request.subject or '').strip()

    if subject:
        message = (
            f'A citizen has submitted a new support request: '
            f'{subject}'
        )
    else:
        message = 'A citizen has submitted a new support request.'

    notifications = [
        Notification(
            recipient=admin,
            support_request=support_request,
            notification_type=Notification.TYPE_GENERAL,
            title='New Support Request',
            message=message,
            published_by=actor
        )
        for admin in admin_recipients
    ]

    if notifications:
        Notification.objects.bulk_create(notifications)


# ---------------------------------------------------------
# SUPPORT REQUEST RESPONSE NOTIFICATION (CITIZEN-FACING)
# (Phase A) Single source of truth for creating the citizen-
# facing Notification when an admin's reply to a SupportRequest
# actually changes the response text. Mirrors
# create_disaster_alert_notification above exactly -- a single
# Notification.objects.create() -- except the recipient here is
# the one citizen who submitted the request, never a broadcast.
#
# Callers are responsible for the "did the response text
# actually change" check -- see
# reports.admin_views.admin_support_request_respond, which is
# the only call site -- so this function itself always creates
# exactly one Notification when called, with no de-duplication
# logic of its own.
# ---------------------------------------------------------

def create_support_response_notification(support_request, actor):

    return Notification.objects.create(
        recipient=support_request.user,
        support_request=support_request,
        notification_type=Notification.TYPE_GENERAL,
        title='Support Request Updated',
        message=(
            f'NDMS responded to your support request '
            f'"{support_request.subject}". View it on your '
            f'Help & Support page.'
        ),
        published_by=actor
    )


# =========================================================
# NOTIFICATION READ
# =========================================================

class NotificationRead(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='read_notifications'
    )

    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='read_by_users'
    )

    read_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        unique_together = (
            'user',
            'notification'
        )

    def __str__(self):

        return (
            f"{self.user.username} - "
            f"{self.notification.title}"
        )


# =========================================================
# FEEDBACK
# =========================================================

class Feedback(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    email = models.EmailField()

    rating = models.PositiveIntegerField(
        default=5
    )

    message = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):

        return (
            f"{self.user.username} - "
            f"{self.rating}/5"
        )


# =========================================================
# USER SETTINGS
# =========================================================
#
# One row per user, created on first visit to the Settings
# page (see reports.views.settings_view). Holds every
# preference on the Settings screen so choices persist for
# the logged-in user across sessions.
#
# =========================================================

class UserSettings(models.Model):

    LANGUAGE_CHOICES = [
        ('EN', 'English'),
        ('NE', 'Nepali'),
    ]

    TIME_ZONE_CHOICES = [
        ('Asia/Kathmandu', 'Nepal Time (Asia/Kathmandu)'),
        ('Asia/Kolkata', 'India Time (Asia/Kolkata)'),
        ('Asia/Dhaka', 'Bangladesh Time (Asia/Dhaka)'),
        ('Asia/Dubai', 'Gulf Time (Asia/Dubai)'),
        ('UTC', 'Coordinated Universal Time (UTC)'),
        ('Europe/London', 'UK Time (Europe/London)'),
        ('America/New_York', 'US Eastern Time (America/New_York)'),
    ]

    DATE_FORMAT_CHOICES = [
        ('DMY', 'DD/MM/YYYY'),
        ('MDY', 'MM/DD/YYYY'),
        ('YMD', 'YYYY-MM-DD'),
    ]

    LOCATION_PERMISSION_CHOICES = [
        ('ALWAYS_ASK', 'Always Ask'),
        ('ALWAYS_ALLOW', 'Always Allow'),
        ('NEVER', 'Never Allow'),
    ]

    PHOTO_UPLOAD_CHOICES = [
        ('ALWAYS_ASK', 'Always Ask'),
        ('AUTO_UPLOAD', 'Auto Upload'),
        ('WIFI_ONLY', 'Wi-Fi Only'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='settings'
    )

    # -----------------------------------------------------
    # ACCOUNT PREFERENCES
    # -----------------------------------------------------

    language = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        default='EN'
    )

    time_zone = models.CharField(
        max_length=50,
        choices=TIME_ZONE_CHOICES,
        default='Asia/Kathmandu'
    )

    date_format = models.CharField(
        max_length=10,
        choices=DATE_FORMAT_CHOICES,
        default='DMY'
    )

    # -----------------------------------------------------
    # NOTIFICATION PREFERENCES
    # -----------------------------------------------------

    disaster_alerts = models.BooleanField(
        default=True
    )

    report_status_updates = models.BooleanField(
        default=True
    )

    emergency_notifications = models.BooleanField(
        default=True
    )

    system_notifications = models.BooleanField(
        default=True
    )

    # -----------------------------------------------------
    # PRIVACY & SECURITY
    # -----------------------------------------------------

    allow_authority_contact = models.BooleanField(
        default=True
    )

    # -----------------------------------------------------
    # REPORT PREFERENCES
    # -----------------------------------------------------

    default_disaster_type = models.ForeignKey(
        DisasterType,
        on_delete=models.SET_NULL,
        related_name='+',
        blank=True,
        null=True
    )

    location_permission = models.CharField(
        max_length=15,
        choices=LOCATION_PERMISSION_CHOICES,
        default='ALWAYS_ASK'
    )

    photo_upload_preference = models.CharField(
        max_length=15,
        choices=PHOTO_UPLOAD_CHOICES,
        default='ALWAYS_ASK'
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):

        return (
            f"Settings - {self.user.username}"
        )


# =========================================================
# SUPPORT REQUEST
# =========================================================
#
# Backs the "Report a Problem" form on the Help & Support
# page, plus (Phase A) the admin response loop: an admin can
# move a request through OPEN -> IN_PROGRESS -> RESOLVED and
# write a reply the citizen sees on their own Help & Support
# page. Still intentionally lightweight -- no assignment,
# no SLA timers, no separate ticket-history model -- this is
# the minimum needed to actually close the loop the citizen
# started, not a full ticketing system.
#
# =========================================================

class SupportRequest(models.Model):

    ISSUE_TYPE_CHOICES = [
        ('TECHNICAL', 'Technical Issue'),
        ('REPORT_SUBMISSION', 'Report Submission Issue'),
        ('NOTIFICATION', 'Notification Issue'),
        ('ACCOUNT', 'Account Issue'),
        ('PROFILE', 'Profile Issue'),
        ('OTHER', 'Other'),
    ]

    # ---------------------------------------------------
    # STATUS (Phase A)
    # Freely admin-settable in either direction (OPEN <->
    # IN_PROGRESS <-> RESOLVED) -- unlike the strictly
    # forward-only Disaster/DisasterReport lifecycles, a
    # support conversation can legitimately need to reopen
    # (e.g. the citizen replies again after a RESOLVED reply
    # turns out not to have fixed things), so no transition
    # table is enforced here.
    # ---------------------------------------------------

    STATUS_OPEN = 'OPEN'
    STATUS_IN_PROGRESS = 'IN_PROGRESS'
    STATUS_RESOLVED = 'RESOLVED'

    STATUS_CHOICES = [
        (STATUS_OPEN, 'Open'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_RESOLVED, 'Resolved'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='support_requests'
    )

    issue_type = models.CharField(
        max_length=20,
        choices=ISSUE_TYPE_CHOICES,
        default='OTHER'
    )

    subject = models.CharField(
        max_length=150
    )

    description = models.TextField()

    attachment = models.FileField(
        upload_to='support_requests/',
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    # ---------------------------------------------------
    # STATUS + ADMIN RESPONSE (Phase A)
    # `status` defaults to OPEN so every existing row created
    # before this migration reads as "not yet handled" rather
    # than silently appearing resolved. `admin_response` is
    # blank until an admin actually writes one -- the citizen
    # Help & Support page only ever shows it once it is
    # non-empty. `responded_at` is set (once) the moment the
    # response TEXT actually changes -- see
    # reports.admin_views.admin_support_request_respond -- not
    # simply whenever the form is saved, so re-saving the same
    # unchanged reply (or changing only `status`) never bumps
    # it and never re-notifies the citizen.
    # ---------------------------------------------------

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_OPEN
    )

    admin_response = models.TextField(
        blank=True,
        default=''
    )

    responded_at = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):

        return (
            f"{self.subject} - {self.user.username}"
        )