import re
from datetime import timedelta
from functools import wraps

from django.conf import settings

from django.contrib.auth.decorators import login_required
from django.contrib.auth import (
    get_user_model,
    logout,
    authenticate,
    login,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView

from django.contrib import messages

from django.core.exceptions import ValidationError

from django.core.validators import validate_email

from django.contrib.auth.password_validation import validate_password

from django.core.paginator import Paginator

from django.db.models import Q

from django.http import (
    HttpResponseForbidden,
    JsonResponse,
)

from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from django.urls import reverse, reverse_lazy

from django.utils import timezone

from django.utils.http import url_has_allowed_host_and_scheme

from .models import (
    Disaster,
    DisasterReport,
    DisasterType,
    EmergencyAgency,
    Feedback,
    Notification,
    NotificationRead,
    UserSettings,
    SupportRequest,
    create_support_request_notification,
)

from .forms import (
    DisasterReportForm,
    FeedbackForm,
    ProfileUpdateForm,
    AvatarUploadForm,
    CitizenSettingsForm,
    SupportRequestForm,
    MAX_REPORT_PHOTOS_PER_UPLOAD,
    validate_incident_report_photo,
)

from .legal import (
    TERMS_VERSION,
    LEGAL_LAST_UPDATED,
    LEGAL_CONTACT_EMAIL,
)


User = get_user_model()


# =========================================================
# CITIZEN-ONLY ACCESS CONTROL
# =========================================================


def is_admin_account(user):
    """
    True for an authenticated staff/superuser (Admin) account.

    Centralized here so every place that needs to tell an Admin
    account apart from a Citizen account (feedback submission
    guards, template checks via the ``ndms_extras`` filter, etc.)
    uses the exact same rule.
    """

    return (
        user.is_authenticated
        and (user.is_staff or user.is_superuser)
    )


def citizen_required(view_func):
    """
    Restrict a view to authenticated Citizen accounts.

    Unauthenticated visitors follow Django's normal login flow.
    Staff/superuser accounts are sent to the separate admin
    dashboard instead of being allowed to use citizen features.
    """

    @login_required
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):

        if request.user.role != 'CITIZEN':

            if request.user.is_staff or request.user.is_superuser:
                return redirect('admin_dashboard')

            return HttpResponseForbidden(
                'You do not have permission to access this page.'
            )

        return view_func(request, *args, **kwargs)

    return _wrapped_view


class CitizenRequiredMixin(LoginRequiredMixin):
    """Allow a class-based view only for authenticated Citizens."""

    def dispatch(self, request, *args, **kwargs):

        if request.user.is_authenticated:

            if request.user.role != 'CITIZEN':

                if request.user.is_staff or request.user.is_superuser:
                    return redirect('admin_dashboard')

                return HttpResponseForbidden(
                    'You do not have permission to access this page.'
                )

        return super().dispatch(request, *args, **kwargs)


# =========================================================
# PUBLIC HOME + FEEDBACK
# =========================================================

def home(request):

    # -----------------------------------------------------
    # SUBMIT FEEDBACK
    # -----------------------------------------------------

    if request.method == 'POST':

        # Only logged-in users can submit feedback
        if not request.user.is_authenticated:
            return redirect('login')

        # Admin/staff accounts are feedback VIEWERS, not
        # submitters — block this regardless of how the request
        # was made (form, direct POST, crafted request, etc.).
        if is_admin_account(request.user):

            messages.error(
                request,
                'Feedback submission is not available for '
                'administrator accounts.'
            )

            return redirect('home')

        rating = request.POST.get('rating')

        message = request.POST.get(
            'message',
            ''
        ).strip()

        # -------------------------------------------------
        # VALIDATE RATING
        # -------------------------------------------------

        try:
            rating = int(rating)

        except (
            TypeError,
            ValueError
        ):
            rating = 0

        if rating < 1 or rating > 5:

            messages.error(
                request,
                'Please choose a rating from 1 to 5 stars.'
            )

            return redirect('home')

        # -------------------------------------------------
        # VALIDATE MESSAGE
        # -------------------------------------------------

        if not message:

            messages.error(
                request,
                'Please write a short message before submitting.'
            )

            return redirect('home')

        # -------------------------------------------------
        # SAVE FEEDBACK
        # -------------------------------------------------

        Feedback.objects.create(
            user=request.user,
            email=request.user.email,
            rating=rating,
            message=message
        )

        messages.success(
            request,
            'Your feedback has been submitted successfully.'
        )

        return redirect('home')

    # -----------------------------------------------------
    # GET HOME PAGE
    # -----------------------------------------------------

    reviews = (
        Feedback.objects
        .select_related('user')
        .order_by('-created_at')
    )

    # -----------------------------------------------------
    # DISASTER AWARENESS — uses the real, admin-managed
    # DisasterType records (name + description) so the Home
    # page never shows hard-coded/fake disaster information.
    # -----------------------------------------------------

    # Home page only ever shows these four headline categories
    # (in this order) — but they are still the real, admin-
    # managed DisasterType rows (id, name, description) looked
    # up by name, never hard-coded text/images. If the admin
    # hasn't created one of these four yet, it's simply skipped
    # rather than shown as a fake/broken card.
    home_disaster_priority = ['Earthquake', 'Flood', 'Fire', 'Other']

    disaster_types = list(
        DisasterType.objects
        .filter(is_active=True, name__in=home_disaster_priority)
    )
    disaster_types.sort(
        key=lambda dt: home_disaster_priority.index(dt.name)
    )

    # -----------------------------------------------------
    # SYSTEM SNAPSHOT -- real database counts only.
    #
    # These are the same public records already listed on the
    # Disasters and Emergency Agencies pages, counted (never
    # estimated). A value of 0 is shown as 0.
    # -----------------------------------------------------

    system_stats = {
        'active_disasters': Disaster.objects.filter(
            status='ACTIVE'
        ).count(),
        'resolved_disasters': Disaster.objects.filter(
            status__in=['RESOLVED', 'CLOSED']
        ).count(),
        'disaster_categories': DisasterType.objects.filter(
            is_active=True
        ).count(),
        'emergency_agencies': EmergencyAgency.objects.count(),
    }

    return render(
        request,
        'reports/home.html',
        {
            'reviews': reviews,
            'disaster_types': disaster_types,
            'system_stats': system_stats,
        }
    )


# =========================================================
# REGISTER
# =========================================================

USERNAME_RE = re.compile(r'[A-Za-z0-9._-]{3,30}')

PHONE_RE = re.compile(r'\+?[0-9]{7,15}')


