from django import forms

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from .models import (
    Disaster,
    DisasterReport,
    DisasterUpdate,
    Notification,
    DisasterType,
    EmergencyAgency,
    Feedback,
    UserSettings,
    SupportRequest,
)


User = get_user_model()


# =========================================================
# NEPAL GEOGRAPHIC BOUNDS
# =========================================================
#
# Mirrors NEPAL_BOUNDS in
# reports/static/reports/js/report-incident.js so the client
# and server always agree on what counts as "inside Nepal".
#
# This is a server-side safety net: the map already restricts
# selection to Nepal in the browser, but a request can always
# be forged/edited directly (e.g. via curl or browser dev
# tools), so the incident report can NEVER be trusted to save
# without this check running again on the server.
#
# =========================================================

NEPAL_BOUNDS = {
    'north': 30.45,
    'south': 26.35,
    'west': 80.05,
    'east': 88.20,
}


def is_within_nepal_bounds(latitude, longitude):
    """
    First-level (bounding-box) geographic check — fast and
    dependency-free. Kept in sync with NEPAL_BOUNDS above.
    """

    return (
        NEPAL_BOUNDS['south'] <= latitude <= NEPAL_BOUNDS['north']
        and
        NEPAL_BOUNDS['west'] <= longitude <= NEPAL_BOUNDS['east']
    )


# =========================================================
# DISASTER REPORT FORM
# =========================================================

class DisasterReportForm(forms.ModelForm):

    class Meta:

        model = DisasterReport

        fields = [
            'disaster_type',
            'reported_severity',
            'incident_start_date',
            'description',
            'latitude',
            'longitude',
            'address',
        ]

        widgets = {

            'disaster_type': forms.Select(
                attrs={
                    'class': 'form-control',
                    'id': 'id_disaster_type',
                }
            ),

            # -------------------------------------------------
            # SEVERITY -- rendered as a professional selectable
            # card/radio component in the template (looping over
            # the BoundField), NOT a plain <select>. RadioSelect
            # is used purely so real, accessible radio inputs
            # reach Django on submit -- the card styling is CSS
            # only (see .ri-severity-* in report-incident.css).
            # -------------------------------------------------

            'reported_severity': forms.RadioSelect(
                attrs={
                    'class': 'ri-severity-input',
                }
            ),

            # -------------------------------------------------
            # INCIDENT START DATE & TIME -- must start blank for
            # every new submission (no `initial`/default is set
            # anywhere for this field, on purpose). The citizen
            # manually picks it; it is never pre-filled with the
            # current time or with report_date.
            # -------------------------------------------------

            'incident_start_date': forms.DateTimeInput(
                attrs={
                    'class': 'form-control',
                    'id': 'id_incident_start_date',
                    'type': 'datetime-local',
                },
                format='%Y-%m-%dT%H:%M',
            ),

            'description': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'id': 'id_description',
                    'rows': 6,
                    'placeholder': (
                        'Describe what happened, '
                        'what you observed, and any '
                        'important information...'
                    ),
                }
            ),

            'latitude': forms.HiddenInput(
                attrs={
                    'id': 'id_latitude',
                }
            ),

            'longitude': forms.HiddenInput(
                attrs={
                    'id': 'id_longitude',
                }
            ),

            'address': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'id': 'id_address',
                    'placeholder': (
                        'Select a location on the map'
                    ),
                    'autocomplete': 'street-address',
                }
            ),
        }


    def __init__(self, *args, **kwargs):

        super().__init__(
            *args,
            **kwargs
        )

        # -----------------------------------------------------
        # ACTIVE DISASTER TYPES ONLY
        # -----------------------------------------------------

        self.fields[
            'disaster_type'
        ].queryset = (
            DisasterType.objects
            .filter(
                is_active=True
            )
            .order_by(
                'name'
            )
        )

        self.fields[
            'disaster_type'
        ].empty_label = (
            'Select disaster type'
        )

        # -----------------------------------------------------
        # LABELS
        # -----------------------------------------------------

        self.fields[
            'disaster_type'
        ].label = 'Disaster Type'

        # -------------------------------------------------
        # SEVERITY
        # No `initial` is set here on purpose -- unlike
        # Disaster.severity (which defaults to 'MEDIUM' at
        # the model level so old rows stay valid), the citizen
        # must always actively pick a level on this form. If
        # we let ModelForm pull the model field's default in
        # as `initial`, a card would appear pre-selected and
        # the required-field check below would never trigger.
        # -------------------------------------------------

        self.fields[
            'reported_severity'
        ].label = 'Incident Severity'

        self.fields[
            'reported_severity'
        ].initial = None

        self.fields[
            'reported_severity'
        ].error_messages['required'] = (
            'Please select the incident severity.'
        )

        # -------------------------------------------------
        # INCIDENT START DATE & TIME
        # The model field is null=True/blank=True purely so
        # existing (legacy) rows survive the migration -- the
        # citizen-facing form always requires an explicit
        # selection, so `required` is forced to True here
        # rather than left to follow the model field's
        # blank=True.
        # -------------------------------------------------

        self.fields[
            'incident_start_date'
        ].label = 'Incident Start Date & Time'

        self.fields[
            'incident_start_date'
        ].required = True

        self.fields[
            'incident_start_date'
        ].help_text = (
            'When did the incident begin? Select the actual '
            'or best-estimated start date and time.'
        )

        self.fields[
            'incident_start_date'
        ].error_messages['required'] = (
            'This field is required.'
        )

        self.fields[
            'description'
        ].label = 'Incident Description'

        self.fields[
            'address'
        ].label = 'Incident Location'


    # =====================================================
    # LOCATION VALIDATION
    # =====================================================

    def clean_latitude(self):

        latitude = self.cleaned_data.get(
            'latitude'
        )

        if latitude in (
            None,
            '',
        ):

            raise forms.ValidationError(
                'Please select the incident location on the map.'
            )

        return latitude


    def clean_longitude(self):

        longitude = self.cleaned_data.get(
            'longitude'
        )

        if longitude in (
            None,
            '',
        ):

            raise forms.ValidationError(
                'Please select the incident location on the map.'
            )

        return longitude


    # =====================================================
    # NEPAL-ONLY LOCATION VALIDATION
    # (server-side — the map already restricts selection to
    # Nepal in the browser, but that is only a UX convenience;
    # the request itself can be edited/replayed, so the actual
    # security boundary is enforced here, independently of any
    # client-side JavaScript.)
    # =====================================================

    def clean(self):

        cleaned_data = super().clean()

        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')

        # Only run the geographic check once both coordinates
        # have individually passed clean_latitude/clean_longitude
        # above — if either is missing, that error already
        # covers it and there is nothing valid to geo-check.

        if latitude is not None and longitude is not None:

            try:

                within_nepal = is_within_nepal_bounds(
                    float(latitude),
                    float(longitude)
                )

            except (TypeError, ValueError):

                within_nepal = False

            if not within_nepal:

                location_error = forms.ValidationError(
                    'Please select a valid location within Nepal.'
                )

                self.add_error('latitude', location_error)
                self.add_error('longitude', location_error)

        return cleaned_data


    # =====================================================
    # INCIDENT START DATE & TIME VALIDATION
    # (server-side -- the browser's own datetime-local `max`
    # restriction is only a UX convenience and can always be
    # bypassed, so the actual future-date rule is enforced
    # here, independently of any client-side JavaScript.)
    # =====================================================

    def clean_incident_start_date(self):

        incident_start_date = self.cleaned_data.get(
            'incident_start_date'
        )

        if not incident_start_date:

            raise forms.ValidationError(
                'This field is required.'
            )

        # incident_start_date is a DateTimeField on a
        # USE_TZ=True project, so this is already the
        # timezone-aware value Django parsed from the
        # submitted local datetime-local string -- compare it
        # directly against the current timezone-aware moment.

        if incident_start_date > timezone.now():

            raise forms.ValidationError(
                'Incident start date and time cannot be '
                'in the future.'
            )

        return incident_start_date


    # =====================================================
    # DESCRIPTION VALIDATION
    # =====================================================

    def clean_description(self):

        description = self.cleaned_data.get(
            'description'
        )

        if not description:

            raise forms.ValidationError(
                'Please describe the incident.'
            )

        description = description.strip()

        if len(description) < 10:

            raise forms.ValidationError(
                'Please provide a little more information '
                'about the incident.'
            )

        return description


