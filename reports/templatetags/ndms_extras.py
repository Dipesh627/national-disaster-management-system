"""
NDMS template extras.

Small, presentation-only template filters used by the navbar/avatar
UI. This module does not touch models, views, or auth logic — it
only formats data that is already available on `request.user`.
"""

from django import template

register = template.Library()


@register.filter(name='initials')
def initials(value):
    """
    Return 1-2 uppercase initials for a display name.

    Examples
    --------
    "Mahee Bhandari" -> "MB"
    "Mahee"          -> "M"
    "admin"          -> "A"
    ""  / None       -> ""
    """

    if not value:
        return ''

    parts = [part for part in str(value).strip().split() if part]

    if not parts:
        return ''

    if len(parts) == 1:
        return parts[0][0].upper()

    return (parts[0][0] + parts[-1][0]).upper()


@register.filter(name='has_multiple_accounts')
def has_multiple_accounts(user):
    """
    Placeholder for future "Switch account" support in the navbar.

    The project does not currently track multiple linked accounts
    per user, so this always returns False today (nothing is built
    or assumed here — no model, auth, or URL changes). Once a
    `linked_accounts` relation exists on the User model, this will
    start returning True for users with 2+ accounts and the
    "Switch account" navbar item will appear automatically.
    """

    linked = getattr(user, 'linked_accounts', None)

    if not linked:
        return False

    try:
        return linked.count() > 1
    except (AttributeError, TypeError):
        return False


# =========================================================
# DISASTER TYPE ICON
# =========================================================
#
# Purely cosmetic glyph lookup for the public Home "Disaster
# Awareness" cards. DisasterType has no icon field, so this
# only picks a symbol to display next to the *real* name and
# description already stored on the model — it invents no
# data. Any type not in the map (including future admin-added
# types) safely falls back to a neutral glyph.
#
# =========================================================

_DISASTER_ICONS = {
    'flood': '\u224b',
    'fire': '!',
    'landslide': '\u25b2',
    'earthquake': '\u25b3',
    'avalanche': '\u2744',
    'road accident': '\u2716',
    'aircraft accident': '\u2708',
    'other': '\u2699',
}


@register.filter(name='disaster_icon')
def disaster_icon(name):
    """Return a small glyph for a DisasterType name (cosmetic only)."""

    if not name:
        return '\u26a0'

    return _DISASTER_ICONS.get(str(name).strip().lower(), '\u26a0')


# =========================================================
# DISASTER TYPE IMAGE
# =========================================================
# Maps disaster names to their static photo asset.
# Unmatched or admin-added types fall back to disaster-other.jpg.
# =========================================================

_DISASTER_IMAGES = {
    'flood': 'reports/images/disaster-flood.jpg',
    'fire': 'reports/images/disaster-fire.jpg',
    'earthquake': 'reports/images/disaster-earthquake.jpg',
    'landslide': 'reports/images/disaster-other.jpg',
    'avalanche': 'reports/images/disaster-other.jpg',
    'road accident': 'reports/images/disaster-other.jpg',
    'aircraft accident': 'reports/images/disaster-other.jpg',
    'other': 'reports/images/disaster-other.JPEG',
}


@register.filter(name='disaster_image')
def disaster_image(name):
    """Return a static image asset path for a DisasterType name."""

    if not name:
        return 'reports/images/disaster-other.jpg'

    return _DISASTER_IMAGES.get(str(name).strip().lower(), 'reports/images/disaster-other.jpg')