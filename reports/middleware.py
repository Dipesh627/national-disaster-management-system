from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone as django_timezone


class DeactivatedAccountMiddleware:
    """
    Enforce `is_active` on every request for an already-authenticated
    session — for BOTH Citizen and Admin/staff accounts.

    Django's own auth machinery only checks `is_active` at LOGIN time
    (``ModelBackend.authenticate()`` calls ``user_can_authenticate()``,
    which refuses to authenticate an inactive account). Nothing in the
    framework re-checks it on later requests: once a session cookie
    exists, ``request.user.is_authenticated`` keeps returning True for
    the lifetime of that session even if an admin deactivates the
    account a second later. None of this project's existing access
    checks (`login_required`, `citizen_required` /
    `CitizenRequiredMixin`, `admin_required`) look at `is_active`
    either — they only ask "is this session authenticated", so a
    citizen (or staff) session that was valid when deactivation
    happened stays fully usable until it expires or the browser is
    closed.

    This middleware closes that gap ONCE, centrally, instead of
    duplicating an `is_active` check into every decorator/mixin: it
    runs on every request, and the moment it sees an authenticated-but-
    deactivated user it forcibly logs the session out server-side and
    sends them to the appropriate login page. Every existing decorator
    downstream then simply sees an anonymous request and behaves
    exactly as it already does for a logged-out visitor — no other
    file has to change.

    Placed immediately after AuthenticationMiddleware (so
    `request.user` is resolved) and before AdminTimezoneMiddleware /
    CitizenTimezoneMiddleware / AdminCitizenPortalIsolationMiddleware,
    so none of those ever run against an account this middleware has
    just logged out.

    Active users (citizen or admin) are completely unaffected, and so
    is the normal login/logout flow — this middleware only ever acts
    on a session that is *already* authenticated.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        user = getattr(request, 'user', None)

        if user is not None and user.is_authenticated and not user.is_active:

            was_admin_account = user.is_staff or user.is_superuser

            auth_logout(request)

            messages.error(
                request,
                'Your account has been deactivated. '
                'Please contact support if you believe this is a mistake.'
            )

            # An AJAX/fetch caller gets a plain 403 instead of a
            # redirect, so client-side JS handling a JSON endpoint
            # (e.g. the "mark notifications read" call) fails
            # cleanly instead of receiving an HTML login page.
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                from django.http import JsonResponse
                return JsonResponse(
                    {'success': False, 'error': 'Account deactivated.'},
                    status=403,
                )

            login_url_name = 'admin_login' if was_admin_account else 'login'

            return redirect(reverse(login_url_name))

        return self.get_response(request)


class AdminTimezoneMiddleware:
    """
    Activate the signed-in administrator's preferred Time Zone
    (UserSettings.time_zone, set on the Admin Settings page) for
    the duration of the request.

    This only changes how already-stored datetimes are DISPLAYED
    (Django's `date`/`time` template filters render using the
    currently active timezone whenever USE_TZ=True) — it never
    touches how a datetime is stored, and auto_now/auto_now_add
    fields are completely unaffected.

    Citizen accounts and logged-out visitors are unaffected and
    keep using the project default (settings.TIME_ZONE).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        user = getattr(request, 'user', None)

        admin_time_zone = None

        if (
            user is not None
            and user.is_authenticated
            and (user.is_staff or user.is_superuser)
        ):

            # Local import — avoids importing models before the
            # app registry is ready, and keeps this middleware
            # module free of a module-level model dependency.
            from .models import UserSettings

            admin_settings = (
                UserSettings.objects
                .filter(user=user)
                .only('time_zone')
                .first()
            )

            if admin_settings is not None:
                admin_time_zone = admin_settings.time_zone

        if admin_time_zone:

            try:
                django_timezone.activate(admin_time_zone)
            except Exception:
                # An invalid/unknown zone name should never break
                # the request — fall back to the project default.
                django_timezone.deactivate()

        else:
            django_timezone.deactivate()

        return self.get_response(request)