# =========================================================
# DISASTER UPDATE FORM
# =========================================================

class DisasterUpdateForm(forms.ModelForm):

    class Meta:

        model = DisasterUpdate

        fields = [
            'disaster',
            'agency',
            'update_details',
            'response_status',
        ]


# =========================================================
# NOTIFICATION FORM
# =========================================================
#
# Backs the Admin "Send Notification" page. Reuses the
# existing Notification model as-is (no schema changes).
#
# 'recipient' is exposed as a single select: the empty
# ("All Citizens") choice means a broadcast notification, and
# the existing citizen-side alerts/notification-bell code
# already treats recipient IS NULL as broadcast, so no other
# system needs to change for this to work.
#
# 'published_by' and 'publish_date' are intentionally excluded
# — the view assigns request.user server-side on create, and
# publish_date is auto_now_add on the model.
#
# =========================================================

class NotificationForm(forms.ModelForm):

    class Meta:

        model = Notification

        fields = [
            'recipient',
            'disaster',
            'title',
            'message',
        ]

        widgets = {

            'recipient': forms.Select(
                attrs={
                    'class': 'nt-form-control',
                }
            ),

            'disaster': forms.Select(
                attrs={
                    'class': 'nt-form-control',
                }
            ),

            'title': forms.TextInput(
                attrs={
                    'class': 'nt-form-control',
                    'placeholder': 'e.g. Emergency flood warning',
                    'autocomplete': 'off',
                }
            ),

            'message': forms.Textarea(
                attrs={
                    'class': 'nt-form-control nt-form-textarea',
                    'placeholder': (
                        'Heavy rainfall is expected in the area. '
                        'Please remain alert.'
                    ),
                    'rows': 5,
                }
            ),
        }

        labels = {

            'recipient': 'Recipient',

            'disaster': 'Disaster',

            'title': 'Title',

            'message': 'Message',
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # -----------------------------------------------------
        # RECIPIENT — real citizens only, "All Citizens" (empty
        # choice) means a broadcast notification (recipient=None)
        #
        # 'CITIZEN' is currently the project's only role choice,
        # so an admin/staff account also carries role='CITIZEN'
        # by default (see admin_users() in admin_views.py).
        # Excluding staff/superuser accounts here — the same
        # convention used there — is what actually scopes this
        # selector to real, registered citizens instead of also
        # listing admin accounts.
        # -----------------------------------------------------

        self.fields['recipient'].queryset = (
            User.objects
            .filter(role='CITIZEN')
            .exclude(is_staff=True)
            .exclude(is_superuser=True)
            .order_by('full_name', 'username')
        )

        self.fields['recipient'].required = False

        self.fields['recipient'].empty_label = 'All Citizens'

        self.fields['recipient'].label_from_instance = (
            lambda citizen: (
                f"{citizen.full_name or citizen.username} "
                f"(@{citizen.username})"
            )
        )

        # -----------------------------------------------------
        # DISASTER — optional association
        # -----------------------------------------------------

        self.fields['disaster'].queryset = Disaster.objects.order_by(
            '-start_date'
        )

        self.fields['disaster'].required = False

        self.fields['disaster'].empty_label = 'No specific disaster'

    # =====================================================
    # RECIPIENT VALIDATION
    # (server-side — a citizen-only selector must never be
    # usable to target an administrative account)
    # =====================================================

    def clean_recipient(self):

        recipient = self.cleaned_data.get('recipient')

        if recipient is not None and (
            recipient.role != 'CITIZEN'
            or recipient.is_staff
            or recipient.is_superuser
        ):

            raise forms.ValidationError(
                'Selected recipient is not a citizen.'
            )

        return recipient

    # =====================================================
    # TITLE VALIDATION
    # =====================================================

    def clean_title(self):

        title = self.cleaned_data.get('title', '').strip()

        if not title:

            raise forms.ValidationError(
                'Title is required.'
            )

        return title

    # =====================================================
    # MESSAGE VALIDATION
    # =====================================================

    def clean_message(self):

        message = self.cleaned_data.get('message', '').strip()

        if not message:

            raise forms.ValidationError(
                'Message is required.'
            )

        return message


# =========================================================
# FEEDBACK FORM
# =========================================================

class FeedbackForm(forms.ModelForm):

    class Meta:

        model = Feedback

        fields = [
            'email',
            'rating',
            'message',
        ]

        widgets = {

            'email': forms.EmailInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': (
                        'Enter your email address'
                    ),
                    'required': True,
                }
            ),

            'rating': forms.HiddenInput(
                attrs={
                    'id': 'ratingValue',
                }
            ),

            'message': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'maxlength': 500,
                    'placeholder': (
                        'Tell us about your experience...'
                    ),
                    'required': True,
                }
            ),
        }

        labels = {

            'email': 'Email Address',

            'rating': 'Rating',

            'message': 'Your Feedback',
        }


    def clean_rating(self):

        rating = self.cleaned_data.get(
            'rating'
        )

        if not rating:

            raise forms.ValidationError(
                'Please select a rating.'
            )

        if rating < 1 or rating > 5:

            raise forms.ValidationError(
                'Rating must be between 1 and 5.'
            )

        return rating


