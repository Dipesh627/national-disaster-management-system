"""
NDMS Citizen preference plumbing (Phase 2).

ONE place where the signed-in citizen's UserSettings row is read per
request, and ONE place where it is exposed to every citizen template.
Views must NOT re-query UserSettings just to render preferences.

    request.user
        -> get_citizen_preferences(request)      (cached on request)
        -> citizen_preferences() context processor
        -> citizen_date_format / citizen_time_zone
        -> {{ value|citizen_date:citizen_date_format }} and friends
           (reports.templatetags.citizen_extras)

Appearance (Theme/Text Size) and Accessibility (Reduce Motion/High
Contrast) preferences, and the citizen-prefs.css/.js layer that
applied them, were removed — they may return as a new, separately
designed system in the future.

ADMIN ISOLATION
---------------
Staff/superuser accounts are deliberately excluded here. Their
date/timezone preferences are already driven by the Admin Settings
mechanism (AdminSettingsForm + AdminTimezoneMiddleware +
`admin_date_format` from _admin_topbar_context()), and that
implementation is left completely untouched. Anonymous visitors and
admins both receive the project defaults below, so no user-specific
value can ever leak.
"""

from django.conf import settings as django_settings
from django.db.models import Q


# Project defaults — used for anonymous visitors, admin accounts, and
# as a safe fallback if the settings row cannot be read for any reason.
CITIZEN_PREFERENCE_DEFAULTS = {
    'date_format': 'DMY',
    'time_zone': django_settings.TIME_ZONE,
    'is_citizen': False,
}


# Cache key stashed on the request object so that the context
# processor, the middleware and any view that needs the values all
# share a single database query per request.
_REQUEST_CACHE_ATTR = '_ndms_citizen_preferences'


def _is_citizen_request(request):
    """True only for an authenticated, non-staff, non-superuser user."""

    user = getattr(request, 'user', None)

    if user is None or not user.is_authenticated:
        return False

    if user.is_staff or user.is_superuser:
        return False

    return True


def get_citizen_preferences(request):
    """
    Return the effective citizen preferences for this request.

    Result is cached on the request, so calling this from the
    middleware AND the context processor AND a view costs one query.
    """

    cached = getattr(request, _REQUEST_CACHE_ATTR, None)

    if cached is not None:
        return cached

    prefs = dict(CITIZEN_PREFERENCE_DEFAULTS)

    if _is_citizen_request(request):

        # Local import: keeps this module importable before the app
        # registry is ready (same pattern as reports/middleware.py).
        from .models import UserSettings

        user_settings = (
            UserSettings.objects
            .filter(user=request.user)
            .only(
                'date_format',
                'time_zone',
            )
            .first()
        )

        if user_settings is not None:
            prefs.update({
                'date_format': user_settings.date_format or 'DMY',
                'time_zone': (
                    user_settings.time_zone
                    or django_settings.TIME_ZONE
                ),
            })

        prefs['is_citizen'] = True

    setattr(request, _REQUEST_CACHE_ATTR, prefs)

    return prefs


def citizen_preferences(request):
    """
    Template context processor.

    Exposes:
        citizen_prefs        - full dict (see above)
        citizen_date_format  - 'DMY' | 'MDY' | 'YMD'
        citizen_time_zone    - IANA zone name currently applied
    """

    prefs = get_citizen_preferences(request)

    return {
        'citizen_prefs': prefs,
        'citizen_date_format': prefs['date_format'],
        'citizen_time_zone': prefs['time_zone'],
    }


# =========================================================
# DISASTER UNREAD RED-DOT INDICATOR
# =========================================================
#
# Single source of truth for "does this citizen have at least
# one unread DISASTER_ALERT notification". Reuses the existing
# Notification / NotificationRead models exactly as they are
# used everywhere else (dashboard(), alerts(), etc.) — no new
# model, no new field, no separate red-dot state.
#
# Cached on the request the same way get_citizen_preferences()
# is, so the public navbar, the Disasters dropdown and the
# Dashboard sidebar all share ONE query per request instead of
# each running their own.
# =========================================================

_DISASTER_ALERT_CACHE_ATTR = '_ndms_has_unread_disaster_alert'


def get_has_unread_disaster_alert(request):
    """
    Return True if the signed-in citizen has at least one unread
    DISASTER_ALERT notification, False otherwise.

    Always False for anonymous visitors and for staff/superuser
    (Admin) accounts — this indicator is citizen-only, exactly
    like the rest of this module's preferences.
    """

    cached = getattr(request, _DISASTER_ALERT_CACHE_ATTR, None)

    if cached is not None:
        return cached

    result = False

    if _is_citizen_request(request):

        # Local import: keeps this module importable before the
        # app registry is ready (same pattern used above).
        from .models import Notification, NotificationRead

        read_ids = (
            NotificationRead.objects
            .filter(user=request.user)
            .values_list('notification_id', flat=True)
        )

        result = (
            Notification.objects
            .filter(
                Q(recipient=request.user) | Q(recipient__isnull=True),
                notification_type=Notification.TYPE_DISASTER_ALERT,
            )
            .exclude(id__in=read_ids)
            .exists()
        )

    setattr(request, _DISASTER_ALERT_CACHE_ATTR, result)

    return result


def disaster_alert_status(request):
    """
    Template context processor.

    Exposes:
        has_unread_disaster_alert - True/False, for the public
            navbar, the Disasters dropdown, and the Dashboard
            sidebar to all render the same small red-dot state.
    """

    return {
        'has_unread_disaster_alert': get_has_unread_disaster_alert(request),
    }