def register(request):

    # -----------------------------------------------------
    # If already logged in
    # -----------------------------------------------------

    if request.user.is_authenticated:
        return redirect('home')

    # -----------------------------------------------------
    # GET
    # -----------------------------------------------------

    if request.method != 'POST':

        return render(
            request,
            'reports/register.html'
        )

    # -----------------------------------------------------
    # POST
    # -----------------------------------------------------

    values = {
        field: request.POST.get(field, '').strip()
        for field in (
            'first_name',
            'last_name',
            'username',
            'email',
            'phone',
        )
    }

    first_name = values['first_name']
    last_name = values['last_name']
    username = values['username']
    email = values['email']
    phone = values['phone']

    password = request.POST.get('password', '')

    confirm_password = request.POST.get('confirm_password', '')

    # -----------------------------------------------------
    # VALIDATION
    #
    # Every problem is collected as {field: [messages]} so the
    # template can show each one next to its own field, all at
    # once. Passwords are never sent back to the page.
    # -----------------------------------------------------

    errors = {}

    def add_error(field, message):
        errors.setdefault(field, []).append(message)

    # ---- required fields --------------------------------

    if not first_name:
        add_error('first_name', 'Please enter your first name.')

    if not last_name:
        add_error('last_name', 'Please enter your last name.')

    if not username:

        add_error('username', 'Please choose a username.')

    elif not USERNAME_RE.fullmatch(username):

        # Letters, numbers, dot, underscore, hyphen only. This also
        # rejects an email address (it contains "@") being used as
        # a username.
        add_error(
            'username',
            'Username must be 3-30 characters: letters, numbers, '
            'dots, underscores or hyphens only (no @ or spaces).'
        )

    if not email:
        add_error('email', 'Please enter your email address.')

    else:

        try:
            validate_email(email)

        except ValidationError:
            add_error('email', 'Please enter a valid email address.')

    # ---- phone (optional, but if given it must be a real number) --

    if phone and not PHONE_RE.fullmatch(re.sub(r'[\s-]', '', phone)):

        add_error(
            'phone',
            'Enter a valid phone number: digits only, 7-15 digits, '
            'with an optional + at the start.'
        )

    # ---- password + confirmation ------------------------

    if not password:

        add_error('password', 'Please create a password.')

    else:

        if password != confirm_password:
            add_error('confirm_password', 'Passwords do not match.')

        # -------------------------------------------------
        # PASSWORD STRENGTH (project AUTH_PASSWORD_VALIDATORS)
        # This view builds the User manually (it does not use
        # Django's own UserCreationForm/SetPasswordForm, which
        # is why the project's configured AUTH_PASSWORD_VALIDATORS
        # were never actually being enforced at registration --
        # NDMSPasswordChangeView already runs them correctly for
        # password changes via Django's SetPasswordForm, so this
        # brings registration in line with that same rule.
        # -------------------------------------------------

        # Must not be, or contain, the username, first/last name or
        # the part of the email before the "@".
        lowered = password.lower()

        for own in (username, first_name, last_name, email.split('@')[0]):

            if len(own) >= 3 and own.lower() in lowered:

                add_error(
                    'password',
                    'Password must not contain your username, name '
                    'or email.'
                )

                break

        try:
            validate_password(
                password,
                user=User(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                ),
            )

        except ValidationError as exc:

            for message in exc.messages:
                add_error('password', message)

    # ---- TERMS & PRIVACY CONSENT (required, server-side) --
    # The HTML `required` attribute is only a convenience;
    # this check is the real gate. No account is created
    # unless the box was ticked. The checkbox is never
    # pre-ticked when the page is shown again.

    if request.POST.get('accept_terms') != 'on':

        add_error(
            'accept_terms',
            'Please accept the Terms & Conditions '
            'and Privacy Policy to create your account.'
        )

    # ---- duplicates -------------------------------------

    if username and User.objects.filter(
        username=username
    ).exists():

        add_error(
            'username',
            'Username already exists. Please choose another username.'
        )

    if email and User.objects.filter(
        email=email
    ).exists():

        add_error(
            'email',
            'An account with this email already exists.'
        )

    # ---- show the form again ----------------------------

    if errors:

        return render(
            request,
            'reports/register.html',
            {
                **values,

                'errors': errors,

                'error':
                'Please review the highlighted fields and try again.',

            }
        )

    # -----------------------------------------------------
    # CREATE CITIZEN ACCOUNT
    # -----------------------------------------------------

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        role='CITIZEN',
        terms_accepted_at=timezone.now(),
        terms_version=TERMS_VERSION,
    )

    # -----------------------------------------------------
    # REGISTRATION SUCCESSFUL
    # -----------------------------------------------------

    login(
        request,
        user
    )

    # -----------------------------------------------------
    # SESSION
    # Registration signs the person straight in. The session ends
    # when the browser closes (no "keep me signed in" option here;
    # Login still has its own Remember me).
    # -----------------------------------------------------

    request.session.set_expiry(0)

    return redirect('home')


# =========================================================
# LOGIN
# =========================================================

def _is_ajax_request(request):
    """
    True for a fetch()/XHR request that sets X-Requested-With
    (same convention DeactivatedAccountMiddleware already uses).
    """

    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


def _safe_login_redirect_url(request, next_url):
    """
    Where to send a user who has just logged in.

    `next_url` comes straight from POST data, so it can be forged
    into an absolute external URL (e.g. "https://evil.example/phish").
    url_has_allowed_host_and_scheme() is the standard way to confirm
    a redirect target is a safe, same-site, non-protocol-relative URL
    before following it — this mirrors exactly what Django's own
    LoginView does for its `next` handling. Anything unsafe (or
    missing) falls back to the home page.

    Shared by the normal form POST (HTTP redirect) and the
    login.html fetch() POST (JSON), so both apply the SAME check.
    """

    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url

    return reverse('home')


def user_login(request):

    # -----------------------------------------------------
    # Already logged in
    # -----------------------------------------------------

    if request.user.is_authenticated:
        return redirect('home')

    # -----------------------------------------------------
    # POST
    # -----------------------------------------------------

    if request.method == 'POST':

        username = request.POST.get(
            'username',
            ''
        ).strip()

        password = request.POST.get(
            'password',
            ''
        )

        next_url = request.POST.get(
            'next',
            ''
        )

        remember_me = (
            request.POST.get('remember_me') == 'on'
        )

        # -------------------------------------------------
        # AUTHENTICATE
        # -------------------------------------------------

        user = authenticate(
            request,
            username=username,
            password=password
        )

        # -------------------------------------------------
        # LOGIN SUCCESSFUL
        # -------------------------------------------------

        if user is not None:

            login(
                request,
                user
            )

            # -------------------------------------------------
            # REMEMBER ME
            # -------------------------------------------------
            #
            # CHECKED: keep the session alive for
            # REMEMBER_ME_SESSION_AGE (settings.py), regardless
            # of browser close.
            #
            # UNCHECKED: set_expiry(0) makes the session cookie
            # a browser-session cookie -- the user is signed out
            # when the browser is closed. (set_expiry(None) would
            # fall back to Django's SESSION_COOKIE_AGE, a 2-week
            # persistent cookie, so the checkbox would have no
            # visible effect.)
            #
            # This only controls how long the *session id* cookie
            # lives. Passwords are never stored; saving them is
            # the browser's own, separate password-manager feature.
            # -------------------------------------------------

            if remember_me:
                request.session.set_expiry(
                    settings.REMEMBER_ME_SESSION_AGE
                )
            else:
                request.session.set_expiry(0)

            # -------------------------------------------------
            # SAFE "next" REDIRECT ONLY
            # -------------------------------------------------
            #
            # Validated by _safe_login_redirect_url() (see above).
            # -------------------------------------------------

            redirect_url = _safe_login_redirect_url(
                request,
                next_url
            )

            # -------------------------------------------------
            # LOGIN PAGE SHOULD NOT STAY IN BROWSER HISTORY
            # -------------------------------------------------
            #
            # A normal form POST + HTTP redirect leaves the login
            # page in the browser's history *underneath* the page
            # the user lands on (Home -> Login -> Report Incident),
            # so Back returns to Login. login.html therefore submits
            # the form with fetch() and, on this JSON reply, calls
            # location.replace(redirect_url), which swaps the Login
            # history entry for the destination (Home -> Report
            # Incident). Authentication itself is unchanged: the
            # session is created here, on the server, exactly as for
            # a normal POST, and the URL was validated above.
            #
            # Without JavaScript the form still posts normally and
            # gets the ordinary redirect below.
            # -------------------------------------------------

            if _is_ajax_request(request):

                return JsonResponse({
                    'success': True,
                    'redirect_url': redirect_url,
                })

            return redirect(
                redirect_url
            )

        # -------------------------------------------------
        # INVALID CREDENTIALS
        # -------------------------------------------------

        # login.html's fetch() call shows this message in place
        # (no navigation, so no extra Login history entry). Without
        # JavaScript the form posts normally and gets the existing
        # error page below (message, username, `next`).
        if _is_ajax_request(request):

            return JsonResponse(
                {
                    'success': False,
                    'error': 'Invalid username or password.',
                },
                status=401,
            )

        return render(
            request,
            'reports/login.html',
            {
                'error':
                'Invalid username or password.',

                'username':
                username,

                'next':
                next_url
            }
        )

    # -----------------------------------------------------
    # GET
    # -----------------------------------------------------

    return render(
        request,
        'reports/login.html',
        {
            'next':
            request.GET.get(
                'next',
                ''
            )
        }
    )


# =========================================================
# LOGOUT
# =========================================================

@login_required
def user_logout(request):

    logout(request)

    return redirect(
        'home'
    )


# =========================================================
# DASHBOARD
# =========================================================

