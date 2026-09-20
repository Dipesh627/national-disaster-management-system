"""
Presentation-only helpers that turn the signed-in citizen's saved
UserSettings.date_format preference into a single reusable date/time
formatting mechanism.

Deliberately kept as a separate module from:

  * ndms_extras.py   - navbar/avatar + disaster icon helpers
  * admin_extras.py  - the Administration side's own, independent
                       `format_admin_date` / `format_admin_datetime`
                       mechanism, which this file does not touch,
                       replace, or share state with.

Values come from the `citizen_date_format` context variable published
by reports.context_processors.citizen_preferences, so nothing here
queries the database.

This module previously also rendered the root-element data
attributes (data-theme / data-text-size / data-motion / data-contrast)
that drove the Appearance/Accessibility preference layer. That layer
(citizen_html_attrs, citizen-prefs.css, citizen-prefs.js) has been
removed; it may return as a new, separately designed system in the
future.
"""

from django import template
from django.template.defaultfilters import date as django_date_filter
from django.utils import timezone as django_timezone

register = template.Library()


# =========================================================
# DATE FORMAT (Citizen Settings -> UserSettings.date_format)
# =========================================================
#
# Single reusable mechanism, mirroring the shape of the Administration
# side's format_admin_date/format_admin_datetime, so citizen templates
# never hard-code a format string:
#
#     {{ value|citizen_date:citizen_date_format }}
#     {{ value|citizen_datetime:citizen_date_format }}
#     {{ value|citizen_time }}
#
# These only change PRESENTATION. Rendering happens through Django's
# own `date` filter, which converts to the currently active timezone
# (set per request by CitizenTimezoneMiddleware) when USE_TZ=True.
# Stored values, chronological ordering, backend filtering and form
# input parsing are all completely unaffected.
#
# Unknown/missing codes fall back to DD/MM/YYYY — the project default —
# so an unset or stale preference can never raise.
#
# =========================================================

_CITIZEN_DATE_FORMAT_PATTERNS = {
    'DMY': 'd/m/Y',
    'MDY': 'm/d/Y',
    'YMD': 'Y-m-d',
}

_CITIZEN_TIME_PATTERN = 'g:i A'


def _pattern(date_format_code):
    return _CITIZEN_DATE_FORMAT_PATTERNS.get(
        date_format_code,
        'd/m/Y'
    )


def _localize(value):
    """
    Convert an aware datetime into the timezone active for this
    request (set by CitizenTimezoneMiddleware from the citizen's
    Time Zone preference).

    Django's template engine already applies template_localtime()
    to a variable before its filters run, so this is normally a
    no-op — but doing it explicitly means these filters are also
    correct when called from Python, and idempotent either way.

    Naive datetimes and plain dates are returned untouched, so
    nothing can raise on a date-only field.
    """

    if not hasattr(value, 'utcoffset'):
        return value

    if django_timezone.is_naive(value):
        return value

    try:
        return django_timezone.localtime(value)
    except Exception:
        return value


@register.filter(name='citizen_date')
def citizen_date(value, date_format_code=None):
    """Render a date/datetime using the citizen's Date Format choice."""

    if not value:
        return ''

    return django_date_filter(_localize(value), _pattern(date_format_code))


@register.filter(name='citizen_datetime')
def citizen_datetime(value, date_format_code=None):
    """Same as citizen_date, with the time of day appended."""

    if not value:
        return ''

    return django_date_filter(
        _localize(value),
        _pattern(date_format_code) + ', ' + _CITIZEN_TIME_PATTERN
    )


@register.filter(name='citizen_time')
def citizen_time(value):
    """
    Render only the time of day, in the citizen's active timezone.

    Format is intentionally independent of the Date Format preference
    (that setting describes date ordering, not clock style).
    """

    if not value:
        return ''

    return django_date_filter(_localize(value), _CITIZEN_TIME_PATTERN)