# =========================================================
# PROFILE UPDATE FORM
# =========================================================
#
# NOTE:
# Only full_name, email and phone are editable by the
# citizen. username and role are intentionally NOT part of
# this form — role is system/admin controlled, and username
# is not editable for now (per project requirements).
#
# =========================================================

class ProfileUpdateForm(forms.ModelForm):

    class Meta:

        model = User

        fields = [
            'full_name',
            'email',
            'phone',
        ]

        widgets = {

            'full_name': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'id': 'id_full_name',
                    'placeholder': 'Enter your full name',
                    'autocomplete': 'name',
                }
            ),

            'email': forms.EmailInput(
                attrs={
                    'class': 'form-control',
                    'id': 'id_email',
                    'placeholder': 'Enter your email address',
                    'autocomplete': 'email',
                }
            ),

            'phone': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'id': 'id_phone',
                    'placeholder': 'Enter your phone number',
                    'autocomplete': 'tel',
                }
            ),
        }

        labels = {

            'full_name': 'Full Name',

            'email': 'Email Address',

            'phone': 'Phone Number',
        }


    # =====================================================
    # FULL NAME VALIDATION
    # =====================================================

    def clean_full_name(self):

        full_name = self.cleaned_data.get(
            'full_name',
            ''
        ).strip()

        if not full_name:

            raise forms.ValidationError(
                'Please enter your full name.'
            )

        return full_name


    # =====================================================
    # EMAIL VALIDATION
    # (must stay unique across all other accounts)
    # =====================================================

    def clean_email(self):

        email = self.cleaned_data.get(
            'email',
            ''
        ).strip()

        if not email:

            raise forms.ValidationError(
                'Please enter your email address.'
            )

        existing_user = (
            User.objects
            .filter(
                email__iexact=email
            )
            .exclude(
                pk=self.instance.pk
            )
            .exists()
        )

        if existing_user:

            raise forms.ValidationError(
                'An account with this email already exists.'
            )

        return email


# =========================================================
# AVATAR UPLOAD FORM
# =========================================================
#
# Backs the "Change Photo" modal on My Profile. Kept as its
# own small ModelForm (rather than folding "avatar" into
# ProfileUpdateForm) so the Edit Profile fields and the photo
# upload remain two independent actions/requests, matching
# how the page already separates "Edit Profile" from
# "Change Password".
#
# =========================================================

MAX_AVATAR_SIZE_BYTES = 5 * 1024 * 1024  # 5MB

ALLOWED_AVATAR_CONTENT_TYPES = [
    'image/jpeg',
    'image/png',
]


class AvatarUploadForm(forms.ModelForm):

    class Meta:

        model = User

        fields = [
            'avatar',
        ]

        widgets = {

            'avatar': forms.FileInput(
                attrs={
                    'class': 'pf-avatar-file-input',
                    'id': 'id_avatar',
                    'accept': 'image/png, image/jpeg',
                }
            ),
        }


    # =====================================================
    # AVATAR VALIDATION
    # (server-side — never trust the client-side accept/size
    # hints alone)
    # =====================================================

    def clean_avatar(self):

        avatar = self.cleaned_data.get(
            'avatar'
        )

        if not avatar:

            raise forms.ValidationError(
                'Please choose a photo to upload.'
            )

        content_type = getattr(
            avatar,
            'content_type',
            None
        )

        if (
            content_type
            and content_type not in ALLOWED_AVATAR_CONTENT_TYPES
        ):

            raise forms.ValidationError(
                'Please upload a JPG or PNG image.'
            )

        if avatar.size > MAX_AVATAR_SIZE_BYTES:

            raise forms.ValidationError(
                'Image is too large. Maximum size is 5MB.'
            )

        return avatar


# =========================================================
# CITIZEN INCIDENT REPORT PHOTO VALIDATION
# =========================================================
#
# create_disaster_report() (reports/views.py) receives report
# photos OUTSIDE of DisasterReportForm, via
# request.FILES.getlist('photos') — see the comment at that call
# site. Because there is no ModelForm field to hang a clean_*()
# method off of, this shared validator lives here instead and is
# called directly from the view, once per uploaded photo, before
# any DisasterReportPhoto row is created.
#
# Same three-layer pattern as AvatarUploadForm.clean_avatar /
# SupportRequestForm.clean_attachment / AdminDisasterForm's
# clean_official_photos: a declared content-type allow-list, a
# maximum file size, and a genuine Pillow-backed image
# re-validation (through a throwaway ImageField) — the real
# security backstop, since it runs unconditionally regardless of
# whatever Content-Type header the client did or didn't send.
# =========================================================