@citizen_required
def dashboard(request):

    # -----------------------------------------------------
    # REPORT QUERY
    # (scoped to the logged-in citizen — the only account
    # type that reaches this view; Admin has its own
    # dashboard/report views under the admin panel)
    # -----------------------------------------------------

    report_queryset = (
        DisasterReport.objects
        .filter(
            user=request.user
        )
        .select_related(
            'disaster_type',
            'disaster'
        )
    )

    # -----------------------------------------------------
    # REPORT STATISTICS
    # -----------------------------------------------------

    total_reports = (
        report_queryset.count()
    )

    pending_reports = (
        report_queryset
        .filter(
            status='PENDING'
        )
        .count()
    )

    under_review_reports = (
        report_queryset
        .filter(
            status='UNDER_REVIEW'
        )
        .count()
    )

    verified_reports = (
        report_queryset
        .filter(
            status='VERIFIED'
        )
        .count()
    )

    # -----------------------------------------------------
    # RECENT REPORTS
    # -----------------------------------------------------

    recent_reports = (
        report_queryset
        .order_by(
            '-report_date'
        )[:5]
    )

    # -----------------------------------------------------
    # ACTIVE DISASTERS (compact dashboard preview)
    # Same query shape as the Admin dashboard's Active
    # Disasters panel (reports.admin_views.admin_dashboard) --
    # real Disaster rows only, status='ACTIVE' per the
    # existing disaster lifecycle rules. Limited to 3 for the
    # citizen preview; the full list stays on View Disasters.
    # -----------------------------------------------------

    active_disasters = (
        Disaster.objects
        .filter(
            status='ACTIVE'
        )
        .select_related(
            'disaster_type'
        )
        .order_by(
            '-start_date'
        )[:3]
    )

    # =====================================================
    # NOTIFICATIONS
    # =====================================================

    notifications = (
        Notification.objects
        .filter(
            Q(
                recipient=request.user
            )
            |
            Q(
                recipient__isnull=True
            )
        )
        .select_related(
            'published_by',
            'disaster',
            'disaster__disaster_type',
            'recipient'
        )
        .order_by(
            '-publish_date'
        )[:5]
    )

    # -----------------------------------------------------
    # READ NOTIFICATION IDS
    # -----------------------------------------------------

    read_notification_ids = set(
        NotificationRead.objects
        .filter(
            user=request.user
        )
        .values_list(
            'notification_id',
            flat=True
        )
    )

    # -----------------------------------------------------
    # UNREAD NOTIFICATION COUNT
    # -----------------------------------------------------

    unread_count = (
        Notification.objects
        .filter(
            Q(
                recipient=request.user
            )
            |
            Q(
                recipient__isnull=True
            )
        )
        .exclude(
            id__in=read_notification_ids
        )
        .count()
    )

    # -----------------------------------------------------
    # DASHBOARD
    # -----------------------------------------------------

    return render(
        request,
        'reports/dashboard.html',
        {
            'total_reports':
                total_reports,

            'pending_reports':
                pending_reports,

            'under_review_reports':
                under_review_reports,

            'verified_reports':
                verified_reports,

            'recent_reports':
                recent_reports,

            'active_disasters':
                active_disasters,

            'notifications':
                notifications,

            'unread_count':
                unread_count,

            'read_notification_ids':
                read_notification_ids,
        }
    )


# =========================================================
# REPORT INCIDENT
# =========================================================

@citizen_required
def create_disaster_report(request):

    # -----------------------------------------------------
    # ONLY CITIZENS CAN SUBMIT REPORTS
    # -----------------------------------------------------

    if request.user.role != 'CITIZEN':

        return redirect(
            'dashboard'
        )

    # -----------------------------------------------------
    # POST
    # -----------------------------------------------------

    if request.method == 'POST':

        form = DisasterReportForm(
            request.POST
        )

        # -------------------------------------------------
        # GET MULTIPLE PHOTOS
        # -------------------------------------------------
        #
        # IMPORTANT:
        # Photo is NOT part of DisasterReportForm.
        # We receive photos separately using:
        #
        # request.FILES.getlist('photos')
        #
        # -------------------------------------------------

        uploaded_photos = request.FILES.getlist(
            'photos'
        )

        # -------------------------------------------------
        # MAXIMUM 5 PHOTOS (unchanged limit)
        # -------------------------------------------------

        if len(uploaded_photos) > MAX_REPORT_PHOTOS_PER_UPLOAD:

            form.add_error(
                None,
                'You can upload a maximum of '
                f'{MAX_REPORT_PHOTOS_PER_UPLOAD} photos.'
            )

        # -------------------------------------------------
        # SERVER-SIDE PHOTO VALIDATION
        # -------------------------------------------------
        #
        # Every photo is re-validated here, server-side, before any
        # DisasterReportPhoto row is ever created — the browser-
        # supplied Content-Type / file extension is never trusted on
        # its own: content type + size are checked, and Pillow
        # actually opens and verifies each file is a genuine,
        # uncorrupted image (the same pattern already used for
        # avatars, support attachments, and official disaster
        # photos elsewhere in this project). Anything that fails is
        # added as a form error so submission is rejected the same
        # way the "maximum 5 photos" check above already is.
        # -------------------------------------------------

        for photo in uploaded_photos:

            try:
                validate_incident_report_photo(photo)

            except ValidationError as exc:

                form.add_error(
                    None,
                    ' '.join(exc.messages)
                )

        # -------------------------------------------------
        # VALIDATE FORM
        # -------------------------------------------------

        if form.is_valid():

            # -------------------------------------------------
            # SAVE MAIN REPORT FIRST
            # -------------------------------------------------

            disaster_report = form.save(
                commit=False
            )

            # Attach logged-in citizen
            disaster_report.user = request.user

            # Safety: always start as PENDING
            disaster_report.status = 'PENDING'

            disaster_report.save()

            # -------------------------------------------------
            # NO "REPORT RECEIVED" NOTIFICATION
            # -------------------------------------------------
            #
            # Intentionally NOT creating a citizen-facing
            # Notification here. The citizen already knows their
            # report was submitted -- that confirmation comes from
            # the success message below (and the redirect to their
            # reports list), not from a separate Alert.
            #
            # Creating a Notification whose recipient AND
            # published_by were both the submitting citizen was
            # the bug this step corrects: a citizen must never
            # appear to be the system/admin publisher of their own
            # notification, and submitting a report is a user
            # action that doesn't need to be echoed back as an
            # "event" notification.
            #
            # Citizen notifications now start at the first real
            # status transition (PENDING -> UNDER_REVIEW), created
            # by admin_report_update_status() in admin_views.py via
            # create_report_status_notification().
            # -------------------------------------------------

            # -------------------------------------------------
            # SAVE PHOTOS
            # -------------------------------------------------
            #
            # NOTE:
            # This assumes your separate photo model is
            # named DisasterReportPhoto.
            #
            # -------------------------------------------------

            if uploaded_photos:

                from .models import DisasterReportPhoto

                for photo in uploaded_photos[:MAX_REPORT_PHOTOS_PER_UPLOAD]:

                    DisasterReportPhoto.objects.create(
                        report=disaster_report,
                        image=photo
                    )

            # -------------------------------------------------
            # SUCCESS MESSAGE
            # -------------------------------------------------

            messages.success(
                request,
                'Your disaster report has been submitted successfully.'
            )

            return redirect(
                'my_reports'
            )

    # -----------------------------------------------------
    # GET
    # -----------------------------------------------------

    else:

        initial = {}
        dt_param = (request.GET.get('disaster_type') or '').strip()

        if dt_param:
            dt_obj = None
            if dt_param.isdigit():
                dt_obj = DisasterType.objects.filter(
                    id=int(dt_param),
                    is_active=True
                ).first()

            if not dt_obj:
                dt_obj = DisasterType.objects.filter(
                    name__iexact=dt_param,
                    is_active=True
                ).first()

            if dt_obj:
                initial['disaster_type'] = dt_obj
        else:
            user_settings_obj, _ = UserSettings.objects.get_or_create(
                user=request.user
            )
            if (
                user_settings_obj.default_disaster_type
                and user_settings_obj.default_disaster_type.is_active
            ):
                initial['disaster_type'] = user_settings_obj.default_disaster_type

        form = DisasterReportForm(initial=initial)

    # -----------------------------------------------------
    # TOPBAR NOTIFICATIONS
    # (same pattern used by dashboard(), needed so the
    # shared topbar notification UI works on this page too)
    # -----------------------------------------------------

    notifications = (
        Notification.objects
        .filter(
            Q(recipient=request.user)
            |
            Q(recipient__isnull=True)
        )
        .select_related(
            'published_by',
            'disaster',
            'disaster__disaster_type',
            'recipient'
        )
        .order_by(
            '-publish_date'
        )[:5]
    )

    read_notification_ids = set(
        NotificationRead.objects
        .filter(
            user=request.user
        )
        .values_list(
            'notification_id',
            flat=True
        )
    )

    unread_count = (
        Notification.objects
        .filter(
            Q(recipient=request.user)
            |
            Q(recipient__isnull=True)
        )
        .exclude(
            id__in=read_notification_ids
        )
        .count()
    )

    # -----------------------------------------------------
    # LOCATION SHARING PREFERENCE (Settings)
    # -----------------------------------------------------
    #
    # Purely informational here -- the map, current-location
    # button and address sync are unchanged either way. If the
    # citizen has turned Location Sharing off in Settings, the
    # template shows a small note; they can still use the map
    # or the current-location button manually if they choose.
    # -----------------------------------------------------

    user_settings, _created = UserSettings.objects.get_or_create(
        user=request.user
    )

    location_sharing_enabled = (
        user_settings.location_permission != 'NEVER'
    )

    return render(
        request,
        'reports/report_incident.html',
        {
            'form':
                form,

            'notifications':
                notifications,

            'unread_count':
                unread_count,

            'read_notification_ids':
                read_notification_ids,

            'GOOGLE_MAPS_API_KEY':
                settings.GOOGLE_MAPS_API_KEY,

            'location_sharing_enabled':
                location_sharing_enabled,
        }
    )


