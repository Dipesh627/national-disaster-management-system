"""
NDMS Emergency Agency template extras.

Small, presentation-only template filter used by the public
Emergency Agencies directory (reports/emergency_agencies.html) to
build a mobile-friendly `tel:` link from a stored
EmergencyAgency.contact_number value. This never changes what is
displayed to the user — only the href used by the "Call Agency"
action — and never invents or guesses a number: it only reformats
whatever digits/`+` are already in the real, admin-entered value.
"""

import re

from django import template

register = template.Library()


@register.filter(name='tel_href')
def tel_href(value):
    """
    Return a `tel:`-scheme value safe to use in an <a href="..."> for
    a stored contact number such as "100" or "+977-1-5970000".

    Keeps only digits and a single leading "+" (tel: URIs ignore
    spaces/dashes/parentheses anyway, but stripping them here keeps
    the href clean). Returns '' for an empty/whitespace-only value so
    templates can still gate the Call Agency button on the ORIGINAL
    field (`{% if agency.contact_number %}`) rather than this filter.
    """

    if not value:
        return ''

    value = str(value).strip()

    if not value:
        return ''

    leading_plus = value.startswith('+')

    digits = re.sub(r'\D', '', value)

    if not digits:
        return ''

    return ('+' if leading_plus else '') + digits