class CitizenTimezoneMiddleware:
    """
    Activate the signed-in CITIZEN's preferred Time Zone
    (UserSettings.time_zone, set on the Citizen Settings page) for
    the duration of the request.

    Deliberately a separate class from AdminTimezoneMiddleware so the
    two preference systems stay isolated: this one only ever runs for
    authenticated NON-staff accounts, and the admin one only ever runs
    for staff/superusers. It is registered immediately AFTER the admin
    middleware in settings.MIDDLEWARE, so the admin middleware's
    deactivate() call for citizens happens first and this one then
    applies the citizen's own zone.

    Exactly like the admin equivalent, this only changes how already
    stored datetimes are DISPLAYED (Django renders `date`/`time`
    template filters in the currently active timezone when USE_TZ=True).
    Nothing is rewritten in the database, DateTimeField values are
    untouched, auto_now/auto_now_add are unaffected, and ORM filtering
    and ordering continue to work on the stored UTC values.

    Anonymous visitors keep the project default (settings.TIME_ZONE).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # Local import for the same reason as above — and it reuses
        # the per-request cache, so this costs no extra query.
        from .context_processors import get_citizen_preferences

        prefs = get_citizen_preferences(request)

        if prefs.get('is_citizen'):

            citizen_time_zone = prefs.get('time_zone')

            if citizen_time_zone:

                try:
                    django_timezone.activate(citizen_time_zone)
                except Exception:
                    # An invalid/unknown or removed zone name must never
                    # break the request — fall back to the project default.
                    django_timezone.deactivate()

            else:
                django_timezone.deactivate()

        return self.get_response(request)


class AdminCitizenPortalIsolationMiddleware:
    """
    Prevent authenticated staff/superuser accounts from accessing
    the Citizen Portal.

    Admin accounts are allowed to access:
        /admin/
        /django-admin/
        /static/
        /media/

    They are also allowed to reach the public marketing pages
    (home "/" and "/about/") — this is intentional and exists
    solely so the Admin sidebar's "Back to Website" link (which
    points at the public home route, per the Admin shell spec)
    actually works instead of bouncing straight back to the
    dashboard. These two pages carry no citizen-only data or
    actions; every citizen-only route (reporting, my-reports,
    profile, settings, etc.) remains fully blocked below.

    The public legal pages ("/terms/" and "/privacy/") are allowed
    for the same reason: the shared site footer links to them, and
    they contain only public policy text.

    "/disasters/" (public Disaster list/detail/guidelines, and the
    public Emergency Agencies directory) is deliberately NOT in
    this allow-list. Public Disaster information and the public
    Emergency Agencies directory are Citizen/Public-only surfaces
    — an Admin/Staff account manages disasters and agencies through
    the Admin Dashboard instead, so a request for any public
    Disaster URL (or any other citizen-portal URL) falls through to
    the redirect below, exactly like every other citizen-only route.

    Any other application URL is redirected to the Admin Dashboard.

    Citizen accounts and unauthenticated visitors are unaffected.
    """

    ADMIN_ALLOWED_PREFIXES = (
        '/admin/',
        '/django-admin/',
        '/static/',
        '/media/',
    )

    # Exact-path public pages the Admin's "Back to Website" /
    # public-navbar flow is allowed to reach. Kept separate from
    # ADMIN_ALLOWED_PREFIXES (which is matched with startswith)
    # since "/" would otherwise match every URL in the project.
    #
    # '/logout/' (the public site's logout URL, reports.views
    # .user_logout) is included here deliberately: it must be
    # reachable by an authenticated admin the same way Home/About
    # are, otherwise this middleware intercepts the request BEFORE
    # the logout view ever runs and bounces the admin straight back
    # to the Admin Dashboard without Django's logout() ever being
    # called — the admin session is never actually destroyed. This
    # does not weaken admin protection: every admin-only URL is
    # still blocked below, and logging out is not a citizen-only
    # action that needs isolating.
    ADMIN_ALLOWED_EXACT_PATHS = (
        '/',
        '/about/',
        '/terms/',
        '/privacy/',
        '/logout/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user

        # Only isolate authenticated staff/superuser accounts.
        if user.is_authenticated and (
            user.is_staff or user.is_superuser
        ):
            path = request.path

            # Admin pages and required static/media files remain accessible.
            if path.startswith(self.ADMIN_ALLOWED_PREFIXES):
                return self.get_response(request)

            # Public home/about pages remain accessible (see docstring).
            if path in self.ADMIN_ALLOWED_EXACT_PATHS:
                return self.get_response(request)

            # Prevent admin accounts from entering the Citizen Portal.
            return redirect('admin_dashboard')

        # Normal citizens and logged-out visitors work normally.
        return self.get_response(request)