# =========================================================
# MY REPORTS
# =========================================================

@citizen_required
def my_reports(request):

    # -----------------------------------------------------
    # ONLY CITIZENS HAVE A "MY REPORTS" VIEW
    # -----------------------------------------------------

    if request.user.role != 'CITIZEN':

        return redirect(
            'dashboard'
        )

    # -----------------------------------------------------
    # BASE QUERYSET — ALWAYS SCOPED TO THE LOGGED-IN CITIZEN
    # -----------------------------------------------------

    own_reports = (
        DisasterReport.objects
        .filter(
            user=request.user
        )
    )

    # -----------------------------------------------------
    # SUMMARY STATISTICS
    # (always computed from ALL of the citizen's reports,
    # regardless of the current filter/search, so the cards
    # stay accurate while browsing a filtered list)
    # -----------------------------------------------------

    total_reports = (
        own_reports.count()
    )

    pending_reports = (
        own_reports
        .filter(
            status='PENDING'
        )
        .count()
    )

    under_review_reports = (
        own_reports
        .filter(
            status='UNDER_REVIEW'
        )
        .count()
    )

    verified_reports = (
        own_reports
        .filter(
            status='VERIFIED'
        )
        .count()
    )

    rejected_reports = (
        own_reports
        .filter(
            status='REJECTED'
        )
        .count()
    )

    # -----------------------------------------------------
    # AWAITING REVIEW
    # (PENDING + UNDER_REVIEW combined -- used by the compact
    # 3-card summary shown on this page; the individual
    # pending/under_review counts above are still used by the
    # Status filter options)
    # -----------------------------------------------------

    awaiting_review_reports = (
        pending_reports
        +
        under_review_reports
    )

    # -----------------------------------------------------
    # STATUS FILTER
    # -----------------------------------------------------

    valid_statuses = [
        'PENDING',
        'UNDER_REVIEW',
        'VERIFIED',
        'REJECTED',
    ]

    status_filter = request.GET.get(
        'status',
        'ALL'
    ).upper()

    if status_filter not in valid_statuses:

        status_filter = 'ALL'

    reports = (
        own_reports
        .select_related(
            'disaster_type',
            'disaster'
        )
        .order_by(
            '-report_date'
        )
    )

    if status_filter != 'ALL':

        reports = reports.filter(
            status=status_filter
        )

    # -----------------------------------------------------
    # DISASTER TYPE FILTER
    # (choices always come from the DisasterType table itself,
    # so newly added types automatically appear -- nothing is
    # hard-coded here)
    # -----------------------------------------------------

    disaster_types = (
        DisasterType.objects
        .filter(
            is_active=True
        )
        .order_by(
            'name'
        )
    )

    disaster_type_param = request.GET.get(
        'disaster_type',
        ''
    ).strip()

    disaster_type_filter = ''

    if disaster_type_param.isdigit():

        if disaster_types.filter(
            id=int(disaster_type_param)
        ).exists():

            disaster_type_filter = disaster_type_param

    if disaster_type_filter:

        reports = reports.filter(
            disaster_type_id=int(disaster_type_filter)
        )

    # -----------------------------------------------------
    # SEARCH
    # (disaster type, address, or report ID)
    # -----------------------------------------------------

    search_query = request.GET.get(
        'q',
        ''
    ).strip()

    if search_query:

        search_filter = (
            Q(
                disaster_type__name__icontains=search_query
            )
            |
            Q(
                address__icontains=search_query
            )
        )

        # Allow searching by numeric report ID, with or
        # without a leading "#" (e.g. "12" or "#12").

        numeric_query = search_query.lstrip('#')

        if numeric_query.isdigit():

            search_filter |= Q(
                id=int(numeric_query)
            )

        reports = reports.filter(
            search_filter
        )

    # -----------------------------------------------------
    # PAGINATION
    # -----------------------------------------------------

    paginator = Paginator(
        reports,
        10
    )

    page_obj = paginator.get_page(
        request.GET.get('page')
    )

    # -----------------------------------------------------
    # TOPBAR NOTIFICATIONS
    # (same pattern used by dashboard() / create_disaster_report(),
    # needed so the shared topbar notification UI works here too)
    # -----------------------------------------------------

    notifications = (
        Notification.objects
        .filter(
            Q(recipient=request.user)
            |
            Q(recipient__isnull=True)
        )
        .select_related(
            'published_by',
            'disaster',
            'disaster__disaster_type',
            'recipient'
        )
        .order_by(
            '-publish_date'
        )[:5]
    )

    read_notification_ids = set(
        NotificationRead.objects
        .filter(
            user=request.user
        )
        .values_list(
            'notification_id',
            flat=True
        )
    )

    unread_count = (
        Notification.objects
        .filter(
            Q(recipient=request.user)
            |
            Q(recipient__isnull=True)
        )
        .exclude(
            id__in=read_notification_ids
        )
        .count()
    )

    return render(
        request,
        'reports/my_reports.html',
        {
            'page_obj':
                page_obj,

            'reports':
                page_obj.object_list,

            'total_reports':
                total_reports,

            'pending_reports':
                pending_reports,

            'under_review_reports':
                under_review_reports,

            'verified_reports':
                verified_reports,

            'rejected_reports':
                rejected_reports,

            'awaiting_review_reports':
                awaiting_review_reports,

            'status_filter':
                status_filter,

            'disaster_types':
                disaster_types,

            'disaster_type_filter':
                disaster_type_filter,

            'search_query':
                search_query,

            'has_active_filters':
                bool(
                    status_filter != 'ALL'
                    or search_query
                    or disaster_type_filter
                ),

            'notifications':
                notifications,

            'unread_count':
                unread_count,

            'read_notification_ids':
                read_notification_ids,
        }
    )


# =========================================================
# REPORT DETAIL (CITIZEN)
# =========================================================

@citizen_required
def report_detail(
    request,
    report_id
):

    # -----------------------------------------------------
    # ONLY CITIZENS HAVE A "MY REPORTS" DETAIL VIEW
    # -----------------------------------------------------

    if request.user.role != 'CITIZEN':

        return redirect(
            'dashboard'
        )

    # -----------------------------------------------------
    # GET REPORT
    # -----------------------------------------------------

    report = get_object_or_404(
        DisasterReport.objects
        .select_related(
            'disaster_type',
            'disaster'
        )
        .prefetch_related(
            'photos'
        ),
        id=report_id
    )

    # -----------------------------------------------------
    # SECURITY — OWNERSHIP ENFORCED ON THE BACKEND
    # A citizen must never be able to view another
    # citizen's report by guessing/changing the URL.
    # -----------------------------------------------------

    if report.user != request.user:

        return HttpResponseForbidden(
            'You are not allowed to view this report.'
        )

    photos = report.photos.all()

    # -----------------------------------------------------
    # STATUS DESCRIPTION
    # (plain-language explanation of the citizen's current
    # report status -- purely presentational, derived from
    # the real status value; no history/timeline is invented)
    # -----------------------------------------------------

    status_descriptions = {
        'PENDING':
            'Your report has been submitted and is awaiting review.',

        'UNDER_REVIEW':
            'Your report is currently being reviewed by NDMS.',

        'VERIFIED':
            'Your report has been reviewed and verified by NDMS.',

        'REJECTED':
            'This report was reviewed and was not accepted.',
    }

    status_description = status_descriptions.get(
        report.status,
        ''
    )

    # -----------------------------------------------------
    # DELETE ELIGIBILITY
    # A citizen may only delete a report while it is still
    # PENDING -- i.e. before any review has started. Once
    # review begins (UNDER_REVIEW), or the report has been
    # finalized (VERIFIED or REJECTED), the record is kept:
    # a VERIFIED report may be linked to an official Disaster
    # and admin/audit history, and a REJECTED report remains
    # the historical record of that decision. This same rule
    # is enforced again, server-side, inside delete_report()
    # below -- this flag only controls whether the Delete
    # action is shown on this page.
    # -----------------------------------------------------

    can_delete = (
        report.status == 'PENDING'
    )

    delete_disabled_reason = ''

    if not can_delete:

        delete_disabled_reasons = {
            'UNDER_REVIEW':
                'This report cannot be deleted because it is '
                'already under review.',

            'VERIFIED':
                'This report cannot be deleted because it has '
                'been verified and kept as an official record.',

            'REJECTED':
                'This report cannot be deleted because it is '
                'kept as a historical record.',
        }

        delete_disabled_reason = delete_disabled_reasons.get(
            report.status,
            'This report cannot be deleted.'
        )

    # -----------------------------------------------------
    # RESPONSE UPDATES
    # Only shown when the report has actually been linked to
    # a Disaster (admin-managed) AND that disaster has real
    # DisasterUpdate entries. Nothing is fabricated -- if
    # there is no linked disaster or no updates yet, the
    # template shows an empty-state message instead.
    # -----------------------------------------------------

    response_updates = []

    official_disaster = None

    latest_response_update = None

    official_photos = []

    if report.disaster_id:

        official_disaster = report.disaster

        response_updates = list(
            report.disaster.updates
            .select_related(
                'agency'
            )
            .order_by(
                '-update_date'
            )
        )

        latest_response_update = (
            response_updates[0] if response_updates else None
        )

        # Official disaster photos only -- the citizen's own raw
        # evidence photos are shown separately above and are
        # never promoted into the official media set.
        official_photos = list(
            report.disaster.photos.all()
        )

    # -----------------------------------------------------
    # TOPBAR NOTIFICATIONS
    # -----------------------------------------------------

    notifications = (
        Notification.objects
        .filter(
            Q(recipient=request.user)
            |
            Q(recipient__isnull=True)
        )
        .select_related(
            'published_by',
            'disaster',
            'disaster__disaster_type',
            'recipient'
        )
        .order_by(
            '-publish_date'
        )[:5]
    )

    read_notification_ids = set(
        NotificationRead.objects
        .filter(
            user=request.user
        )
        .values_list(
            'notification_id',
            flat=True
        )
    )

    unread_count = (
        Notification.objects
        .filter(
            Q(recipient=request.user)
            |
            Q(recipient__isnull=True)
        )
        .exclude(
            id__in=read_notification_ids
        )
        .count()
    )

    return render(
        request,
        'reports/report_detail.html',
        {
            'report':
                report,

            'photos':
                photos,

            'status_description':
                status_description,

            'can_delete':
                can_delete,

            'delete_disabled_reason':
                delete_disabled_reason,

            'response_updates':
                response_updates,

            'official_disaster':
                official_disaster,

            'latest_response_update':
                latest_response_update,

            'official_photos':
                official_photos,

            'notifications':
                notifications,

            'unread_count':
                unread_count,

            'read_notification_ids':
                read_notification_ids,

            'GOOGLE_MAPS_API_KEY':
                settings.GOOGLE_MAPS_API_KEY,
        }
    )