MAX_REPORT_PHOTO_SIZE_BYTES = 8 * 1024 * 1024  # 8MB per photo

MAX_REPORT_PHOTOS_PER_UPLOAD = 5  # unchanged from the existing limit

ALLOWED_REPORT_PHOTO_CONTENT_TYPES = [
    'image/jpeg',
    'image/png',
    'image/webp',
]


def validate_incident_report_photo(photo):
    """
    Validate a single citizen incident-report photo.

    Raises django.core.exceptions.ValidationError (forms.ValidationError
    is the same class) with a user-facing message when the photo is
    rejected. Returns None — never trusted to mutate `photo` — when it
    passes.
    """

    content_type = getattr(photo, 'content_type', None)

    if (
        content_type
        and content_type not in ALLOWED_REPORT_PHOTO_CONTENT_TYPES
    ):
        raise forms.ValidationError(
            f'"{photo.name}" is not a JPG, PNG, or WEBP image.'
        )

    if photo.size > MAX_REPORT_PHOTO_SIZE_BYTES:
        raise forms.ValidationError(
            f'"{photo.name}" is too large. Maximum size is 8MB per photo.'
        )

    image_validator = forms.ImageField()

    try:
        image_validator.clean(photo)
    except forms.ValidationError:
        raise forms.ValidationError(
            f'"{photo.name}" is not a valid image file.'
        )


# =========================================================
# =========================================================
# CITIZEN SETTINGS FORM
# =========================================================
#
# Backs the lightweight Citizen Settings page:
#   - General: Date Format, Time Zone
#   - Reporting: Default Disaster Type
#
# Reuses the existing UserSettings model. Profile information,
# notifications, and non-functional/unsupported settings (language,
# location permission, photo upload preference) are intentionally
# excluded per Phase 1 scope. Appearance (Theme/Text Size) and
# Accessibility (Reduce Motion/High Contrast) were removed —
# see UserSettings for details; they may return as a new,
# separately designed system in the future.
#
# =========================================================

