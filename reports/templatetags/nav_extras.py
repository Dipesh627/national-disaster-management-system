"""
NDMS navbar data.

Read-only data for the public navbar's "Disasters" and "Agencies"
dropdowns. Both lists come straight from the database (the same
DisasterType / EmergencyAgency rows the public pages already use),
so nothing in the menu is hard-coded.

    {% load nav_extras %}
    {% nav_menu_data as nav_menu %}
    {% for dt in nav_menu.disaster_types %} ... {% endfor %}
    {% for t in nav_menu.agency_types %} ... {% endfor %}

Staff/superuser accounts never see these dropdowns (the isolation
middleware blocks those pages for them), so no queries are run.
The result is cached on the request, so a page that renders the
navbar twice still costs one pair of queries.
"""

from django import template

register = template.Library()

_CACHE_ATTR = '_ndms_nav_menu_data'

# Keep the dropdowns compact; the full lists live on their own pages.
MAX_DISASTER_TYPES = 8
MAX_AGENCY_TYPES = 6


@register.simple_tag(takes_context=True)
def nav_menu_data(context):

    request = context.get('request')

    cached = getattr(request, _CACHE_ATTR, None)

    if cached is not None:
        return cached

    data = {
        'disaster_types': [],
        'agency_types': [],
    }

    user = getattr(request, 'user', None)

    is_admin_account = (
        user is not None
        and user.is_authenticated
        and (user.is_staff or user.is_superuser)
    )

    if not is_admin_account:

        # Local import: keeps this module importable before the app
        # registry is ready (same pattern as context_processors.py).
        from ..models import DisasterType, EmergencyAgency

        data['disaster_types'] = list(
            DisasterType.objects
            .filter(is_active=True)
            .order_by('name')[:MAX_DISASTER_TYPES]
        )

        data['agency_types'] = list(
            EmergencyAgency.objects
            .exclude(agency_type='')
            .order_by('agency_type')
            .values_list('agency_type', flat=True)
            .distinct()[:MAX_AGENCY_TYPES]
        )

    if request is not None:
        setattr(request, _CACHE_ATTR, data)

    return data