# =========================================================
# DELETE MY OWN REPORT (CITIZEN)
# =========================================================
#
# A citizen may delete only their own report, from the Report
# Details page. Ownership is enforced here on the server —
# the same way report_detail() above enforces it for viewing —
# so changing the report_id in the URL/request can never let
# someone delete (or even discover the existence of) another
# citizen's report. POST-only, and CSRF protection (already
# enabled project-wide) applies as normal.
# =========================================================

@citizen_required
def delete_report(
    request,
    report_id
):

    if request.method != 'POST':

        return redirect(
            'report_detail',
            report_id=report_id
        )

    if request.user.role != 'CITIZEN':

        return redirect(
            'dashboard'
        )

    report = get_object_or_404(
        DisasterReport,
        id=report_id
    )

    # -----------------------------------------------------
    # SECURITY — OWNERSHIP ENFORCED ON THE BACKEND
    # -----------------------------------------------------

    if report.user != request.user:

        return HttpResponseForbidden(
            'You are not allowed to delete this report.'
        )

    # -----------------------------------------------------
    # DELETE ELIGIBILITY — ENFORCED SERVER-SIDE
    # Only a still-PENDING report may be deleted. This is
    # checked again here (independent of whatever the UI
    # showed) so eligibility can never be bypassed by
    # posting directly to this URL. See report_detail()
    # for the matching can_delete flag used to show/hide
    # the Delete action on the page itself.
    # -----------------------------------------------------

    if report.status != 'PENDING':

        messages.error(
            request,
            'This report cannot be deleted because it is '
            'already being processed or retained as an '
            'official record.'
        )

        return redirect(
            'report_detail',
            report_id=report.id
        )

    report.delete()

    messages.success(
        request,
        f'Report #{report_id} was deleted successfully.'
    )

    return redirect(
        'my_reports'
    )


# =========================================================
# ABOUT
# =========================================================

def about(request):

    return render(
        request,
        'reports/about.html'
    )


# =========================================================
# LEGAL PAGES (Terms & Conditions / Privacy Policy)
# =========================================================
#
# Public pages -- no login required, so visitors can read them
# before registering. The wording lives in the templates; the
# version, revision date and contact email come from
# reports/legal.py so there is a single place to update them.
# =========================================================

def _legal_context():

    return {
        'terms_version': TERMS_VERSION,
        'legal_last_updated': LEGAL_LAST_UPDATED,
        'legal_contact_email': LEGAL_CONTACT_EMAIL,
    }


def terms(request):

    return render(
        request,
        'reports/terms.html',
        _legal_context()
    )


def privacy(request):

    return render(
        request,
        'reports/privacy.html',
        _legal_context()
    )


# =========================================================
# FEEDBACK
# =========================================================

@login_required
def submit_feedback(request):

    if request.method != 'POST':

        return redirect(
            'home'
        )

    # Admin/staff accounts are feedback VIEWERS, not submitters —
    # block this endpoint for them too, independent of the home()
    # guard above and of AdminCitizenPortalIsolationMiddleware, so
    # feedback can never be created no matter how the request
    # reaches this view.
    if is_admin_account(request.user):

        messages.error(
            request,
            'Feedback submission is not available for '
            'administrator accounts.'
        )

        return redirect('home')

    form = FeedbackForm(
        request.POST
    )

    if form.is_valid():

        feedback = form.save(
            commit=False
        )

        feedback.user = request.user

        feedback.save()

    return redirect(
        'home'
    )


# =========================================================
# PUBLIC DISASTERS (DIRECTORY & DETAIL)
# =========================================================