class CitizenSettingsForm(forms.ModelForm):

    class Meta:

        model = UserSettings

        fields = [
            'date_format',
            'time_zone',
            'default_disaster_type',
        ]

        widgets = {

            'date_format': forms.Select(
                attrs={
                    'class': 'st-select',
                    'id': 'id_date_format',
                }
            ),

            'time_zone': forms.Select(
                attrs={
                    'class': 'st-select',
                    'id': 'id_time_zone',
                }
            ),

            'default_disaster_type': forms.Select(
                attrs={
                    'class': 'st-select',
                    'id': 'id_default_disaster_type',
                }
            ),
        }

        labels = {

            'date_format': 'Date Format',

            'time_zone': 'Time Zone',

            'default_disaster_type': 'Default Disaster Type',
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields['default_disaster_type'].queryset = (
            DisasterType.objects
            .filter(is_active=True)
            .order_by('name')
        )

        self.fields['default_disaster_type'].empty_label = (
            'Select disaster type'
        )

        self.fields['default_disaster_type'].required = False



# =========================================================
# ADMIN SETTINGS FORM
# =========================================================
#
# A smaller counterpart to CitizenSettingsForm for the Admin account
# dropdown's "Settings" page. Reuses the same UserSettings
# model (it isn't Citizen-specific), but only exposes the
# fields that make sense for an Administration account —
# General Preferences. Citizen-only report preferences
# (default disaster type, location permission, photo upload
# preference) and citizen notification toggles (disaster
# alerts, report status updates, etc.) are left out since they
# describe Citizen reporting behaviour, not Administration use
# of the system. Accessibility (Reduce Motion/High Contrast/
# Font Size) was removed — see UserSettings for details; it
# may return as a new, separately designed system in the
# future.
#
# =========================================================

class AdminSettingsForm(forms.ModelForm):

    class Meta:

        model = UserSettings

        fields = [
            'language',
            'time_zone',
            'date_format',
        ]

        widgets = {

            'language': forms.Select(
                attrs={
                    'class': 'ads-select',
                    'id': 'id_language',
                }
            ),

            'time_zone': forms.Select(
                attrs={
                    'class': 'ads-select',
                    'id': 'id_time_zone',
                }
            ),

            'date_format': forms.Select(
                attrs={
                    'class': 'ads-select',
                    'id': 'id_date_format',
                }
            ),
        }

        labels = {

            'language': 'Language',

            'time_zone': 'Time Zone',

            'date_format': 'Date Format',
        }

    # =====================================================
    # LANGUAGE — ONLY EXPOSE WHAT THE PROJECT ACTUALLY SUPPORTS
    # =====================================================
    #
    # UserSettings.LANGUAGE_CHOICES also lists 'NE' (Nepali), but
    # this project has no
    # Django i18n content (no {% trans %}/{% blocktrans %} tags,
    # no .po files, no LocaleMiddleware) — so a Nepali interface
    # does not actually exist anywhere yet. Restricting the
    # Admin language selector to the choice that is genuinely
    # functional avoids a switcher that saves a value but
    # changes nothing, per the Admin Settings requirements.
    #
    # =====================================================

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields['language'].choices = [
            choice
            for choice in UserSettings.LANGUAGE_CHOICES
            if choice[0] == 'EN'
        ]

        self.fields['language'].help_text = (
            'English is currently the only fully '
            'supported administration interface language.'
        )


# =========================================================
# ADMIN DISASTER TYPE FORM
# =========================================================
#
# Backs the Add/Edit Disaster Type admin pages. Name is
# required and must be unique case-insensitively so citizens
# and admins never see near-duplicate categories (e.g.
# "Flood" and "flood").
#
# =========================================================

class AdminDisasterTypeForm(forms.ModelForm):

    class Meta:

        model = DisasterType

        fields = [
            'name',
            'description',
            'is_active',
        ]

        widgets = {

            'name': forms.TextInput(
                attrs={
                    'class': 'dt-form-control',
                    'placeholder': 'e.g. Flood, Landslide, Earthquake',
                }
            ),

            'description': forms.Textarea(
                attrs={
                    'class': 'dt-form-control dt-form-textarea',
                    'rows': 4,
                    'placeholder': (
                        'Briefly explain what this category represents.'
                    ),
                }
            ),

            'is_active': forms.CheckboxInput(
                attrs={
                    'class': 'dt-toggle-input',
                }
            ),
        }

    def clean_name(self):

        name = self.cleaned_data.get('name', '').strip()

        if not name:
            raise forms.ValidationError(
                'Disaster type name is required.'
            )

        duplicate = DisasterType.objects.filter(
            name__iexact=name
        )

        if self.instance and self.instance.pk:
            duplicate = duplicate.exclude(
                pk=self.instance.pk
            )

        if duplicate.exists():
            raise forms.ValidationError(
                'A disaster type with this name already exists.'
            )

        return name


# =========================================================
# ADMIN EMERGENCY AGENCY FORM
# =========================================================
#
# Backs the Add/Edit Emergency Agency admin pages. Mirrors
# AdminDisasterTypeForm's structure/conventions: agency name
# is required and must be unique case-insensitively so admins
# never see near-duplicate agencies (e.g. "Nepal Police" and
# "nepal police").
#
# =========================================================

class AdminEmergencyAgencyForm(forms.ModelForm):

    class Meta:

        model = EmergencyAgency

        fields = [
            'agency_name',
            'agency_type',
            'contact_number',
            'location',
        ]

        widgets = {

            'agency_name': forms.TextInput(
                attrs={
                    'class': 'ea-form-control',
                    'placeholder': 'e.g. Nepal Police',
                    'autocomplete': 'off',
                }
            ),

            'agency_type': forms.TextInput(
                attrs={
                    'class': 'ea-form-control',
                    'placeholder': 'e.g. Security, Emergency Response',
                    'autocomplete': 'off',
                }
            ),

            'contact_number': forms.TextInput(
                attrs={
                    'class': 'ea-form-control',
                    'placeholder': 'e.g. 100 or +977-1-5970000',
                    'autocomplete': 'off',
                }
            ),

            'location': forms.TextInput(
                attrs={
                    'class': 'ea-form-control',
                    'placeholder': 'e.g. Naxal, Kathmandu',
                    'autocomplete': 'off',
                }
            ),
        }

        labels = {

            'agency_name': 'Agency Name',

            'agency_type': 'Agency Type',

            'contact_number': 'Contact Number',

            'location': 'Location',
        }

    def clean_agency_name(self):

        agency_name = self.cleaned_data.get('agency_name', '').strip()

        if not agency_name:
            raise forms.ValidationError(
                'Agency name is required.'
            )

        duplicate = EmergencyAgency.objects.filter(
            agency_name__iexact=agency_name
        )

        if self.instance and self.instance.pk:
            duplicate = duplicate.exclude(
                pk=self.instance.pk
            )

        if duplicate.exists():
            raise forms.ValidationError(
                'An emergency agency with this name already exists.'
            )

        return agency_name

    def clean_agency_type(self):

        agency_type = self.cleaned_data.get('agency_type', '').strip()

        if not agency_type:
            raise forms.ValidationError(
                'Agency type is required.'
            )

        return agency_type

    def clean_contact_number(self):

        contact_number = self.cleaned_data.get('contact_number', '').strip()

        if not contact_number:
            raise forms.ValidationError(
                'Contact number is required.'
            )

        return contact_number

    def clean_location(self):

        # Optional: existing agencies were created before this field
        # existed, so it must never be required at the form level —
        # just normalized (trimmed) when provided.
        location = self.cleaned_data.get('location', '').strip()

        return location


# =========================================================
# ADMIN RESPONSE UPDATE FORM
# =========================================================
#
# Backs the Add/Edit Response Update admin pages. Mirrors
# AdminEmergencyAgencyForm / AdminDisasterTypeForm's
# structure/conventions.
#
# 'updated_by' and 'update_date' are intentionally excluded —
# the view assigns request.user server-side on create, and
# update_date is auto_now_add on the model.
#
# =========================================================

class AdminResponseUpdateForm(forms.ModelForm):

    class Meta:

        model = DisasterUpdate

        fields = [
            'disaster',
            'agency',
            'update_details',
            'response_status',
        ]

        widgets = {

            'disaster': forms.Select(
                attrs={
                    'class': 'ru-form-control',
                }
            ),

            'agency': forms.Select(
                attrs={
                    'class': 'ru-form-control',
                }
            ),

            'update_details': forms.Textarea(
                attrs={
                    'class': 'ru-form-control ru-form-textarea',
                    'placeholder': (
                        'Describe the response action taken, e.g. '
                        '"Rescue operation started at Ward 5..."'
                    ),
                    'rows': 5,
                }
            ),

            'response_status': forms.Select(
                attrs={
                    'class': 'ru-form-control',
                }
            ),
        }

        labels = {

            'disaster': 'Disaster',

            'agency': 'Emergency Agency',

            'update_details': 'Update Details',

            'response_status': 'Response Status',
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields['disaster'].queryset = Disaster.objects.order_by(
            'title'
        )

        self.fields['disaster'].empty_label = 'Select disaster'

        self.fields['agency'].queryset = EmergencyAgency.objects.order_by(
            'agency_name'
        )

        self.fields['agency'].empty_label = 'Select agency'

    def clean_disaster(self):

        disaster = self.cleaned_data.get('disaster')

        # A CLOSED disaster is a finalized historical record —
        # never a valid target for a *new* response update, and
        # never a valid target to re-point an *existing* update
        # to either. (Mutating an update that already belongs to
        # a closed disaster is blocked separately, at the view
        # level in admin_response_update_edit/delete, before this
        # form is ever built.)
        if disaster is not None and disaster.status == 'CLOSED':
            raise forms.ValidationError(
                'This disaster is closed. Response updates cannot '
                'be added to a closed disaster.'
            )

        return disaster

    def clean_update_details(self):

        update_details = self.cleaned_data.get(
            'update_details', ''
        ).strip()

        if not update_details:
            raise forms.ValidationError(
                'Update details are required.'
            )

        return update_details


# =========================================================
# MULTIPLE FILE FIELD
# =========================================================
#
# Django's built-in forms.FileField only ever cleans a single
# uploaded file. The "Official Disaster Photos" picker on the
# manual Add Disaster page needs multiple files from one <input
# type="file" multiple>, so this is the standard Django recipe
# for that: a widget that allows multiple selection, paired
# with a field whose clean() runs the normal single-file
# clean() over every file in the list. Nothing else about
# FileField's behaviour (validators, required handling, etc.)
# is changed.
# =========================================================

class MultipleFileInput(forms.ClearableFileInput):

    allow_multiple_selected = True


class MultipleFileField(forms.FileField):

    def __init__(self, *args, **kwargs):

        kwargs.setdefault('widget', MultipleFileInput())

        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):

        single_file_clean = super().clean

        if isinstance(data, (list, tuple)):

            result = [
                single_file_clean(uploaded_file, initial)
                for uploaded_file in data
            ]

        else:

            result = single_file_clean(data, initial)

        return result


# =========================================================
# ADMIN DISASTER FORM
# =========================================================
#
# Backs the admin Add/Edit Disaster pages. Shares NEPAL_BOUNDS
# / is_within_nepal_bounds with DisasterReportForm above so the
# server-side geographic check always agrees with the citizen-
# facing one, instead of duplicating/forking that logic.
#
# Location (latitude/longitude) is only REQUIRED when creating
# a new disaster (is_create=True, passed in from the view).
# Existing disasters created before location fields existed may
# have blank coordinates — editing them does not suddenly force
# a location to be supplied.
#
# OFFICIAL DISASTER PHOTOS
# `official_photos` is intentionally NOT a model field — it
# backs the manual "Add Disaster" photo upload only (see
# reports.admin_views.admin_disaster_create). It is declared
# here (rather than only in the create view) so the same
# server-side validation always runs regardless of how the form
# is submitted, but it is only ever rendered on the manual
# create page (reports/admin/disaster_form.html gates the
# section on `not is_edit and not source_report`) and only ever
# saved as DisasterPhoto records for that same manual-create,
# no-source-report path. Editing a disaster, and creating one
# from a verified report, never touch this field.
# =========================================================

MAX_DISASTER_PHOTO_SIZE_BYTES = 8 * 1024 * 1024  # 8MB per photo

MAX_DISASTER_PHOTOS_PER_UPLOAD = 10

ALLOWED_DISASTER_PHOTO_CONTENT_TYPES = [
    'image/jpeg',
    'image/png',
    'image/webp',
]


class AdminDisasterForm(forms.ModelForm):

    official_photos = MultipleFileField(
        required=False,
        label='Official Disaster Photos',
        widget=MultipleFileInput(
            attrs={
                'class': 'ds-photo-upload-input',
                'accept': 'image/png, image/jpeg, image/webp',
                'data-max-photos': str(MAX_DISASTER_PHOTOS_PER_UPLOAD),
                'data-max-size-bytes': str(MAX_DISASTER_PHOTO_SIZE_BYTES),
            }
        ),
    )

    class Meta:

        model = Disaster

        fields = [
            'disaster_type',
            'title',
            'severity',
            'status',
            'start_date',
            'description',
            'latitude',
            'longitude',
            'address',
        ]

        widgets = {

            'disaster_type': forms.Select(
                attrs={
                    'class': 'ds-form-control',
                }
            ),

            'title': forms.TextInput(
                attrs={
                    'class': 'ds-form-control',
                    'placeholder': 'e.g. Kathmandu Valley Flooding',
                    'maxlength': 200,
                }
            ),

            'severity': forms.Select(
                attrs={
                    'class': 'ds-form-control',
                }
            ),

            'status': forms.Select(
                attrs={
                    'class': 'ds-form-control',
                }
            ),

            'start_date': forms.DateTimeInput(
                attrs={
                    'class': 'ds-form-control',
                    'type': 'datetime-local',
                },
                format='%Y-%m-%dT%H:%M',
            ),

            'description': forms.Textarea(
                attrs={
                    'class': 'ds-form-control ds-form-textarea',
                    'placeholder': (
                        'Describe the disaster, its scale, and '
                        'any important details...'
                    ),
                    'rows': 6,
                }
            ),

            'latitude': forms.HiddenInput(),

            'longitude': forms.HiddenInput(),

            'address': forms.TextInput(
                attrs={
                    'class': 'ds-form-control',
                    'placeholder': 'Select a location on the map',
                    'autocomplete': 'off',
                }
            ),
        }

        labels = {

            'disaster_type': 'Disaster Type',
            'title': 'Disaster Title',
            'severity': 'Severity',
            'status': 'Status',
            'start_date': 'Start Date & Time',
            'description': 'Description',
            'address': 'Address',
        }


    def __init__(self, *args, is_create=False, from_report=False, **kwargs):

        self.is_create = is_create

        # True only when this create-form is being used for the
        # "Create Disaster from this Report" workflow (see
        # admin_disaster_create) -- as opposed to a normal manual
        # "Add Disaster". Controls whether start_date is real,
        # admin-editable prefilled data (from the report) or a
        # purely-cosmetic field the server always overwrites with
        # the current time.
        self.from_report = from_report

        super().__init__(*args, **kwargs)

        # Active disaster types, plus the currently selected
        # type even if it has since been deactivated (so an
        # existing disaster's type is never silently dropped
        # from the dropdown while editing).
        self.fields['disaster_type'].queryset = (
            DisasterType.objects
            .filter(
                Q(is_active=True)
                | Q(pk=self.instance.disaster_type_id)
            )
            .order_by('name')
        )

        self.fields['disaster_type'].empty_label = (
            'Select disaster type'
        )

        if is_create:

            self.fields['severity'].initial = 'MEDIUM'
            self.fields['status'].initial = 'ACTIVE'

            if self.from_report:

                # Creating from a verified report: start_date is
                # real, meaningful data -- prefilled from the
                # report's own incident_start_date by
                # admin_disaster_create, and the admin must be able
                # to review/edit it before the Disaster is created.
                # The server trusts (and requires) this submitted
                # value in this workflow only.
                self.fields['start_date'].required = True

            else:

                # Manual "Add Disaster": the visible start date/time
                # shown to the admin is "now" (filled in by JS in
                # disaster_form.html) purely for display — the
                # server always overwrites start_date with
                # timezone.now() on create (see
                # admin_disaster_create), so this field does not
                # need to be submitted at all.
                self.fields['start_date'].required = False
                self.fields['start_date'].widget.attrs['readonly'] = True

            # Location is required only for NEW disasters.
            self.fields['latitude'].required = True
            self.fields['longitude'].required = True

        else:

            # Editing: never force a location onto a legacy
            # disaster that never had one.
            self.fields['latitude'].required = False
            self.fields['longitude'].required = False

            # ---------------------------------------------------
            # STATUS — NOT EDITABLE THROUGH THIS FORM
            # Disaster status changes must always go through the
            # dedicated, validated lifecycle transition action
            # (see admin_disaster_update_status / the Disaster
            # Detail page), which enforces the ACTIVE ->
            # UNDER_CONTROL -> RESOLVED -> CLOSED chain and
            # rejects anything else server-side.
            #
            # disabled=True is enforced by Django itself, not by
            # hiding a button: a disabled field always validates
            # using its *initial* (current) value, no matter what
            # a tampered/crafted POST body contains, so this form
            # can never be used to bypass the transition chain.
            # ---------------------------------------------------
            self.fields['status'].disabled = True


    def clean_title(self):

        title = self.cleaned_data.get('title', '').strip()

        if not title:
            raise forms.ValidationError(
                'Please enter a disaster title.'
            )

        return title


    def clean_start_date(self):

        start_date = self.cleaned_data.get('start_date')

        # Only the report-based creation workflow relies on this
        # check (required=True is already set only in that case) --
        # never silently fall back to "now" when the report itself
        # had no recorded incident start date.
        if self.is_create and self.from_report and not start_date:
            raise forms.ValidationError(
                'Please provide the incident start date and time.'
            )

        return start_date


    def clean_latitude(self):

        latitude = self.cleaned_data.get('latitude')

        if self.is_create and latitude in (None, ''):
            raise forms.ValidationError(
                'Please select the disaster location on the map.'
            )

        return latitude


    def clean_longitude(self):

        longitude = self.cleaned_data.get('longitude')

        if self.is_create and longitude in (None, ''):
            raise forms.ValidationError(
                'Please select the disaster location on the map.'
            )

        return longitude


    # =====================================================
    # OFFICIAL DISASTER PHOTOS VALIDATION
    # (server-side — never trust the client-side accept/size
    # hints alone, same pattern as AvatarUploadForm.clean_avatar
    # / SupportRequestForm.clean_attachment above)
    # =====================================================

    def clean_official_photos(self):

        photos = self.cleaned_data.get('official_photos') or []

        if not photos:
            return []

        if len(photos) > MAX_DISASTER_PHOTOS_PER_UPLOAD:
            raise forms.ValidationError(
                'You can upload up to '
                f'{MAX_DISASTER_PHOTOS_PER_UPLOAD} photos at once.'
            )

        # A throwaway ImageField reuses Django's own image
        # validation (Pillow-verifies the file is a genuine,
        # uncorrupted image) instead of trusting the browser-
        # supplied content type / file extension alone.
        image_validator = forms.ImageField()

        for photo in photos:

            content_type = getattr(photo, 'content_type', None)

            if (
                content_type
                and content_type
                not in ALLOWED_DISASTER_PHOTO_CONTENT_TYPES
            ):
                raise forms.ValidationError(
                    f'"{photo.name}" is not a JPG, PNG, or WEBP '
                    'image.'
                )

            if photo.size > MAX_DISASTER_PHOTO_SIZE_BYTES:
                raise forms.ValidationError(
                    f'"{photo.name}" is too large. Maximum size '
                    'is 8MB per photo.'
                )

            try:
                image_validator.clean(photo)
            except forms.ValidationError:
                raise forms.ValidationError(
                    f'"{photo.name}" is not a valid image file.'
                )

        return photos


    def clean(self):

        cleaned_data = super().clean()

        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')

        # Only geo-check when both coordinates are present —
        # editing a legacy disaster with no location at all
        # should not be blocked by this check.
        if latitude is not None and longitude is not None:

            try:

                within_nepal = is_within_nepal_bounds(
                    float(latitude),
                    float(longitude)
                )

            except (TypeError, ValueError):

                within_nepal = False

            if not within_nepal:

                location_error = forms.ValidationError(
                    'Please select a valid location within Nepal.'
                )

                self.add_error('latitude', location_error)
                self.add_error('longitude', location_error)

        return cleaned_data


# =========================================================
# SUPPORT REQUEST FORM
# =========================================================
#
# Backs the "Report a Problem" form on the Help & Support
# page. Attachment is optional; validated the same way as
# AvatarUploadForm.clean_avatar — never trust the client-side
# accept/size hints alone.
#
# =========================================================

MAX_SUPPORT_ATTACHMENT_SIZE_BYTES = 5 * 1024 * 1024  # 5MB

ALLOWED_SUPPORT_ATTACHMENT_CONTENT_TYPES = [
    'image/jpeg',
    'image/png',
    'application/pdf',
]


class SupportRequestForm(forms.ModelForm):

    class Meta:

        model = SupportRequest

        fields = [
            'issue_type',
            'subject',
            'description',
            'attachment',
        ]

        widgets = {

            'issue_type': forms.Select(
                attrs={
                    'class': 'hs-select',
                    'id': 'id_issue_type',
                }
            ),

            'subject': forms.TextInput(
                attrs={
                    'class': 'hs-input',
                    'id': 'id_subject',
                    'placeholder': (
                        'Briefly describe the issue'
                    ),
                    'maxlength': 150,
                }
            ),

            'description': forms.Textarea(
                attrs={
                    'class': 'hs-textarea',
                    'id': 'id_description',
                    'rows': 5,
                    'placeholder': (
                        'Explain what happened, what you '
                        'expected, and any steps to '
                        'reproduce the issue...'
                    ),
                }
            ),

            'attachment': forms.FileInput(
                attrs={
                    'class': 'hs-file-input',
                    'id': 'id_attachment',
                    'accept': (
                        'image/png, image/jpeg, '
                        'application/pdf'
                    ),
                }
            ),
        }

        labels = {

            'issue_type': 'Issue Type',

            'subject': 'Subject',

            'description': 'Description',

            'attachment': 'Attachment',
        }


    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields['issue_type'].empty_label = (
            'Select issue type'
        )

        self.fields['attachment'].required = False


    # =====================================================
    # SUBJECT VALIDATION
    # =====================================================

    def clean_subject(self):

        subject = self.cleaned_data.get(
            'subject',
            ''
        ).strip()

        if not subject:

            raise forms.ValidationError(
                'Please enter a subject.'
            )

        return subject


    # =====================================================
    # DESCRIPTION VALIDATION
    # =====================================================

    def clean_description(self):

        description = self.cleaned_data.get(
            'description',
            ''
        ).strip()

        if not description:

            raise forms.ValidationError(
                'Please describe the problem.'
            )

        return description


    # =====================================================
    # ATTACHMENT VALIDATION
    # (server-side — never trust the client-side accept/size
    # hints alone)
    # =====================================================

    def clean_attachment(self):

        attachment = self.cleaned_data.get(
            'attachment'
        )

        if not attachment:

            return attachment

        if attachment.size > MAX_SUPPORT_ATTACHMENT_SIZE_BYTES:

            raise forms.ValidationError(
                'File is too large. Maximum size is 5MB.'
            )

        content_type = getattr(
            attachment,
            'content_type',
            None
        )

        # -------------------------------------------------
        # A declared PDF is verified against the real file
        # signature (magic bytes) rather than trusted on the
        # Content-Type header alone — a renamed/relabelled
        # non-PDF file is rejected here even if the browser
        # claimed "application/pdf".
        # -------------------------------------------------

        if content_type == 'application/pdf':

            header = attachment.read(5)
            attachment.seek(0)

            if header != b'%PDF-':

                raise forms.ValidationError(
                    'This does not look like a valid PDF file.'
                )

            return attachment

        # -------------------------------------------------
        # Anything declared as an image, OR with NO Content-Type
        # at all (an absent header must never be treated as a
        # free pass — that would let any file through simply by
        # omitting it), is Pillow-verified as a genuine,
        # uncorrupted image the same way avatars/report photos
        # are. Any other declared type is rejected outright.
        # -------------------------------------------------

        if content_type in ('image/jpeg', 'image/png') or not content_type:

            image_validator = forms.ImageField()

            try:
                image_validator.clean(attachment)
            except forms.ValidationError:
                raise forms.ValidationError(
                    'Please upload a JPG, PNG, or PDF file.'
                )

            return attachment

        raise forms.ValidationError(
            'Please upload a JPG, PNG, or PDF file.'
        )


# =========================================================
# ADMIN SUPPORT REQUEST RESPONSE FORM (Phase A)
# =========================================================
#
# Backs the Status + Response panel on the Admin Support
# Request Detail page. Deliberately just the two fields an
# admin actually sets here -- everything else about a
# SupportRequest (who submitted it, the issue type/subject/
# description/attachment) is citizen-authored and untouched
# by this form.
#
# =========================================================

class AdminSupportRequestResponseForm(forms.ModelForm):

    class Meta:

        model = SupportRequest

        fields = [
            'status',
            'admin_response',
        ]

        widgets = {

            'status': forms.Select(
                attrs={
                    'class': 'sr-select',
                }
            ),

            'admin_response': forms.Textarea(
                attrs={
                    'class': 'sr-textarea',
                    'placeholder': (
                        'Write a reply the citizen will see on '
                        'their Help & Support page...'
                    ),
                    'rows': 5,
                }
            ),
        }

        labels = {

            'status': 'Status',

            'admin_response': 'Response to Citizen',
        }


    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields['admin_response'].required = False


    # =====================================================
    # RESPONSE VALIDATION
    # A request cannot be marked RESOLVED with no response --
    # the citizen would otherwise see their request flip to
    # "Resolved" with nothing explaining why. Every other
    # status (OPEN, IN_PROGRESS) may be set with or without a
    # response, e.g. to just signal "we're looking into it"
    # before a full reply is ready.
    # =====================================================

    def clean(self):

        cleaned_data = super().clean()

        status = cleaned_data.get('status')

        admin_response = (
            cleaned_data.get('admin_response') or ''
        ).strip()

        cleaned_data['admin_response'] = admin_response

        if status == SupportRequest.STATUS_RESOLVED and not admin_response:

            self.add_error(
                'admin_response',
                'Please write a response before marking this '
                'request as Resolved.'
            )

        return cleaned_data