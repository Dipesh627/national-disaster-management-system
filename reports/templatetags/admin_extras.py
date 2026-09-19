"""
NDMS Admin template extras.

Presentation-only filter used by admin templates to turn a model's
status/severity value (e.g. DisasterReport.status, Disaster.severity)
into one of the shared `.badge-*` CSS classes defined in
reports/static/reports/admin/admin-components.css. Kept separate
from reports/templatetags/ndms_extras.py, which is scoped to the
public navbar/avatar UI.
"""

from django import template
from django.template.defaultfilters import date as django_date_filter
from django.utils.http import urlencode

register = template.Library()


# =========================================================
# DATE FORMAT (Admin Settings -> UserSettings.date_format)
# =========================================================
#
# Single, reusable formatting mechanism for the admin's chosen
# Date Format preference (DMY / MDY / YMD), instead of scattering
# hardcoded `|date:"..."` format strings across templates. Views
# expose the signed-in admin's current choice as `admin_date_format`
# in context (see _admin_topbar_context() in admin_views.py); any
# admin template can then do:
#
#     {{ some_datetime|format_admin_date:admin_date_format }}
#     {{ some_datetime|format_admin_datetime:admin_date_format }}
#
# Unknown/missing codes fall back to DD/MM/YYYY, the project's
# existing default, so this never raises on an unset preference.
#
# =========================================================

_ADMIN_DATE_FORMAT_PATTERNS = {
    'DMY': 'd/m/Y',
    'MDY': 'm/d/Y',
    'YMD': 'Y-m-d',
}


@register.filter(name='format_admin_date')
def format_admin_date(value, date_format_code=None):
    """Render a date/datetime using the admin's Date Format preference."""

    if not value:
        return ''

    pattern = _ADMIN_DATE_FORMAT_PATTERNS.get(
        date_format_code,
        'd/m/Y'
    )

    return django_date_filter(value, pattern)


@register.filter(name='format_admin_datetime')
def format_admin_datetime(value, date_format_code=None):
    """Same as format_admin_date, with the time of day appended."""

    if not value:
        return ''

    pattern = _ADMIN_DATE_FORMAT_PATTERNS.get(
        date_format_code,
        'd/m/Y'
    ) + ', g:i A'

    return django_date_filter(value, pattern)


# Every status/severity value used across the admin models, mapped
# to a badge color that matches its meaning (red = needs attention/
# urgent, orange = in progress/medium, green = good/resolved,
# navy = neutral/informational).
_BADGE_MAP = {

    # DisasterReport.status
    'PENDING': 'badge-orange',
    'UNDER_REVIEW': 'badge-navy',
    'VERIFIED': 'badge-green',
    'REJECTED': 'badge-red',

    # Disaster.severity
    'LOW': 'badge-green',
    'MEDIUM': 'badge-orange',
    'HIGH': 'badge-red',
    'CRITICAL': 'badge-red-solid',

    # Disaster.status
    'ACTIVE': 'badge-red',
    'UNDER_CONTROL': 'badge-orange',
    'RESOLVED': 'badge-green',
    'CLOSED': 'badge-muted',

    # DisasterUpdate.response_status
    'IN_PROGRESS': 'badge-orange',
    'COMPLETED': 'badge-green',

    # User.role
    'CITIZEN': 'badge-navy',
}


@register.filter(name='badge_class')
def badge_class(value):
    """
    Map a status/severity choice value to a `.badge-*` CSS class.

    Unknown values fall back to `badge-muted` rather than raising,
    since this only affects styling, never logic.
    """

    if not value:
        return 'badge-muted'

    return _BADGE_MAP.get(str(value).upper(), 'badge-muted')

@register.simple_tag(takes_context=True)
def querystring_without_page(context):
    """
    Re-build the current request's querystring with the `page`
    parameter removed, so pagination links can add their own
    `&page=N` without dropping the active search/filter values.

    Returns an already-encoded string with no leading `&`/`?`,
    e.g. `q=flood&status=PENDING`, or an empty string if there
    are no other parameters.
    """

    request = context.get('request')

    if request is None:
        return ''

    params = request.GET.copy()

    params.pop('page', None)

    return urlencode(params)