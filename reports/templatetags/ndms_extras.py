"""
NDMS template extras.

Small, presentation-only template filters used by the navbar/avatar
UI. This module does not touch models, views, or auth logic — it
only formats data that is already available on `request.user`.
"""

from django import template
from django.utils.safestring import mark_safe

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


# =========================================================
# DISASTER TYPE ICON
# =========================================================
#
# Purely cosmetic icon lookup for the public navbar dropdown and
# the Home page. DisasterType has no icon field, so this only
# picks a small inline SVG to show next to the *real* name and
# description already stored on the model - it invents no data.
# Any type not in the map (including future admin-added types)
# falls back to a neutral "information" icon.
#
# Icons are simple 24x24 outline SVGs drawn with currentColor,
# so they follow the theme (light/dark) automatically. They
# replace the earlier Unicode glyphs (triangles, snowflake,
# etc.), which rendered inconsistently between systems.
#
# =========================================================

_SVG_OPEN = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" '
    'aria-hidden="true" focusable="false">'
)

_DISASTER_ICON_PATHS = {
    'flood': (
        '<path d="M3 8c1.5 0 1.5 1.2 3 1.2S7.5 8 9 8s1.5 1.2 3 1.2S13.5 8 15 8s1.5 1.2 3 1.2S19.5 8 21 8"/>'
        '<path d="M3 13c1.5 0 1.5 1.2 3 1.2S7.5 13 9 13s1.5 1.2 3 1.2S13.5 13 15 13s1.5 1.2 3 1.2S19.5 13 21 13"/>'
        '<path d="M3 18c1.5 0 1.5 1.2 3 1.2S7.5 18 9 18s1.5 1.2 3 1.2S13.5 18 15 18s1.5 1.2 3 1.2S19.5 18 21 18"/>'
    ),
    'fire': (
        '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.07-2.14-.22-4.05 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.15.43-2.29 1-3a2.5 2.5 0 0 0 2.5 2.5Z"/>'
    ),
    'earthquake': (
        '<path d="M22 12h-3.2a2 2 0 0 0-1.9 1.4l-2.4 7.6a.3.3 0 0 1-.6 0L9.3 3a.3.3 0 0 0-.6 0l-2.4 7.6A2 2 0 0 1 4.4 12H2"/>'
    ),
    'landslide': (
        '<path d="M3 20 9.5 7l3.5 6 2-3 6 10Z"/>'
        '<circle cx="17.5" cy="5.5" r="1.4"/><circle cx="20.5" cy="8.5" r="1"/>'
    ),
    'avalanche': (
        '<path d="m8 3 4 8 5-5 5 15H2L8 3Z"/>'
    ),
    'road accident': (
        '<path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9l-1.4 2.9A3.7 3.7 0 0 0 2 12v4c0 .6.4 1 1 1h2"/>'
        '<circle cx="7" cy="17" r="2"/><circle cx="17" cy="17" r="2"/><path d="M9 17h6"/>'
    ),
    'aircraft accident': (
        '<path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2Z"/>'
    ),
}

_DISASTER_ICON_DEFAULT = (
    '<circle cx="12" cy="12" r="9"/>'
    '<path d="M12 7.5v5.5"/>'
    '<path d="M12 16.4v.1"/>'
)


@register.filter(name='disaster_svg')
def disaster_svg(name):
    """Return an inline outline SVG icon for a DisasterType name."""

    key = str(name).strip().lower() if name else ''

    paths = _DISASTER_ICON_PATHS.get(key, _DISASTER_ICON_DEFAULT)

    return mark_safe(_SVG_OPEN + paths + '</svg>')


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
    'landslide': 'reports/images/disaster-other.jpeg',
    'avalanche': 'reports/images/disaster-other.jpeg',
    'road accident': 'reports/images/disaster-other.jpeg',
    'aircraft accident': 'reports/images/disaster-other.jpeg',
    'other': 'reports/images/disaster-other.jpeg',
}

# The shipped fallback photo is disaster-other.jpeg. The previous map
# pointed at "disaster-other.jpg" (missing) and "disaster-other.JPEG"
# (wrong case on case-sensitive servers), so those images 404'd.
_DISASTER_IMAGE_DEFAULT = 'reports/images/disaster-other.jpeg'


@register.filter(name='disaster_image')
def disaster_image(name):
    """Return a static image asset path for a DisasterType name."""

    if not name:
        return _DISASTER_IMAGE_DEFAULT

    return _DISASTER_IMAGES.get(
        str(name).strip().lower(),
        _DISASTER_IMAGE_DEFAULT
    )