def disaster_list(request):
    """
    Public Disaster Directory:
    Displays verified and officially managed disaster situations across Nepal.
    Supports combined server-side search, filtering by type, severity, and status,
    with pagination preserving active filters.
    """
    queryset = (
        Disaster.objects
        .select_related('disaster_type')
        .prefetch_related('photos', 'updates')
        .order_by('-start_date')
    )

    # Search: title, location/address, or description
    q = request.GET.get('q', '').strip()
    if q:
        queryset = queryset.filter(
            Q(title__icontains=q) |
            Q(address__icontains=q) |
            Q(description__icontains=q)
        )

    # Filter: Disaster Type
    selected_type = request.GET.get('type', '').strip()
    if selected_type:
        queryset = queryset.filter(disaster_type_id=selected_type)

    # Filter: Severity
    selected_severity = request.GET.get('severity', '').strip().upper()
    valid_severities = dict(Disaster.SEVERITY_CHOICES)
    if selected_severity and selected_severity in valid_severities:
        queryset = queryset.filter(severity=selected_severity)
    else:
        selected_severity = ''

    # Filter: Status
    selected_status = request.GET.get('status', '').strip().upper()
    valid_statuses = dict(Disaster.STATUS_CHOICES)
    if selected_status and selected_status in valid_statuses:
        queryset = queryset.filter(status=selected_status)
    else:
        selected_status = ''

    # Pagination: 6 disasters per page (2 columns x 3 rows)
    paginator = Paginator(queryset, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Build query string for pagination links preserving active filters
    params = request.GET.copy()
    if 'page' in params:
        del params['page']
    query_string = params.urlencode()

    disaster_types = DisasterType.objects.filter(is_active=True).order_by('name')

    has_active_filters = bool(q or selected_type or selected_severity or selected_status)

    context = {
        'page_obj': page_obj,
        'disasters': page_obj,
        'disaster_types': disaster_types,
        'severity_choices': Disaster.SEVERITY_CHOICES,
        'status_choices': Disaster.STATUS_CHOICES,
        'q': q,
        'selected_type': selected_type,
        'selected_severity': selected_severity,
        'selected_status': selected_status,
        'query_string': query_string,
        'has_active_filters': has_active_filters,
    }

    return render(
        request,
        'reports/disaster_list.html',
        context
    )


def disaster_guidelines(request):
    """
    Public Disaster Awareness & Guidelines:
    Comprehensive, bilingual (English + Nepali) public safety and disaster
    preparedness center. Educates citizens on natural and human-induced hazards,
    actionable Before/During/After safety instructions, emergency kits, family
    plans, and safe NDMS incident reporting procedures.
    """
    disaster_types = DisasterType.objects.filter(is_active=True).order_by('name')
    agencies = EmergencyAgency.objects.all().order_by('id')

    context = {
        'disaster_types': disaster_types,
        'agencies': agencies,
    }

    return render(
        request,
        'reports/disaster_guidelines.html',
        context
    )


def emergency_agencies(request):
    """
    Public Emergency Agencies Directory:
    Read-only, citizen-facing directory of the official response
    agencies already managed by Admin (the same EmergencyAgency
    records used by the Admin Emergency Agencies page and the
    Disaster Response Updates timeline) — no separate agency data
    store. Supports combined server-side search (name/type/location)
    and an Agency Type filter derived from the real database values.
    """
    queryset = EmergencyAgency.objects.all().order_by('agency_name')

    # Search: agency name, agency type, or location
    q = request.GET.get('q', '').strip()
    if q:
        queryset = queryset.filter(
            Q(agency_name__icontains=q) |
            Q(agency_type__icontains=q) |
            Q(location__icontains=q)
        )

    # Filter: Agency Type — options come from the real, admin-managed
    # agency_type values actually in the database, never hard-coded.
    agency_types = (
        EmergencyAgency.objects
        .exclude(agency_type='')
        .order_by('agency_type')
        .values_list('agency_type', flat=True)
        .distinct()
    )

    selected_type = request.GET.get('type', '').strip()
    if selected_type:
        queryset = queryset.filter(agency_type=selected_type)

    # Pagination: 9 agencies per page (3 columns x 3 rows)
    paginator = Paginator(queryset, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Build query string for pagination links preserving active filters
    params = request.GET.copy()
    if 'page' in params:
        del params['page']
    query_string = params.urlencode()

    has_active_filters = bool(q or selected_type)

    context = {
        'page_obj': page_obj,
        'agencies': page_obj,
        'agency_types': agency_types,
        'q': q,
        'selected_type': selected_type,
        'query_string': query_string,
        'has_active_filters': has_active_filters,
    }

    return render(
        request,
        'reports/emergency_agencies.html',
        context
    )


def disaster_detail(request, disaster_id):
    """
    Public Disaster Detail:
    Trustworthy official detail page for a verified disaster situation.
    Presents official overview, location/map, response updates timeline,
    and approved official photos. Raw citizen report evidence is never exposed.
    """
    disaster = get_object_or_404(
        Disaster.objects
        .select_related('disaster_type')
        .prefetch_related('reports'),
        id=disaster_id
    )

    updates = (
        disaster.updates
        .select_related('agency', 'updated_by')
        .order_by('-update_date')
    )

    photos = (
        disaster.photos
        .all()
        .order_by('-uploaded_at')
    )

    # Count of linked verified citizen reports (privacy-safe, no citizen PII)
    linked_reports_count = disaster.reports.count()

    context = {
        'disaster': disaster,
        'updates': updates,
        'photos': photos,
        'linked_reports_count': linked_reports_count,
        'GOOGLE_MAPS_API_KEY': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
    }

    return render(
        request,
        'reports/disaster_detail.html',
        context
    )


# =========================================================
# ALERTS (CITIZEN — NOTIFICATIONS / ALERT CENTER)
# =========================================================

@citizen_required
def alerts(request):

    # -----------------------------------------------------
    # BASE QUERYSET — NOTIFICATIONS VISIBLE TO THIS USER
    # (own notifications + global/broadcast notifications —
    # the exact same visibility rule already used by
    # dashboard() and my_reports())
    # -----------------------------------------------------

    visible_notifications = (
        Notification.objects
        .filter(
            Q(
                recipient=request.user
            )
            |
            Q(
                recipient__isnull=True
            )
        )
        .select_related(
            'published_by',
            'disaster',
            'disaster__disaster_type',
            'recipient'
        )
    )

    # -----------------------------------------------------
    # READ NOTIFICATION IDS FOR THIS USER
    # -----------------------------------------------------

    read_notification_ids = set(
        NotificationRead.objects
        .filter(
            user=request.user
        )
        .values_list(
            'notification_id',
            flat=True
        )
    )

    # -----------------------------------------------------
    # SUMMARY STATISTICS
    # (always computed from ALL alerts visible to the user,
    # regardless of the current filter, so the summary cards
    # stay accurate while browsing a filtered list)
    # -----------------------------------------------------

    total_alerts = (
        visible_notifications.count()
    )

    unread_alerts = (
        visible_notifications
        .exclude(
            id__in=read_notification_ids
        )
        .count()
    )

    recent_cutoff = (
        timezone.now() - timedelta(days=7)
    )

    recent_alerts = (
        visible_notifications
        .filter(
            publish_date__gte=recent_cutoff
        )
        .count()
    )

    # -----------------------------------------------------
    # FILTER (All / Unread / Read)
    # -----------------------------------------------------

    valid_filters = [
        'UNREAD',
        'READ',
    ]

    alert_filter = request.GET.get(
        'filter',
        'ALL'
    ).upper()

    if alert_filter not in valid_filters:

        alert_filter = 'ALL'

    alert_list = (
        visible_notifications
        .order_by(
            '-publish_date'
        )
    )

    if alert_filter == 'UNREAD':

        alert_list = alert_list.exclude(
            id__in=read_notification_ids
        )

    elif alert_filter == 'READ':

        alert_list = alert_list.filter(
            id__in=read_notification_ids
        )

    # -----------------------------------------------------
    # PAGINATION
    # -----------------------------------------------------

    paginator = Paginator(
        alert_list,
        10
    )

    page_obj = paginator.get_page(
        request.GET.get('page')
    )

    # -----------------------------------------------------
    # TOPBAR NOTIFICATIONS
    # (same pattern used by dashboard() / my_reports(), needed
    # so the shared topbar notification bell/dropdown works
    # correctly on this page too)
    # -----------------------------------------------------

    notifications = (
        visible_notifications
        .order_by(
            '-publish_date'
        )[:5]
    )

    unread_count = unread_alerts

    return render(
        request,
        'reports/alerts.html',
        {
            'page_obj':
                page_obj,

            'alert_list':
                page_obj.object_list,

            'total_alerts':
                total_alerts,

            'unread_alerts':
                unread_alerts,

            'recent_alerts':
                recent_alerts,

            'alert_filter':
                alert_filter,

            'read_notification_ids':
                read_notification_ids,

            'notifications':
                notifications,

            'unread_count':
                unread_count,
        }
    )


# =========================================================
# SAFE REDIRECT HELPER FOR NOTIFICATION ACTIONS
# =========================================================

def _safe_notification_redirect(request):

    # -----------------------------------------------------
    # Redirect back to wherever the mark-as-read action was
    # triggered from (e.g. the Alerts page, preserving its
    # current filter/page), falling back to the Alerts page
    # itself if that is missing or unsafe.
    # -----------------------------------------------------

    referer = request.META.get(
        'HTTP_REFERER'
    )

    if referer and url_has_allowed_host_and_scheme(
        url=referer,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure()
    ):

        return referer

    return reverse(
        'alerts'
    )


# =========================================================
# MARK ONE NOTIFICATION AS READ
# =========================================================

@citizen_required
def mark_notification_read(
    request,
    notification_id
):

    # -----------------------------------------------------
    # STATE-CHANGING ACTION — POST ONLY
    # -----------------------------------------------------

    if request.method != 'POST':

        return HttpResponseForbidden(
            'Only POST requests are allowed.'
        )

    notification = get_object_or_404(
        Notification,
        id=notification_id
    )

    # -----------------------------------------------------
    # USER ACCESS CHECK
    # -----------------------------------------------------

    if (
        notification.recipient is not None
        and
        notification.recipient != request.user
    ):

        return HttpResponseForbidden(
            'You are not authorized to access this notification.'
        )

    NotificationRead.objects.get_or_create(

        user=request.user,

        notification=notification
    )

    # A report-linked notification (Report Received / Under
    # Review / Verified / Rejected) is marked read and sent
    # straight to that report's existing Report Details page --
    # this is the citizen's own report, so no extra access check
    # is needed beyond the recipient check above.
    if notification.report_id is not None:

        return redirect(
            'report_detail',
            report_id=notification.report_id
        )

    # A disaster-linked notification is marked read and then sent
    # straight to the existing canonical Disaster Details page
    # (map/location included) instead of back to wherever the
    # click came from, so the citizen sees the official disaster
    # info immediately -- and never a second, duplicate detail
    # page. Plain notifications keep the existing "return to
    # referer" behaviour unchanged.
    if notification.disaster_id is not None:

        return redirect(
            'disaster_detail',
            disaster_id=notification.disaster_id
        )

    return redirect(
        _safe_notification_redirect(request)
    )


# =========================================================
# NOTIFICATION DETAIL
# =========================================================
#
# Shows a single general notification (no linked Report, no
# linked Disaster). Report-linked notifications redirect to the
# existing Report Details page and disaster-linked notifications
# redirect to the existing, canonical Disaster Details page --
# see the redirects below -- so this template only ever needs to
# render plain notification content.
# =========================================================

@citizen_required
def notification_detail(
    request,
    notification_id
):

    notification = get_object_or_404(
        Notification.objects
        .select_related(
            'published_by',
            'disaster',
            'disaster__disaster_type',
        ),
        id=notification_id
    )

    # -----------------------------------------------------
    # USER ACCESS CHECK
    # (same rule as mark_notification_read: a notification
    # targeted at a specific recipient is only visible to
    # that recipient; broadcast notifications — recipient is
    # null — are visible to every citizen)
    # -----------------------------------------------------

    if (
        notification.recipient_id is not None
        and
        notification.recipient_id != request.user.id
    ):

        return HttpResponseForbidden(
            'You are not authorized to access this notification.'
        )

    # Report-linked notifications don't have their own detail
    # page -- they route straight to the existing Report Details
    # page for the report they're about, same as
    # mark_notification_read() does for the unread case.
    if notification.report_id is not None:

        return redirect(
            'report_detail',
            report_id=notification.report_id
        )

    # Disaster-linked notifications don't have their own detail
    # page either -- they route straight to the existing,
    # canonical Disaster Details page for the disaster they're
    # about, same as mark_notification_read() does for the
    # unread case. This keeps the Disaster Details page the
    # SINGLE source of truth for disaster information instead of
    # duplicating it here.
    if notification.disaster_id is not None:

        return redirect(
            'disaster_detail',
            disaster_id=notification.disaster_id
        )

    # -----------------------------------------------------
    # SHARED TOPBAR CONTEXT
    # (same "own + broadcast notifications" query pattern used
    # by alerts() / dashboard() / my_reports(), so the shared
    # sidebar badge and topbar notification dropdown behave
    # identically on this page)
    # -----------------------------------------------------

    visible_notifications = (
        Notification.objects
        .filter(
            Q(recipient=request.user)
            | Q(recipient__isnull=True)
        )
    )

    read_notification_ids = set(
        NotificationRead.objects
        .filter(user=request.user)
        .values_list('notification_id', flat=True)
    )

    context = {
        'notification': notification,
        'read_notification_ids': read_notification_ids,
        'notifications': (
            visible_notifications
            .select_related('disaster')
            .order_by('-publish_date')[:5]
        ),
        'unread_count': (
            visible_notifications
            .exclude(id__in=read_notification_ids)
            .count()
        ),
    }

    return render(
        request,
        'reports/notification_detail.html',
        context
    )


# =========================================================
# MARK ALL NOTIFICATIONS AS READ
# =========================================================

@citizen_required
def mark_all_notifications_read(request):

    if request.method == 'POST':

        # -------------------------------------------------
        # GET USER'S VISIBLE NOTIFICATIONS
        # -------------------------------------------------

        notifications = (
            Notification.objects
            .filter(
                Q(
                    recipient=request.user
                )
                |
                Q(
                    recipient__isnull=True
                )
            )
        )

        # -------------------------------------------------
        # EXISTING READ NOTIFICATIONS
        # -------------------------------------------------

        existing_ids = set(
            NotificationRead.objects
            .filter(
                user=request.user
            )
            .values_list(
                'notification_id',
                flat=True
            )
        )

        # -------------------------------------------------
        # CREATE READ OBJECTS
        # -------------------------------------------------

        read_objects = []

        for notification in notifications:

            if notification.id not in existing_ids:

                read_objects.append(
                    NotificationRead(
                        user=request.user,
                        notification=notification
                    )
                )

        # -------------------------------------------------
        # BULK CREATE
        # -------------------------------------------------

        if read_objects:

            NotificationRead.objects.bulk_create(
                read_objects
            )

    return redirect(
        _safe_notification_redirect(request)
    )


# =========================================================
# MARK DISASTER ALERTS AS READ
# =========================================================
#
# Backs the Disaster unread red-dot indicator (public navbar,
# Disasters dropdown, Dashboard sidebar). Called automatically
# (small background POST, see reports/js/disaster-alerts-read.js)
# when a signed-in citizen opens View Disasters, so the existing
# unread DISASTER_ALERT notification(s) become read without an
# extra "Mark as Read" click.
#
# Reuses the exact same Notification / NotificationRead models
# and the same "own + broadcast" visibility rule already used by
# dashboard() / alerts() / mark_all_notifications_read() -- no
# new notification system, no new model.
#
# Only DISASTER_ALERT notifications are ever touched here; report
# and general notifications are completely untouched, and this
# never affects another citizen's NotificationRead rows.
# =========================================================

@citizen_required
def mark_disaster_alerts_read(request):

    if request.method != 'POST':

        return HttpResponseForbidden(
            'Only POST requests are allowed.'
        )

    # -----------------------------------------------------
    # THIS USER'S ALREADY-READ NOTIFICATION IDS
    # -----------------------------------------------------

    read_notification_ids = (
        NotificationRead.objects
        .filter(
            user=request.user
        )
        .values_list(
            'notification_id',
            flat=True
        )
    )

    # -----------------------------------------------------
    # THIS USER'S UNREAD DISASTER ALERT IDS
    # (own + broadcast, DISASTER_ALERT only)
    # -----------------------------------------------------

    unread_alert_ids = list(
        Notification.objects
        .filter(
            Q(
                recipient=request.user
            )
            |
            Q(
                recipient__isnull=True
            ),
            notification_type=Notification.TYPE_DISASTER_ALERT
        )
        .exclude(
            id__in=read_notification_ids
        )
        .values_list(
            'id',
            flat=True
        )
    )

    # -----------------------------------------------------
    # MARK READ (per-user NotificationRead rows only --
    # the broadcast Notification itself is never touched)
    # -----------------------------------------------------
    #
    # ignore_conflicts=True respects the existing
    # (user, notification) unique_together constraint even
    # under a race (e.g. two tabs open at once), so this never
    # raises or creates duplicate NotificationRead rows.
    # -----------------------------------------------------

    if unread_alert_ids:

        NotificationRead.objects.bulk_create(
            [
                NotificationRead(
                    user=request.user,
                    notification_id=notification_id
                )
                for notification_id in unread_alert_ids
            ],
            ignore_conflicts=True
        )

    return JsonResponse(
        {
            'success': True
        }
    )


# =========================================================
# MY PROFILE
# =========================================================
#
# NOTE:
# This reuses the exact same "topbar notifications" query
# pattern already used by dashboard() / create_disaster_report()
# / my_reports() / alerts(), so the shared topbar notification
# bell/dropdown works correctly on this page too.
#
# =========================================================

@citizen_required
def profile(request):

    # -----------------------------------------------------
    # EDIT PROFILE (POST)
    # -----------------------------------------------------

    if request.method == 'POST':

        form = ProfileUpdateForm(
            request.POST,
            instance=request.user
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                'Profile updated successfully.'
            )

            # Redirect (POST/Redirect/GET) so a page refresh
            # never resubmits the form.
            return redirect(
                'profile'
            )

    # -----------------------------------------------------
    # GET
    # -----------------------------------------------------

    else:

        form = ProfileUpdateForm(
            instance=request.user
        )

    # -----------------------------------------------------
    # CHANGE PHOTO
    # (blank form for the modal on this page — the upload
    # itself is submitted to the separate change_photo view
    # below, keeping it independent of the Edit Profile form)
    # -----------------------------------------------------

    avatar_form = AvatarUploadForm()

    # -----------------------------------------------------
    # MY ACTIVITY — REAL REPORT STATISTICS FOR THIS USER
    # -----------------------------------------------------

    own_reports = (
        DisasterReport.objects
        .filter(
            user=request.user
        )
    )

    total_reports = (
        own_reports.count()
    )

    pending_reports = (
        own_reports
        .filter(
            status='PENDING'
        )
        .count()
    )

    under_review_reports = (
        own_reports
        .filter(
            status='UNDER_REVIEW'
        )
        .count()
    )

    verified_reports = (
        own_reports
        .filter(
            status='VERIFIED'
        )
        .count()
    )

    rejected_reports = (
        own_reports
        .filter(
            status='REJECTED'
        )
        .count()
    )

    # -----------------------------------------------------
    # TOPBAR NOTIFICATIONS
    # (same pattern used elsewhere in this file)
    # -----------------------------------------------------

    notifications = (
        Notification.objects
        .filter(
            Q(recipient=request.user)
            |
            Q(recipient__isnull=True)
        )
        .select_related(
            'published_by',
            'disaster',
            'disaster__disaster_type',
            'recipient'
        )
        .order_by(
            '-publish_date'
        )[:5]
    )

    read_notification_ids = set(
        NotificationRead.objects
        .filter(
            user=request.user
        )
        .values_list(
            'notification_id',
            flat=True
        )
    )

    unread_count = (
        Notification.objects
        .filter(
            Q(recipient=request.user)
            |
            Q(recipient__isnull=True)
        )
        .exclude(
            id__in=read_notification_ids
        )
        .count()
    )

    return render(
        request,
        'reports/profile.html',
        {
            'form':
                form,

            'avatar_form':
                avatar_form,

            'total_reports':
                total_reports,

            'pending_reports':
                pending_reports,

            'under_review_reports':
                under_review_reports,

            'verified_reports':
                verified_reports,

            'rejected_reports':
                rejected_reports,

            'notifications':
                notifications,

            'unread_count':
                unread_count,

            'read_notification_ids':
                read_notification_ids,
        }
    )


# =========================================================
# CHANGE PHOTO
# =========================================================
#
# Kept as its own view (rather than a branch inside profile())
# so the Edit Profile form above is never touched by a photo
# upload, and vice versa. request.user is always the target —
# there is no id in the URL, so a logged-in user can only ever
# change their own avatar.
#
# =========================================================

@citizen_required
def change_photo(request):

    if request.method != 'POST':
        return redirect('profile')

    form = AvatarUploadForm(
        request.POST,
        request.FILES,
        instance=request.user
    )

    if form.is_valid():

        form.save()

        messages.success(
            request,
            'Profile photo updated successfully.'
        )

    else:

        error_message = (
            form.errors['avatar'][0]
            if form.errors.get('avatar')
            else 'Could not update your photo. Please try a JPG or PNG under 5MB.'
        )

        messages.error(
            request,
            error_message
        )

    return redirect('profile')


# =========================================================
# REMOVE PHOTO
# =========================================================
#
# Deletes the current user's uploaded avatar file and clears
# the field, reverting the header/topbar back to the
# first-letter placeholder. Same own-user-only guarantee as
# change_photo — request.user is always the target.
#
# =========================================================

@citizen_required
def remove_photo(request):

    if request.method != 'POST':
        return redirect('profile')

    if request.user.avatar:

        request.user.avatar.delete(
            save=False
        )

        request.user.avatar = None

        request.user.save()

        messages.success(
            request,
            'Profile photo removed.'
        )

    return redirect('profile')


# =========================================================
# SETTINGS
# =========================================================
#
# NOTE:
# UserSettings is keyed one-to-one on request.user and is
# never looked up by an id from the URL, so there is no way
# for a logged-in user to reach another user's settings.
#
# =========================================================

@citizen_required
def settings_view(request):

    # -----------------------------------------------------
    # GET OR CREATE THE SETTINGS ROW FOR THIS USER
    # -----------------------------------------------------

    user_settings, created = (
        UserSettings.objects.get_or_create(
            user=request.user
        )
    )

    # -----------------------------------------------------
    # SAVE (POST)
    # -----------------------------------------------------

    if request.method == 'POST':

        form = CitizenSettingsForm(
            request.POST,
            instance=user_settings
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                'Your settings have been saved successfully.'
            )

            # Redirect (POST/Redirect/GET) so a page refresh
            # never resubmits the form.
            return redirect(
                'settings'
            )

    # -----------------------------------------------------
    # GET
    # -----------------------------------------------------

    else:

        form = CitizenSettingsForm(
            instance=user_settings
        )

    # -----------------------------------------------------
    # TOPBAR NOTIFICATIONS
    # (same pattern used by every other view in this file)
    # -----------------------------------------------------

    notifications = (
        Notification.objects
        .filter(
            Q(recipient=request.user)
            |
            Q(recipient__isnull=True)
        )
        .select_related(
            'published_by',
            'disaster',
            'disaster__disaster_type',
            'recipient'
        )
        .order_by(
            '-publish_date'
        )[:5]
    )

    read_notification_ids = set(
        NotificationRead.objects
        .filter(
            user=request.user
        )
        .values_list(
            'notification_id',
            flat=True
        )
    )

    unread_count = (
        Notification.objects
        .filter(
            Q(recipient=request.user)
            |
            Q(recipient__isnull=True)
        )
        .exclude(
            id__in=read_notification_ids
        )
        .count()
    )

    return render(
        request,
        'reports/settings.html',
        {
            'form':
                form,

            'notifications':
                notifications,

            'unread_count':
                unread_count,

            'read_notification_ids':
                read_notification_ids,
        }
    )


# =========================================================
# CHANGE PASSWORD
# =========================================================
#
# NOTE:
# Reuses Django's built-in, battle-tested password-change
# flow (no custom/duplicate password-handling logic). Only
# the template and the post-success behaviour are customised
# so it fits the NDMS dashboard shell and returns the citizen
# to their Profile page with a normal success message instead
# of a separate "done" page.
#
# =========================================================

class NDMSPasswordChangeView(
    CitizenRequiredMixin,
    PasswordChangeView
):

    template_name = 'reports/password_change.html'

    success_url = reverse_lazy(
        'profile'
    )

    def form_valid(self, form):

        response = super().form_valid(form)

        messages.success(
            self.request,
            'Your password has been changed successfully.'
        )

        return response

    # -----------------------------------------------------
    # SHARED TOPBAR CONTEXT
    # (same notification pattern used by every other view in
    # this file, so the sidebar badge / notification dropdown
    # render correctly on this page too)
    # -----------------------------------------------------

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        notifications = (
            Notification.objects
            .filter(
                Q(recipient=self.request.user)
                |
                Q(recipient__isnull=True)
            )
            .select_related(
                'published_by',
                'disaster',
                'disaster__disaster_type',
                'recipient'
            )
            .order_by(
                '-publish_date'
            )[:5]
        )

        read_notification_ids = set(
            NotificationRead.objects
            .filter(
                user=self.request.user
            )
            .values_list(
                'notification_id',
                flat=True
            )
        )

        unread_count = (
            Notification.objects
            .filter(
                Q(recipient=self.request.user)
                |
                Q(recipient__isnull=True)
            )
            .exclude(
                id__in=read_notification_ids
            )
            .count()
        )

        context['notifications'] = notifications
        context['read_notification_ids'] = read_notification_ids
        context['unread_count'] = unread_count

        return context

# =========================================================
# HELP & SUPPORT
# =========================================================

@citizen_required
def help_support(request):

    # -----------------------------------------------------
    # REPORT A PROBLEM (POST)
    # -----------------------------------------------------

    if request.method == 'POST':

        form = SupportRequestForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            support_request = form.save(
                commit=False
            )

            support_request.user = request.user

            support_request.save()

            # Existing Notification system, admin-facing: alert
            # every eligible Admin/Staff account that a new
            # Support Request has come in. Only reached after a
            # successful save on this POST branch, so a failed
            # validation, a page refresh/GET, or any other
            # SupportRequest change never creates one of these.
            create_support_request_notification(
                support_request,
                request.user
            )

            messages.success(
                request,
                'Your problem report has been submitted. '
                'Our team will look into it.'
            )

            # Redirect (POST/Redirect/GET) so a page refresh
            # never resubmits the form.
            return redirect(
                'help_support'
            )

        else:

            messages.error(
                request,
                'Please fix the errors below and try '
                'submitting again.'
            )

    # -----------------------------------------------------
    # GET
    # -----------------------------------------------------

    else:

        form = SupportRequestForm()

    # -----------------------------------------------------
    # MY SUPPORT REQUESTS (Phase A)
    # Scoped to the logged-in citizen ONLY -- the same
    # ownership pattern used everywhere else in this file
    # (my_reports(), report_detail(), etc.). A citizen can
    # never see another citizen's support requests, status,
    # or admin response through this view.
    # -----------------------------------------------------

    my_support_requests = (
        SupportRequest.objects
        .filter(user=request.user)
        .order_by('-created_at')
    )

    # -----------------------------------------------------
    # SHARED TOPBAR / SIDEBAR CONTEXT
    # (same notification pattern already used by dashboard(),
    # alerts(), and every other dashboard-style view in this
    # file, so the sidebar badge and notification dropdown
    # render correctly on this page too)
    # -----------------------------------------------------

    notifications = (
        Notification.objects
        .filter(
            Q(
                recipient=request.user
            )
            |
            Q(
                recipient__isnull=True
            )
        )
        .select_related(
            'published_by',
            'disaster',
            'disaster__disaster_type',
            'recipient'
        )
        .order_by(
            '-publish_date'
        )[:5]
    )

    read_notification_ids = set(
        NotificationRead.objects
        .filter(
            user=request.user
        )
        .values_list(
            'notification_id',
            flat=True
        )
    )

    unread_count = (
        Notification.objects
        .filter(
            Q(
                recipient=request.user
            )
            |
            Q(
                recipient__isnull=True
            )
        )
        .exclude(
            id__in=read_notification_ids
        )
        .count()
    )

    return render(
        request,
        'reports/help_support.html',
        {
            'form':
                form,

            'my_support_requests':
                my_support_requests,

            'notifications':
                notifications,

            'read_notification_ids':
                read_notification_ids,

            'unread_count':
                unread_count,
        }
    )