"""
Presentation-only helpers that turn the signed-in citizen's saved
UserSettings preferences into (a) the root-element data attributes the
citizen CSS keys off, and (b) a single reusable date/time formatting
mechanism.

Deliberately kept as a separate module from:

  * ndms_extras.py   - navbar/avatar + disaster icon helpers
  * admin_extras.py  - the Administration side's own, independent
                       `format_admin_date` / `format_admin_datetime`
                       mechanism, which this file does not touch,
                       replace, or share state with.

Values come from the `citizen_prefs` / `citizen_date_format` context
variables published by reports.context_processors.citizen_preferences,
so nothing here queries the database.
"""

from django import template
from django.template.defaultfilters import date as django_date_filter
from django.utils import timezone as django_timezone
from django.utils.safestring import mark_safe

register = template.Library()


# =========================================================
# ROOT ELEMENT ATTRIBUTES
# =========================================================
#
# Rendered straight into <html> on every citizen/public page:
#
#     <html lang="en"{% citizen_html_attrs %}>
#
# ...producing e.g.
#
#     data-theme="dark" data-text-size="large"
#     data-motion="reduced" data-contrast="high"
#
# Because the attributes are server-rendered, the correct theme is
# present in the very first byte of HTML — there is no flash of the
# wrong theme. Only theme="SYSTEM" needs client-side resolution, which
# citizen-prefs.js does synchronously in <head> before first paint.
#
# =========================================================

_THEME_ATTR = {
    'LIGHT': 'light',
    'DARK': 'dark',
    'SYSTEM': 'system',
}

_FONT_SIZE_ATTR = {
    'STANDARD': 'standard',
    'LARGE': 'large',
}


@register.simple_tag(takes_context=True)
def citizen_html_attrs(context):
    """Render the citizen preference data-attributes for <html>."""

    prefs = context.get('citizen_prefs') or {}

    theme = _THEME_ATTR.get(
        prefs.get('theme'),
        'light'
    )

    text_size = _FONT_SIZE_ATTR.get(
        prefs.get('font_size'),
        'standard'
    )

    attrs = [
        'data-theme="%s"' % theme,
        'data-text-size="%s"' % text_size,
    ]

    # `data-theme="system"` is resolved to light/dark by
    # citizen-prefs.js; data-theme-choice keeps the original choice so
    # the script can keep following OS changes live.
    if theme == 'system':
        attrs.append('data-theme-choice="system"')

    if prefs.get('reduce_motion'):
        attrs.append('data-motion="reduced"')

    if prefs.get('high_contrast'):
        attrs.append('data-contrast="high"')

    return mark_safe(' ' + ' '.join(attrs))


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