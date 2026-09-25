from functools import wraps
from itertools import chain

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.views.decorators.cache import never_cache

from .forms import (
    AdminDisasterForm,
    AdminDisasterTypeForm,
    AdminEmergencyAgencyForm,
    AdminResponseUpdateForm,
    AdminSettingsForm,
    AdminSupportRequestResponseForm,
    AvatarUploadForm,
    FeedbackForm,
    NotificationForm,
    ProfileUpdateForm,
)

from .models import (
    User,
    DisasterReport,
    Disaster,
    DisasterPhoto,
    DisasterType,
    EmergencyAgency,
    DisasterUpdate,
    Notification,
    NotificationRead,
    Feedback,
    SupportRequest,
    UserSettings,
    create_report_status_notification,
    create_disaster_alert_notification,
    create_support_response_notification,
)


# =========================================================
# ACCESS CONTROL
# =========================================================

def admin_required(view_func):
    """
    Restrict a view to authenticated staff/superuser accounts.

    Unauthenticated visitors are sent to the admin login page.
    An authenticated account that is neither staff nor superuser
    (i.e. an ordinary Citizen/User account) is logged out and
    sent there too, so a normal account can never load an admin
    page or its data just by typing the URL.

    Every admin view (except admin_login itself) should use this
    instead of repeating the same two checks.

    Also applies Django's `never_cache` to every view it protects,
    so authenticated admin pages are sent with headers telling the
    browser not to store/reuse them. This means pressing Back after
    logout cannot present a stale, seemingly-authenticated copy of
    an admin page from the browser cache — the browser is forced to
    re-request it, which re-runs the two checks above against the
    now-anonymous session and redirects to the Admin Login page.
    Public pages are untouched by this and remain normally cacheable.
    """

    @never_cache
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):

        if not request.user.is_authenticated:

            return redirect('admin_login')

        if not (
            request.user.is_staff
            or request.user.is_superuser
        ):

            logout(request)

            return redirect('admin_login')

        return view_func(request, *args, **kwargs)

    return _wrapped_view


# =========================================================
# SHARED ADMIN SHELL CONTEXT
# =========================================================

def _admin_topbar_context(request=None):
    """
    Context shared by every Admin shell page (base.html): the
    notification bell, plus the signed-in admin's Date Format
    preference (admin_date_format), used by format_admin_date /
    format_admin_datetime.

    Originally there was no separate "Admin notification"
    model/inbox in this project, so rather than fake one, the
    bell surfaced something genuinely actionable for an
    Administrator — Disaster Reports still awaiting review —
    using the same 'PENDING' status already used throughout
    admin_reports().

    That's still true for reports. Support Request notifications
    (see create_support_request_notification) are the one real
    per-admin Notification/NotificationRead inbox this project
    has, so they're folded into the same bell here rather than
    building a second, separate alert surface.
    """

    pending_reports_qs = (
        DisasterReport.objects
        .filter(status='PENDING')
        .select_related(
            'user',
            'disaster_type',
        )
        .order_by('-report_date')
    )

    admin_pending_reports_count = pending_reports_qs.count()

    context = {
        'admin_pending_reports_count': admin_pending_reports_count,
        'admin_pending_reports': pending_reports_qs[:5],
    }

    if request is not None and request.user.is_authenticated:

        # -------------------------------------------------
        # SUPPORT REQUEST NOTIFICATIONS (existing Notification
        # / NotificationRead system, personal to this admin)
        # -------------------------------------------------

        read_notification_ids = NotificationRead.objects.filter(
            user=request.user
        ).values_list(
            'notification_id',
            flat=True
        )

        unread_support_notifications_qs = (
            Notification.objects
            .filter(
                recipient=request.user,
                support_request__isnull=False,
            )
            .exclude(
                id__in=read_notification_ids
            )
            .select_related('support_request')
            .order_by('-publish_date')
        )

        admin_support_notifications_count = (
            unread_support_notifications_qs.count()
        )

        context['admin_support_notifications_count'] = (
            admin_support_notifications_count
        )
        context['admin_support_notifications'] = (
            unread_support_notifications_qs[:5]
        )

        # Combined total used only for the single topbar bell
        # badge, so it "naturally" includes the new notification
        # type without touching admin_pending_reports_count,
        # which other templates (sidebar badge, dashboard) still
        # use on its own for the reports-specific figure.
        context['admin_alerts_total_count'] = (
            admin_pending_reports_count
            + admin_support_notifications_count
        )

        admin_settings = UserSettings.objects.filter(
            user=request.user
        ).first()

        if admin_settings is not None:

            context['admin_date_format'] = admin_settings.date_format

    else:

        context['admin_alerts_total_count'] = admin_pending_reports_count

    return context


# =========================================================
# AUTHENTICATION
# =========================================================

def admin_login(request):

    # Already logged-in admin
    if request.user.is_authenticated:

        if request.user.is_staff or request.user.is_superuser:
            return redirect('admin_dashboard')

        # Normal user should not remain on admin login
        logout(request)

    error = None
    username = ''

    if request.method == 'POST':

        username = request.POST.get(
            'username',
            ''
        ).strip()

        password = request.POST.get(
            'password',
            ''
        )

        if not username or not password:

            error = 'Please enter your username and password.'

        else:

            user = authenticate(
                request,
                username=username,
                password=password
            )

            if user is None:

                error = 'Invalid admin credentials.'

            elif not user.is_active:

                error = 'This account is inactive.'

            elif not (
                user.is_staff
                or user.is_superuser
            ):

                error = (
                    'You do not have permission '
                    'to access the admin panel.'
                )

            else:

                login(
                    request,
                    user
                )

                return redirect(
                    'admin_dashboard'
                )

    return render(
        request,
        'reports/admin/login.html',
        {
            'error': error,
            'username': username,
        }
    )


@admin_required
def admin_logout(request):

    logout(request)

    return redirect('admin_login')


# =========================================================
# DASHBOARD
# =========================================================

@admin_required
def admin_dashboard(request):

    # -----------------------------------------------------
    # KPI METRICS
    # -----------------------------------------------------

    total_users = User.objects.count()

    total_citizens = User.objects.filter(
        role='CITIZEN'
    ).count()

    total_reports = DisasterReport.objects.count()

    pending_reports = DisasterReport.objects.filter(
        status='PENDING'
    ).count()

    under_review_reports = DisasterReport.objects.filter(
        status='UNDER_REVIEW'
    ).count()

    verified_reports = DisasterReport.objects.filter(
        status='VERIFIED'
    ).count()

    rejected_reports = DisasterReport.objects.filter(
        status='REJECTED'
    ).count()

    active_disasters_qs = Disaster.objects.filter(
        status='ACTIVE'
    )

    active_disasters_count = active_disasters_qs.count()

    high_active_count = active_disasters_qs.filter(severity='HIGH').count()

    critical_active_count = active_disasters_qs.filter(
        severity='CRITICAL'
    ).count()

    high_critical_active_count = high_active_count + critical_active_count

    # -----------------------------------------------------
    # SITUATION — RECENT DISASTER REPORTS (table, section 04)
    # -----------------------------------------------------

    recent_reports = (
        DisasterReport.objects
        .select_related(
            'user',
            'disaster_type',
            'disaster',
        )
        .order_by('-report_date')[:7]
    )

    # -----------------------------------------------------
    # SITUATION — ACTIVE DISASTERS (section 03, left column)
    # -----------------------------------------------------

    active_disasters = (
        active_disasters_qs
        .select_related('disaster_type')
        .order_by('-start_date')[:5]
    )

    # -----------------------------------------------------
    # RESPONSE UPDATES (section 05)
    # -----------------------------------------------------

    recent_response_updates = (
        DisasterUpdate.objects
        .select_related(
            'disaster',
            'agency',
        )
        .order_by('-update_date')[:5]
    )

    # -----------------------------------------------------
    # RECENT ACTIVITY FEED (section 03, right column)
    #
    # There is no unified "activity log" model in this project,
    # so rather than invent one, this merges the real, already-
    # timestamped events that already exist across the admin —
    # new disaster reports, response updates, published
    # notifications and citizen feedback — into a single feed
    # sorted by when they actually happened.
    # -----------------------------------------------------

    activity_reports = [
        {
            'kind': 'report',
            'text': f"New disaster report submitted \u2014 {r.disaster_type.name}",
            'timestamp': r.report_date,
        }
        for r in DisasterReport.objects.select_related('disaster_type').order_by('-report_date')[:5]
    ]

    activity_updates = [
        {
            'kind': 'update',
            'text': f"Response update added \u2014 {u.agency.agency_name} on {u.disaster.title}",
            'timestamp': u.update_date,
        }
        for u in DisasterUpdate.objects.select_related('agency', 'disaster').order_by('-update_date')[:5]
    ]

    activity_notifications = [
        {
            'kind': 'notification',
            'text': f"Notification published \u2014 {n.title}",
            'timestamp': n.publish_date,
        }
        for n in Notification.objects.order_by('-publish_date')[:5]
    ]

    activity_feedback = [
        {
            'kind': 'feedback',
            'text': "Citizen feedback received",
            'timestamp': f.created_at,
        }
        for f in Feedback.objects.order_by('-created_at')[:5]
    ]

    recent_activity = sorted(
        chain(
            activity_reports,
            activity_updates,
            activity_notifications,
            activity_feedback,
        ),
        key=lambda item: item['timestamp'],
        reverse=True,
    )[:6]

    # -----------------------------------------------------
    # COMMUNITY ACTIVITY (section 06, left column)
    # -----------------------------------------------------

    last_7_days = timezone.now() - timezone.timedelta(days=7)

    total_notifications = Notification.objects.count()

    notifications_this_week = Notification.objects.filter(
        publish_date__gte=last_7_days
    ).count()

    total_support_requests = SupportRequest.objects.count()

    # -----------------------------------------------------
    # ADMIN ACTIVITY (section 06, right column)
    # -----------------------------------------------------

    total_feedback = Feedback.objects.count()

    feedback_this_week = Feedback.objects.filter(
        created_at__gte=last_7_days
    ).count()

    total_agencies = EmergencyAgency.objects.count()

    context = {

        'total_users': total_users,
        'total_citizens': total_citizens,

        'total_reports': total_reports,
        'pending_reports': pending_reports,
        'under_review_reports': under_review_reports,
        'verified_reports': verified_reports,
        'rejected_reports': rejected_reports,

        'active_disasters_count': active_disasters_count,
        'critical_active_count': high_critical_active_count,
        'high_active_count': high_active_count,

        'recent_reports': recent_reports,
        'active_disasters': active_disasters,
        'recent_response_updates': recent_response_updates,
        'recent_activity': recent_activity,

        'total_notifications': total_notifications,
        'notifications_this_week': notifications_this_week,
        'total_support_requests': total_support_requests,

        'total_feedback': total_feedback,
        'feedback_this_week': feedback_this_week,
        'total_agencies': total_agencies,

        'dashboard_generated_at': timezone.now(),

    }

    context.update(_admin_topbar_context(request))

    return render(
        request,
        'reports/admin/dashboard.html',
        context
    )


# =========================================================
# GLOBAL SEARCH
# =========================================================

@admin_required
def admin_global_search(request):
    """
    Topbar "Admin Alerts"'s sibling shell feature: a GLOBAL
    ADMIN SEARCH, deliberately kept on its own URL/view/
    template so a topbar query never lands in — or leaks out
    of — any single module's own request.GET.get('q') search.

    Each section below mirrors the exact fields already used
    by that module's own search (see admin_reports/
    admin_disasters/admin_disaster_types/admin_agencies/
    admin_response_updates/admin_users above), so results here
    stay consistent with what an admin would find by searching
    that module directly. Every section is capped at 5 results
    and read-only — nothing here creates, edits, or deletes
    any record.
    """

    search_query = request.GET.get('q', '').strip()

    report_results = DisasterReport.objects.none()
    disaster_results = Disaster.objects.none()
    type_results = DisasterType.objects.none()
    agency_results = EmergencyAgency.objects.none()
    update_results = DisasterUpdate.objects.none()
    citizen_results = User.objects.none()

    if search_query:

        report_results = (
            DisasterReport.objects
            .select_related(
                'user',
                'disaster_type',
            )
            .filter(
                Q(user__username__icontains=search_query)
                | Q(user__first_name__icontains=search_query)
                | Q(user__last_name__icontains=search_query)
                | Q(address__icontains=search_query)
                | Q(description__icontains=search_query)
                | Q(disaster_type__name__icontains=search_query)
            )
            .order_by('-report_date')[:5]
        )

        disaster_results = (
            Disaster.objects
            .select_related('disaster_type')
            .filter(
                Q(title__icontains=search_query)
                | Q(description__icontains=search_query)
                | Q(disaster_type__name__icontains=search_query)
            )
            .order_by('-start_date')[:5]
        )

        type_results = (
            DisasterType.objects
            .filter(
                Q(name__icontains=search_query)
                | Q(description__icontains=search_query)
            )
            .order_by('name')[:5]
        )

        agency_results = (
            EmergencyAgency.objects
            .filter(
                Q(agency_name__icontains=search_query)
                | Q(agency_type__icontains=search_query)
                | Q(contact_number__icontains=search_query)
            )
            .order_by('agency_name')[:5]
        )

        update_results = (
            DisasterUpdate.objects
            .select_related(
                'disaster',
                'agency',
            )
            .filter(
                Q(disaster__title__icontains=search_query)
                | Q(agency__agency_name__icontains=search_query)
                | Q(update_details__icontains=search_query)
            )
            .order_by('-update_date')[:5]
        )

        citizen_results = (
            User.objects
            .filter(role='CITIZEN')
            .exclude(is_staff=True)
            .exclude(is_superuser=True)
            .filter(
                Q(username__icontains=search_query)
                | Q(first_name__icontains=search_query)
                | Q(last_name__icontains=search_query)
                | Q(email__icontains=search_query)
                | Q(phone__icontains=search_query)
            )
            .order_by('-date_joined')[:5]
        )

    total_results = (
        len(report_results)
        + len(disaster_results)
        + len(type_results)
        + len(agency_results)
        + len(update_results)
        + len(citizen_results)
    )

    context = {

        'search_query': search_query,

        'report_results': report_results,
        'disaster_results': disaster_results,
        'type_results': type_results,
        'agency_results': agency_results,
        'update_results': update_results,
        'citizen_results': citizen_results,

        'total_results': total_results,

    }

    context.update(_admin_topbar_context(request))

    return render(
        request,
        'reports/admin/search.html',
        context,
    )


# =========================================================
# USER MANAGEMENT
# =========================================================

@admin_required
def admin_users(request):

    # -----------------------------------------------------
    # BASE QUERYSET — CITIZENS ONLY
    #
    # 'CITIZEN' is currently the project's only role choice, so
    # an admin/staff account (created via Django's own
    # createsuperuser) also carries role='CITIZEN' by default.
    # Excluding staff/superuser accounts here is what actually
    # scopes this list to real, registered citizens instead of
    # also listing admin accounts.
    #
    # reports_count is annotated (rather than counted per row in
    # the template) so the citizen table avoids an N+1 query.
    # -----------------------------------------------------

    citizens_qs = (
        User.objects
        .filter(role='CITIZEN')
        .exclude(is_staff=True)
        .exclude(is_superuser=True)
    )

    users = (
        citizens_qs
        .annotate(reports_count=Count('disaster_reports', distinct=True))
        .order_by('-date_joined')
    )

    # -----------------------------------------------------
    # STATUS FILTER
    # -----------------------------------------------------

    status_filter = request.GET.get(
        'status',
        'ALL'
    ).upper()

    if status_filter == 'ACTIVE':
        users = users.filter(is_active=True)
    elif status_filter == 'INACTIVE':
        users = users.filter(is_active=False)
    else:
        status_filter = 'ALL'

    # -----------------------------------------------------
    # SEARCH
    # (username, first/last name, or email)
    # -----------------------------------------------------

    search_query = request.GET.get(
        'q',
        ''
    ).strip()

    if search_query:

        users = users.filter(
            Q(username__icontains=search_query)
            | Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
            | Q(email__icontains=search_query)
        )

    # -----------------------------------------------------
    # SUMMARY COUNTS (unaffected by filters, for the header)
    # -----------------------------------------------------

    total_citizens = citizens_qs.count()

    active_citizens = citizens_qs.filter(
        is_active=True
    ).count()

    inactive_citizens = citizens_qs.filter(
        is_active=False
    ).count()

    # -----------------------------------------------------
    # PAGINATION
    # -----------------------------------------------------

    paginator = Paginator(users, 10)

    page_obj = paginator.get_page(
        request.GET.get('page')
    )

    context = {

        'page_obj': page_obj,

        'status_filter': status_filter,
        'search_query': search_query,

        'total_citizens': total_citizens,
        'active_citizens': active_citizens,
        'inactive_citizens': inactive_citizens,

    }

    context.update(_admin_topbar_context(request))

    return render(
        request,
        'reports/admin/users.html',
        context
    )


@admin_required
def admin_user_detail(request, user_id):

    # -----------------------------------------------------
    # OBJECT-LEVEL AUTHORIZATION — CITIZEN-MANAGEMENT SCOPE ONLY
    # -----------------------------------------------------
    #
    # This page is part of the Citizen management module (reached
    # from admin_users(), which already only lists role='CITIZEN'
    # non-staff/non-superuser accounts). Without this same scoping
    # here, an admin could manually edit the URL
    # (/admin/users/<id>/) to open ANY user id — including other
    # staff/superuser admin accounts — into a page built to show
    # citizen report statistics. Matching the admin_users() query
    # exactly closes that off: a staff/superuser id (or any id
    # outside the citizen-management scope) now 404s here, exactly
    # like a nonexistent id would.
    # -----------------------------------------------------

    target_user = get_object_or_404(
        User,
        id=user_id,
        role='CITIZEN',
        is_staff=False,
        is_superuser=False,
    )

    citizen_reports_qs = DisasterReport.objects.filter(
        user=target_user
    )

    reports_count = citizen_reports_qs.count()

    # -----------------------------------------------------
    # REPORT STATUS BREAKDOWN
    #
    # The template (reports/admin/user_detail.html) has always
    # displayed pending/under_review/verified/rejected counts,
    # but this view never actually passed them, so they rendered
    # blank. Using the real DisasterReport.STATUS_CHOICES values
    # here fixes that existing data gap without changing anything
    # else about the page.
    # -----------------------------------------------------

    pending_reports_count = citizen_reports_qs.filter(
        status='PENDING'
    ).count()

    under_review_reports_count = citizen_reports_qs.filter(
        status='UNDER_REVIEW'
    ).count()

    verified_reports_count = citizen_reports_qs.filter(
        status='VERIFIED'
    ).count()

    rejected_reports_count = citizen_reports_qs.filter(
        status='REJECTED'
    ).count()

    recent_reports = (
        citizen_reports_qs
        .select_related(
            'disaster_type',
            'disaster',
        )
        .order_by('-report_date')[:5]
    )

    context = {
        'target_user': target_user,
        'reports_count': reports_count,
        'pending_reports_count': pending_reports_count,
        'under_review_reports_count': under_review_reports_count,
        'verified_reports_count': verified_reports_count,
        'rejected_reports_count': rejected_reports_count,
        'recent_reports': recent_reports,
    }

    context.update(_admin_topbar_context(request))

    return render(
        request,
        'reports/admin/user_detail.html',
        context
    )


@admin_required
def admin_user_toggle_active(request, user_id):

    # Destructive/state-changing action: POST only.
    if request.method != 'POST':
        return redirect('admin_user_detail', user_id=user_id)

    # -----------------------------------------------------
    # OBJECT-LEVEL AUTHORIZATION — CITIZEN-MANAGEMENT SCOPE ONLY
    # -----------------------------------------------------
    #
    # Same scoping as admin_user_detail() above, and for the same
    # reason: without it, a manually-edited URL let an ordinary
    # admin/staff account flip is_active on ANOTHER staff account
    # (the pre-existing checks below only ever protected
    # superusers and "don't deactivate yourself" — a non-superuser
    # staff target slipped through both). Restricting the lookup
    # to real, non-privileged citizen accounts means this endpoint
    # can no longer reach a staff/superuser id at all, regardless
    # of what it does with the flag afterward.
    # -----------------------------------------------------

    target_user = get_object_or_404(
        User,
        id=user_id,
        role='CITIZEN',
        is_staff=False,
        is_superuser=False,
    )

    # Safety rails: the admin panel must never be able to lock out
    # a superuser account, or let an admin deactivate themselves.
    # (Kept as defense-in-depth even though the scoped lookup above
    # already makes both conditions unreachable in practice.)
    if target_user.is_superuser:

        messages.error(
            request,
            "Superuser accounts can't be deactivated "
            "from the admin panel."
        )

        return redirect('admin_user_detail', user_id=user_id)

    if target_user.id == request.user.id:

        messages.error(
            request,
            "You can't deactivate your own account."
        )

        return redirect('admin_user_detail', user_id=user_id)

    target_user.is_active = not target_user.is_active

    target_user.save(
        update_fields=['is_active']
    )

    if target_user.is_active:

        messages.success(
            request,
            f"{target_user.username} has been activated."
        )

    else:

        messages.success(
            request,
            f"{target_user.username} has been deactivated."
        )

    return redirect('admin_user_detail', user_id=user_id)


# =========================================================
# DISASTER REPORT MANAGEMENT
# =========================================================

@admin_required
def admin_reports(request):

    reports = (
        DisasterReport.objects
        .select_related(
            'user',
            'disaster_type',
            'disaster',
        )
        .order_by('-report_date')
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
    else:
        reports = reports.filter(status=status_filter)

    # -----------------------------------------------------
    # DISASTER TYPE FILTER
    # -----------------------------------------------------

    type_filter = request.GET.get('type', 'ALL')

    if type_filter != 'ALL':

        reports = reports.filter(
            disaster_type__id=type_filter
        )

    # -----------------------------------------------------
    # SEARCH
    # (report ID, citizen name/username, address,
    # description, disaster type name)
    # -----------------------------------------------------

    search_query = request.GET.get(
        'q',
        ''
    ).strip()

    if search_query:

        clean_id_query = search_query.lstrip('#').strip()
        report_id_match = int(clean_id_query) if clean_id_query.isdigit() else None

        search_q = (
            Q(user__username__icontains=search_query)
            | Q(user__first_name__icontains=search_query)
            | Q(user__last_name__icontains=search_query)
            | Q(address__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(disaster_type__name__icontains=search_query)
        )

        if report_id_match is not None:
            search_q |= Q(id=report_id_match)

        reports = reports.filter(search_q)

    # -----------------------------------------------------
    # SUMMARY COUNTS (unaffected by filters)
    # -----------------------------------------------------

    total_reports = DisasterReport.objects.count()

    pending_count = DisasterReport.objects.filter(
        status='PENDING'
    ).count()

    under_review_count = DisasterReport.objects.filter(
        status='UNDER_REVIEW'
    ).count()

    verified_count = DisasterReport.objects.filter(
        status='VERIFIED'
    ).count()

    rejected_count = DisasterReport.objects.filter(
        status='REJECTED'
    ).count()

    # -----------------------------------------------------
    # PAGINATION
    # -----------------------------------------------------

    paginator = Paginator(reports, 10)

    page_obj = paginator.get_page(
        request.GET.get('page')
    )

    context = {

        'page_obj': page_obj,

        'status_filter': status_filter,
        'type_filter': type_filter,
        'search_query': search_query,

        'status_choices': DisasterReport.STATUS_CHOICES,
        'disaster_types': DisasterType.objects.order_by('name'),

        'total_reports': total_reports,
        'pending_count': pending_count,
        'under_review_count': under_review_count,
        'verified_count': verified_count,
        'rejected_count': rejected_count,

    }

    context.update(_admin_topbar_context(request))

    return render(
        request,
        'reports/admin/reports.html',
        context
    )


@admin_required
def admin_report_detail(request, report_id):

    report = get_object_or_404(
        DisasterReport.objects
        .select_related(
            'user',
            'disaster_type',
            'disaster',
        )
        .prefetch_related(
            'photos'
        ),
        id=report_id
    )

    photos = report.photos.all()

    reporter_reports_count = DisasterReport.objects.filter(
        user=report.user
    ).count()

    context = {
        'report': report,
        'photos': photos,
        'reporter_reports_count': reporter_reports_count,
        'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY,
    }

    context.update(_admin_topbar_context(request))

    return render(
        request,
        'reports/admin/report_detail.html',
        context
    )


@admin_required
def admin_report_update_status(request, report_id):

    # Destructive/state-changing action: POST only.
    if request.method != 'POST':
        return redirect('admin_report_detail', report_id=report_id)

    report = get_object_or_404(
        DisasterReport,
        id=report_id
    )

    new_status = request.POST.get('status', '').strip().upper()

    # Allowed status transition workflow:
    # PENDING -> UNDER_REVIEW
    # UNDER_REVIEW -> VERIFIED, REJECTED
    # Arbitrary jumping (e.g. PENDING -> VERIFIED or REJECTED) is rejected.
    ALLOWED_TRANSITIONS = {
        'PENDING': ['UNDER_REVIEW'],
        'UNDER_REVIEW': ['VERIFIED', 'REJECTED'],
        'VERIFIED': [],
        'REJECTED': [],
    }

    old_status = report.status

    # Idempotent re-submission (e.g. page reload or duplicate submission)
    if new_status == old_status:
        messages.info(
            request,
            f'Report #{report.id} is already marked as {report.get_status_display()}.'
        )
        return redirect('admin_report_detail', report_id=report_id)

    allowed = ALLOWED_TRANSITIONS.get(old_status, [])

    if new_status not in allowed:
        status_display_map = dict(DisasterReport.STATUS_CHOICES)
        target_display = status_display_map.get(new_status, new_status)
        messages.error(
            request,
            f'Invalid status transition: Report #{report.id} cannot be moved from '
            f'{report.get_status_display()} to {target_display}.'
        )
        return redirect('admin_report_detail', report_id=report_id)

    report.status = new_status

    report.save(
        update_fields=['status']
    )

    # -----------------------------------------------------
    # CITIZEN NOTIFICATION ON REAL STATUS TRANSITION
    # -----------------------------------------------------
    create_report_status_notification(
        report=report,
        new_status=new_status,
        actor=request.user
    )

    messages.success(
        request,
        f'Report #{report.id} marked as '
        f'{report.get_status_display()}.'
    )

    return redirect('admin_report_detail', report_id=report_id)

# =========================================================
# DISASTERS
# =========================================================

@admin_required
def admin_disasters(request):

    disasters = (
        Disaster.objects
        .select_related('disaster_type')
        .annotate(reports_count=Count('reports'))
        .order_by('-start_date')
    )

    search_query = request.GET.get('q', '').strip()

    if search_query:

        disasters = disasters.filter(
            Q(title__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(disaster_type__name__icontains=search_query)
        )

    severity_filter = request.GET.get('severity', 'ALL').upper()

    valid_severities = [
        choice[0] for choice in Disaster.SEVERITY_CHOICES
    ]

    if severity_filter not in valid_severities:
        severity_filter = 'ALL'
    else:
        disasters = disasters.filter(severity=severity_filter)

    status_filter = request.GET.get('status', 'ALL').upper()

    valid_statuses = [
        choice[0] for choice in Disaster.STATUS_CHOICES
    ]

    if status_filter not in valid_statuses:
        status_filter = 'ALL'
    else:
        disasters = disasters.filter(status=status_filter)

    paginator = Paginator(disasters, 10)

    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'severity_filter': severity_filter,
        'status_filter': status_filter,
        'severity_choices': Disaster.SEVERITY_CHOICES,
        'status_choices': Disaster.STATUS_CHOICES,
        'total_disasters': Disaster.objects.count(),
        'active_disasters_count': Disaster.objects.filter(
            status='ACTIVE'
        ).count(),
        'under_control_disasters_count': Disaster.objects.filter(
            status='UNDER_CONTROL'
        ).count(),
        'resolved_disasters_count': Disaster.objects.filter(
            status='RESOLVED'
        ).count(),
        'closed_disasters_count': Disaster.objects.filter(
            status='CLOSED'
        ).count(),
    }

    context.update(_admin_topbar_context(request))

    return render(
        request,
        'reports/admin/disasters.html',
        context
    )


def _suggested_disaster_title(report):
    """
    Sensible, editable starting title for a Disaster being created
    from a verified report. Purely a convenience prefill — the
    admin can (and often will) change it before creating the
    Disaster; it is never re-derived from the report afterwards.
    """

    disaster_type_name = report.disaster_type.name

    if report.address:
        return f'{disaster_type_name} reported in {report.address}'

    return f'{disaster_type_name} incident'


@admin_required
def admin_disaster_create(request):

    # =====================================================
    # OPTIONAL SOURCE REPORT
    # Supports both existing workflows on the same page:
    #   - Admin -> Disasters -> Add Disaster        (no report)
    #   - Report Detail -> Create Disaster from this Report
    #     (?from_report=<id>)
    # =====================================================

    from_report_raw = request.GET.get('from_report', '').strip()

    source_report = None
    source_report_photos = []

    if from_report_raw:

        try:
            from_report_id = int(from_report_raw)
        except (TypeError, ValueError):
            messages.error(request, 'Invalid report reference.')
            return redirect('admin_reports')

        source_report = get_object_or_404(
            DisasterReport.objects.select_related(
                'disaster_type',
                'user',
            ),
            id=from_report_id
        )

        # Only VERIFIED reports are eligible for disaster creation.
        # Never trust the query string / hidden UI state alone —
        # this is enforced again below, inside the transaction, on
        # every POST.
        if source_report.status != 'VERIFIED':
            messages.error(
                request,
                f'Report #{source_report.id} must be verified '
                'before it can be converted into an official '
                'disaster.'
            )
            return redirect(
                'admin_report_detail',
                report_id=source_report.id
            )

        # Duplicate prevention: a verified report can only ever
        # produce one official Disaster.
        if source_report.disaster_id:
            messages.info(
                request,
                f'Report #{source_report.id} has already been '
                'converted into an official disaster.'
            )
            return redirect(
                'admin_disaster_edit',
                disaster_id=source_report.disaster_id
            )

        source_report_photos = list(source_report.photos.all())

    # Which report-photo checkboxes should render as checked.
    # On a fresh GET, default every evidence photo to selected
    # (the admin un-checks whatever should stay internal-only). On
    # a failed POST, preserve exactly what the admin submitted.
    if request.method == 'POST':

        selected_photo_ids = set()

        for raw_id in request.POST.getlist('selected_photos'):
            try:
                selected_photo_ids.add(int(raw_id))
            except (TypeError, ValueError):
                continue

    else:

        selected_photo_ids = {
            photo.id for photo in source_report_photos
        }

    if request.method == 'POST':

        form = AdminDisasterForm(
            request.POST,
            request.FILES,
            is_create=True,
            from_report=bool(source_report),
        )

        if form.is_valid():

            disaster = None
            eligibility_error_report = None

            # =================================================
            # TRANSACTION SAFETY
            # Validate -> create Disaster -> link report ->
            # attach approved photos, all atomically, so a
            # failure never leaves a half-created Disaster or a
            # broken report relationship.
            # =================================================
            with transaction.atomic():

                locked_report = None

                if source_report:

                    # Lock the report row and re-check eligibility
                    # server-side, right before writing, so two
                    # concurrent submissions for the same report
                    # can never both succeed.
                    locked_report = (
                        DisasterReport.objects
                        .select_for_update()
                        .get(id=source_report.id)
                    )

                    if (
                        locked_report.status != 'VERIFIED'
                        or locked_report.disaster_id
                    ):
                        eligibility_error_report = locked_report
                        transaction.set_rollback(True)

                if eligibility_error_report is None:

                    disaster = form.save(commit=False)

                    if not source_report:
                        # NEVER trust a client-submitted start time
                        # for a manually-created disaster — the
                        # server always stamps the exact current
                        # timestamp, in the project's configured
                        # TIME_ZONE (Asia/Kathmandu).
                        disaster.start_date = timezone.now()

                    # For a report-based disaster, disaster.start_date
                    # is exactly what the admin reviewed/edited on
                    # the form (prefilled from
                    # report.incident_start_date — see the GET
                    # branch below) — never report.report_date and
                    # never timezone.now().

                    disaster.save()

                    if locked_report:

                        locked_report.disaster = disaster

                        locked_report.save(
                            update_fields=['disaster']
                        )

                        # ---------------------------------------
                        # OFFICIAL PHOTOS (Report -> Disaster)
                        # Only photos the admin explicitly selected
                        # here — and only photos actually owned by
                        # THIS report — ever become official,
                        # public Disaster media. Referencing the
                        # existing file directly (no re-upload) so
                        # nothing is duplicated on disk.
                        # ---------------------------------------
                        if selected_photo_ids:

                            eligible_photos = locked_report.photos.filter(
                                id__in=selected_photo_ids
                            )

                            for report_photo in eligible_photos:

                                disaster_photo = DisasterPhoto(
                                    disaster=disaster,
                                    source_report_photo=report_photo,
                                )
                                disaster_photo.image.name = (
                                    report_photo.image.name
                                )
                                disaster_photo.save()

                    else:

                        # ---------------------------------------
                        # OFFICIAL PHOTOS (Manual Admin Creation)
                        # Photos the admin explicitly uploaded
                        # while manually creating this Disaster
                        # (no source report). Saved directly as
                        # official DisasterPhoto records, with no
                        # source_report_photo link — deliberately
                        # kept separate from the report-to-disaster
                        # photo-selection flow above, and from raw
                        # DisasterReportPhoto evidence, which is
                        # never exposed through this path. Already
                        # inside the same atomic block as
                        # disaster.save(), so a failure here rolls
                        # back the whole Disaster creation instead
                        # of leaving an orphan record.
                        # ---------------------------------------
                        for photo_file in (
                            form.cleaned_data.get('official_photos')
                            or []
                        ):

                            DisasterPhoto.objects.create(
                                disaster=disaster,
                                image=photo_file,
                            )

                    # -----------------------------------------------
                    # DISASTER ALERT NOTIFICATION
                    # Exactly ONE broadcast DISASTER_ALERT is created
                    # here, inside the same atomic block as the
                    # Disaster (and its report link / official
                    # photos) above -- so a rollback anywhere in this
                    # block (including the eligibility re-check
                    # above) also rolls back the notification, and a
                    # citizen never sees an alert for a Disaster that
                    # doesn't actually exist. This is the single call
                    # site for this notification type: it never fires
                    # on edit, status change, or any other Disaster
                    # write path.
                    # -----------------------------------------------
                    create_disaster_alert_notification(
                        disaster=disaster,
                        actor=request.user,
                    )

            if eligibility_error_report is not None:

                messages.error(
                    request,
                    f'Report #{eligibility_error_report.id} is no '
                    'longer eligible for disaster creation.'
                )

                return redirect(
                    'admin_report_detail',
                    report_id=eligibility_error_report.id
                )

            if source_report:

                messages.success(
                    request,
                    'Official Disaster created successfully from '
                    f'Report #{source_report.id}.'
                )

            else:

                messages.success(
                    request,
                    f'"{disaster.title}" was created successfully.'
                )

            return redirect('admin_disasters')

    else:

        initial = {}

        if source_report:

            initial = {
                'disaster_type': source_report.disaster_type_id,
                'title': _suggested_disaster_title(source_report),
                'severity': source_report.reported_severity,
                'status': 'ACTIVE',
                'description': source_report.description,
                'address': source_report.address,
                'latitude': source_report.latitude,
                'longitude': source_report.longitude,
            }

            # Incident Start Date & Time — from the report's OWN
            # incident_start_date, never report_date (when the
            # citizen submitted the report) and never the current
            # time. Left blank if the (legacy) report never
            # recorded one; the admin must then supply it
            # explicitly (see AdminDisasterForm.clean_start_date).
            if source_report.incident_start_date:
                initial['start_date'] = timezone.localtime(
                    source_report.incident_start_date
                )

        form = AdminDisasterForm(
            is_create=True,
            from_report=bool(source_report),
            initial=initial,
        )

    context = {
        'form': form,
        'is_edit': False,
        'disaster': None,
        'source_report': source_report,
        'source_report_photos': source_report_photos,
        'selected_photo_ids': selected_photo_ids,
        'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY,
    }

    context.update(_admin_topbar_context(request))

    return render(
        request,
        'reports/admin/disaster_form.html',
        context
    )


@admin_required
def admin_disaster_edit(request, disaster_id):

    disaster = get_object_or_404(
        Disaster,
        id=disaster_id
    )

    # =====================================================
    # CLOSED DISASTER LOCK
    # A CLOSED disaster is a permanent, immutable official
    # record. Hiding the Edit button (see disasters.html /
    # disaster_detail.html) is only a UI convenience — the
    # real protection lives here, independent of the UI, so
    # this is enforced on every request regardless of how the
    # admin got here: a direct GET to this URL, a bookmarked
    # link, or a crafted/manual POST all hit this same check
    # before anything else runs.
    # =====================================================
    if disaster.status == 'CLOSED':

        messages.error(
            request,
            f'"{disaster.title}" is closed. Closed disasters '
            'are permanent records and can no longer be '
            'edited.'
        )

        return redirect('admin_disaster_detail', disaster_id=disaster.id)

    if request.method == 'POST':

        form = AdminDisasterForm(
            request.POST,
            instance=disaster,
            is_create=False,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                f'"{disaster.title}" was updated successfully.'
            )

            return redirect('admin_disasters')

    else:

        # The raw model value is UTC-aware; convert to the
        # project's current timezone (Asia/Kathmandu) before
        # handing it to the widget, so the datetime-local input
        # displays the disaster's actual Nepal start time rather
        # than its UTC equivalent.
        form = AdminDisasterForm(
            instance=disaster,
            is_create=False,
            initial={
                'start_date': timezone.localtime(disaster.start_date),
            },
        )

    context = {
        'form': form,
        'is_edit': True,
        'disaster': disaster,
        # Lightweight "Created from Report #X" traceability — only
        # ever set for Disasters created through the
        # report-to-disaster workflow (see admin_disaster_create).
        # Manually-created Disasters simply have no linked report.
        'source_report': disaster.reports.select_related('user').first(),
        'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY,
    }

    context.update(_admin_topbar_context(request))

    return render(
        request,
        'reports/admin/disaster_form.html',
        context
    )


# =========================================================
# DISASTER STATUS LIFECYCLE
# =========================================================
#
# The official Disaster lifecycle. Only ever moves forward one
# stage at a time — arbitrary jumps (e.g. ACTIVE -> RESOLVED or
# ACTIVE -> CLOSED) are never allowed. Single source of truth
# for both the Disaster Detail page (which only ever renders a
# button for the *one* legal next stage) and
# admin_disaster_update_status below (which enforces the same
# chain server-side regardless of what a client submits).
# =========================================================

DISASTER_STATUS_TRANSITIONS = {
    'ACTIVE': ['UNDER_CONTROL'],
    'UNDER_CONTROL': ['RESOLVED'],
    'RESOLVED': ['CLOSED'],
    'CLOSED': [],
}


@admin_required
def admin_disaster_detail(request, disaster_id):

    disaster = get_object_or_404(
        Disaster.objects.select_related(
            'disaster_type',
        ),
        id=disaster_id
    )

    updates = list(
        disaster.updates
        .select_related(
            'agency',
            'updated_by',
        )
        .order_by('-update_date')
    )

    latest_update = updates[0] if updates else None

    photos = list(disaster.photos.all())

    linked_reports = list(
        disaster.reports
        .select_related(
            'user',
            'disaster_type',
        )
        .order_by('-report_date')
    )

    allowed_next_statuses = DISASTER_STATUS_TRANSITIONS.get(
        disaster.status, []
    )

    next_status = (
        allowed_next_statuses[0] if allowed_next_statuses else None
    )

    status_display_map = dict(Disaster.STATUS_CHOICES)

    next_status_display = status_display_map.get(next_status)

    context = {
        'disaster': disaster,
        'updates': updates,
        'latest_update': latest_update,
        'photos': photos,
        'linked_reports': linked_reports,
        'next_status': next_status,
        'next_status_display': next_status_display,
        # Lightweight "Created from Report #X" traceability, same
        # rule as admin_disaster_edit — only ever set for
        # Disasters created through the report-to-disaster
        # workflow.
        'source_report': disaster.reports.select_related('user').first(),
        'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY,
    }

    context.update(_admin_topbar_context(request))

    return render(
        request,
        'reports/admin/disaster_detail.html',
        context
    )


@admin_required
def admin_disaster_update_status(request, disaster_id):

    # Destructive/state-changing action: POST only, never GET.
    if request.method != 'POST':
        return redirect('admin_disaster_detail', disaster_id=disaster_id)

    disaster = get_object_or_404(
        Disaster,
        id=disaster_id
    )

    new_status = request.POST.get('status', '').strip().upper()

    old_status = disaster.status

    # Idempotent re-submission (e.g. page reload/double click).
    if new_status == old_status:

        messages.info(
            request,
            f'"{disaster.title}" is already marked as '
            f'{disaster.get_status_display()}.'
        )

        return redirect('admin_disaster_detail', disaster_id=disaster_id)

    allowed = DISASTER_STATUS_TRANSITIONS.get(old_status, [])

    # Server-side enforcement of the lifecycle chain -- never
    # trusts the submitted value just because a button for it
    # exists somewhere in the UI. A crafted/manual POST with an
    # out-of-sequence or nonsense status is rejected exactly the
    # same way.
    if new_status not in allowed:

        target_display = dict(Disaster.STATUS_CHOICES).get(
            new_status, new_status or '(none)'
        )

        messages.error(
            request,
            f'Invalid status transition: "{disaster.title}" cannot '
            f'be moved from {disaster.get_status_display()} to '
            f'{target_display}.'
        )

        return redirect('admin_disaster_detail', disaster_id=disaster_id)

    disaster.status = new_status

    update_fields = ['status']

    # -----------------------------------------------------
    # RESOLVED DATE (Phase A)
    # Set exactly once, the first time this Disaster reaches
    # RESOLVED. Never overwritten afterwards -- in particular,
    # the later RESOLVED -> CLOSED transition (the only other
    # transition that can reach this branch) leaves an
    # already-set resolved_date completely untouched, so it
    # always reflects the moment the disaster was actually
    # resolved, not when it was subsequently closed out.
    # -----------------------------------------------------

    if (
        new_status in ('RESOLVED', 'CLOSED')
        and disaster.resolved_date is None
    ):

        disaster.resolved_date = timezone.now()

        update_fields.append('resolved_date')

    disaster.save(
        update_fields=update_fields
    )

    messages.success(
        request,
        f'"{disaster.title}" marked as '
        f'{disaster.get_status_display()}.'
    )

    return redirect('admin_disaster_detail', disaster_id=disaster_id)


# =========================================================
# DISASTER TYPES
# =========================================================

@admin_required
def admin_disaster_types(request):

    disaster_types = (
        DisasterType.objects
        .annotate(
            report_count=Count(
                'disaster_reports',
                distinct=True
            ),
            disaster_count=Count(
                'disasters',
                distinct=True
            ),
        )
        .order_by('name')
    )

    # -----------------------------------------------------
    # SEARCH
    # -----------------------------------------------------

    search_query = request.GET.get(
        'q',
        ''
    ).strip()

    if search_query:

        disaster_types = disaster_types.filter(
            Q(name__icontains=search_query)
            | Q(description__icontains=search_query)
        )

    # -----------------------------------------------------
    # STATUS FILTER
    # -----------------------------------------------------

    status_filter = request.GET.get(
        'status',
        'ALL'
    ).upper()

    valid_statuses = [
        'ALL',
        'ACTIVE',
        'INACTIVE',
    ]

    if status_filter not in valid_statuses:
        status_filter = 'ALL'

    if status_filter == 'ACTIVE':
        disaster_types = disaster_types.filter(
            is_active=True
        )
    elif status_filter == 'INACTIVE':
        disaster_types = disaster_types.filter(
            is_active=False
        )

    # -----------------------------------------------------
    # PAGINATION
    # -----------------------------------------------------

    paginator = Paginator(
        disaster_types,
        10
    )

    page_obj = paginator.get_page(
        request.GET.get('page')
    )

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
    }

    context.update(_admin_topbar_context(request))

    return render(
        request,
        'reports/admin/disaster_types.html',
        context
    )


@admin_required
def admin_disaster_type_create(request):

    if request.method == 'POST':

        form = AdminDisasterTypeForm(
            request.POST
        )

        if form.is_valid():

            disaster_type = form.save()

            messages.success(
                request,
                f'{disaster_type.name} was created successfully.'
            )

            return redirect(
                'admin_disaster_types'
            )

    else:

        form = AdminDisasterTypeForm(
            initial={
                'is_active': True
            }
        )

    context = {
        'form': form,
        'form_mode': 'create',
        'form_title': 'Add Disaster Type',
        'form_description': (
            'Create a new disaster category that can be used '
            'across disaster reports and disaster records.'
        ),
    }

    context.update(_admin_topbar_context(request))

    return render(
        request,
        'reports/admin/disaster_type_form.html',
        context
    )


@admin_required
def admin_disaster_type_edit(request, disaster_type_id):

    disaster_type = get_object_or_404(
        DisasterType,
        id=disaster_type_id
    )

    if request.method == 'POST':

        form = AdminDisasterTypeForm(
            request.POST,
            instance=disaster_type
        )

        if form.is_valid():

            updated_type = form.save()

            messages.success(
                request,
                f'{updated_type.name} was updated successfully.'
            )

            return redirect(
                'admin_disaster_types'
            )

    else:

        form = AdminDisasterTypeForm(
            instance=disaster_type
        )

    context = {
        'form': form,
        'disaster_type': disaster_type,
        'form_mode': 'edit',
        'form_title': 'Edit Disaster Type',
        'form_description': (
            'Update the category information and its availability '
            'across NDMS.'
        ),
    }

    context.update(_admin_topbar_context(request))

    return render(
        request,
        'reports/admin/disaster_type_form.html',
        context
    )


@admin_required
def admin_disaster_type_toggle(request, disaster_type_id):

    # Destructive/state-changing action: POST only.
    if request.method != 'POST':
        return redirect(
            'admin_disaster_types'
        )

    disaster_type = get_object_or_404(
        DisasterType,
        id=disaster_type_id
    )

    disaster_type.is_active = not disaster_type.is_active

    disaster_type.save(
        update_fields=['is_active']
    )

    if disaster_type.is_active:

        messages.success(
            request,
            f'{disaster_type.name} is now active and available for use.'
        )

    else:

        messages.success(
            request,
            f'{disaster_type.name} has been deactivated.'
        )

    return redirect(
        'admin_disaster_types'
    )


@admin_required
def admin_disaster_type_delete(request, disaster_type_id):

    # Destructive/state-changing action: POST only.
    if request.method != 'POST':
        return redirect(
            'admin_disaster_types'
        )

    disaster_type = get_object_or_404(
        DisasterType,
        id=disaster_type_id
    )

    disaster_type_name = disaster_type.name

    try:
        disaster_type.delete()

    except ProtectedError:

        messages.error(
            request,
            (
                f'{disaster_type_name} cannot be deleted because it is '
                'already used by disaster reports or disaster records. '
                'Deactivate it instead.'
            )
        )

        return redirect(
            'admin_disaster_types'
        )

    messages.success(
        request,
        f'{disaster_type_name} was deleted successfully.'
    )

    return redirect(
        'admin_disaster_types'
    )


# =========================================================
# EMERGENCY AGENCIES
# =========================================================

@admin_required
def admin_agencies(request):

    agencies = (
        EmergencyAgency.objects
        .annotate(
            response_count=Count(
                'disaster_updates',
                distinct=True
            ),
        )
        .order_by('agency_name')
    )

    search_query = request.GET.get('q', '').strip()

    if search_query:

        agencies = agencies.filter(
            Q(agency_name__icontains=search_query)
            | Q(agency_type__icontains=search_query)
            | Q(contact_number__icontains=search_query)
        )

    paginator = Paginator(agencies, 10)

    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'total_agencies': EmergencyAgency.objects.count(),
    }

    context.update(_admin_topbar_context(request))

    return render(
        request,
        'reports/admin/agencies.html',
        context
    )


@admin_required
def admin_agency_create(request):

    if request.method == 'POST':

        form = AdminEmergencyAgencyForm(
            request.POST
        )

        if form.is_valid():

            agency = form.save()

            messages.success(
                request,
                f'{agency.agency_name} was created successfully.'
            )

            return redirect(
                'admin_agencies'
            )

    else:

        form = AdminEmergencyAgencyForm()

    context = {
        'form': form,
        'form_mode': 'create',
        'form_title': 'Add Emergency Agency',
        'form_description': (
            'Add a new organization involved in disaster response '
            'and coordination.'
        ),
    }

    context.update(_admin_topbar_context(request))

    return render(
        request,
        'reports/admin/agency_form.html',
        context
    )


@admin_required
def admin_agency_edit(request, agency_id):

    agency = get_object_or_404(
        EmergencyAgency,
        id=agency_id
    )

    if request.method == 'POST':

        form = AdminEmergencyAgencyForm(
            request.POST,
            instance=agency
        )

        if form.is_valid():

            updated_agency = form.save()

            messages.success(
                request,
                f'{updated_agency.agency_name} was updated successfully.'
            )

            return redirect(
                'admin_agencies'
            )

    else:

        form = AdminEmergencyAgencyForm(
            instance=agency
        )

    context = {
        'form': form,
        'agency': agency,
        'form_mode': 'edit',
        'form_title': 'Edit Emergency Agency',
        'form_description': (
            'Update this agency\'s information.'
        ),
    }

    context.update(_admin_topbar_context(request))

    return render(
        request,
        'reports/admin/agency_form.html',
        context
    )


@admin_required
def admin_agency_delete(request, agency_id):

    # Destructive/state-changing action: POST only.
    if request.method != 'POST':
        return redirect(
            'admin_agencies'
        )

    agency = get_object_or_404(
        EmergencyAgency,
        id=agency_id
    )

    agency_name = agency.agency_name

    try:
        agency.delete()

    except ProtectedError:

        messages.error(
            request,
            (
                f'{agency_name} cannot be deleted because it is '
                'already associated with response updates.'
            )
        )

        return redirect(
            'admin_agencies'
        )

    messages.success(
        request,
        f'{agency_name} was deleted successfully.'
    )

    return redirect(
        'admin_agencies'
    )


# =========================================================
# RESPONSE UPDATES
# =========================================================

@admin_required
def admin_response_updates(request):

    updates = (
        DisasterUpdate.objects
        .select_related(
            'disaster',
            'agency',
            'updated_by',
        )
        .order_by('-update_date')
    )

    search_query = request.GET.get('q', '').strip()

    if search_query:

        updates = updates.filter(
            Q(disaster__title__icontains=search_query)
            | Q(agency__agency_name__icontains=search_query)
            | Q(update_details__icontains=search_query)
        )

    status_filter = request.GET.get('status', 'ALL').upper()

    valid_statuses = [
        choice[0] for choice in DisasterUpdate.RESPONSE_STATUS_CHOICES
    ]

    if status_filter not in valid_statuses:
        status_filter = 'ALL'
    else:
        updates = updates.filter(response_status=status_filter)

    paginator = Paginator(updates, 10)

    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'status_choices': DisasterUpdate.RESPONSE_STATUS_CHOICES,
        'total_updates': DisasterUpdate.objects.count(),
    }

    context.update(_admin_topbar_context(request))

    return render(
        request,
        'reports/admin/response_updates.html',
        context
    )


def _safe_next_url(raw_next):
    """
    Only ever follow an internal, site-relative "next" redirect
    target (e.g. back to the Disaster Detail page a Response
    Update was created/edited/deleted from) -- never an
    absolute/external URL, so this can never be turned into an
    open redirect.
    """

    raw_next = (raw_next or '').strip()

    if raw_next.startswith('/') and not raw_next.startswith('//'):
        return raw_next

    return ''


@admin_required
def admin_response_update_create(request):

    next_url = _safe_next_url(
        request.POST.get('next') or request.GET.get('next')
    )

    if request.method == 'POST':

        form = AdminResponseUpdateForm(
            request.POST
        )

        if form.is_valid():

            update = form.save(commit=False)
            update.updated_by = request.user
            update.save()

            messages.success(
                request,
                'Response update created successfully.'
            )

            return redirect(next_url or 'admin_response_updates')

    else:

        # If arriving from a Disaster Detail page ("Add Response
        # Update"), preselect that Disaster -- the existing
        # Disaster selector on this form is preserved as-is, this
        # only changes its default value.
        initial = {}

        disaster_id_raw = request.GET.get('disaster', '').strip()

        if disaster_id_raw:

            try:
                initial['disaster'] = int(disaster_id_raw)
            except (TypeError, ValueError):
                pass

        form = AdminResponseUpdateForm(initial=initial)

    context = {
        'form': form,
        'form_mode': 'create',
        'form_title': 'Add Response Update',
        'form_description': (
            'Record a new agency response action for a disaster.'
        ),
        'next_url': next_url,
    }

    context.update(_admin_topbar_context(request))

    return render(
        request,
        'reports/admin/response_update_form.html',
        context
    )


@admin_required
def admin_response_update_edit(request, update_id):

    update = get_object_or_404(
        DisasterUpdate.objects.select_related('disaster'),
        id=update_id
    )

    next_url = _safe_next_url(
        request.POST.get('next') or request.GET.get('next')
    )

    # CLOSED DISASTER PROTECTION -- a closed disaster's record is
    # finalized; its historical response updates can no longer be
    # edited. Blocked here (both GET and POST) rather than only
    # hidden in the UI.
    if update.disaster.status == 'CLOSED':

        messages.error(
            request,
            f'"{update.disaster.title}" is closed. Response '
            'updates for a closed disaster can no longer be '
            'edited.'
        )

        return redirect(next_url or 'admin_response_updates')

    if request.method == 'POST':

        form = AdminResponseUpdateForm(
            request.POST,
            instance=update
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                'Response update updated successfully.'
            )

            return redirect(next_url or 'admin_response_updates')

    else:

        form = AdminResponseUpdateForm(
            instance=update
        )

    context = {
        'form': form,
        'update': update,
        'form_mode': 'edit',
        'form_title': 'Edit Response Update',
        'form_description': (
            'Update this response update\'s information.'
        ),
        'next_url': next_url,
    }

    context.update(_admin_topbar_context(request))

    return render(
        request,
        'reports/admin/response_update_form.html',
        context
    )


@admin_required
def admin_response_update_delete(request, update_id):

    next_url = _safe_next_url(request.POST.get('next'))

    # Destructive/state-changing action: POST only.
    if request.method != 'POST':
        return redirect(next_url or 'admin_response_updates')

    update = get_object_or_404(
        DisasterUpdate.objects.select_related('disaster'),
        id=update_id
    )

    # CLOSED DISASTER PROTECTION -- see admin_response_update_edit
    # above; a closed disaster's historical response updates can
    # no longer be deleted either.
    if update.disaster.status == 'CLOSED':

        messages.error(
            request,
            f'"{update.disaster.title}" is closed. Response '
            'updates for a closed disaster can no longer be '
            'deleted.'
        )

        return redirect(next_url or 'admin_response_updates')

    update.delete()

    messages.success(
        request,
        'Response update deleted successfully.'
    )

    return redirect(next_url or 'admin_response_updates')


# =========================================================
# NOTIFICATIONS
# =========================================================

@admin_required
def admin_notifications(request):

    notifications = (
        Notification.objects
        .select_related(
            'disaster',
            'published_by',
            'recipient',
        )
        .order_by('-publish_date')
    )

    search_query = request.GET.get('q', '').strip()

    if search_query:

        notifications = notifications.filter(
            Q(title__icontains=search_query)
            | Q(message__icontains=search_query)
            | Q(disaster__title__icontains=search_query)
            | Q(recipient__first_name__icontains=search_query)
            | Q(recipient__last_name__icontains=search_query)
            | Q(recipient__username__icontains=search_query)
        )

    type_filter = request.GET.get('type', 'ALL').upper()

    if type_filter == 'BROADCAST':

        notifications = notifications.filter(recipient__isnull=True)

    elif type_filter == 'PERSONAL':

        notifications = notifications.filter(recipient__isnull=False)

    else:

        type_filter = 'ALL'

    paginator = Paginator(notifications, 10)

    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'type_filter': type_filter,
        'total_notifications': Notification.objects.count(),
    }

    context.update(_admin_topbar_context(request))

    return render(
        request,
        'reports/admin/notifications.html',
        context
    )


@admin_required
def admin_notification_create(request):

    if request.method == 'POST':

        form = NotificationForm(
            request.POST
        )

        if form.is_valid():

            notification = form.save(commit=False)
            notification.published_by = request.user
            notification.save()

            messages.success(
                request,
                'Notification sent successfully.'
            )

            return redirect(
                'admin_notifications'
            )

    else:

        form = NotificationForm()

    context = {
        'form': form,
        'form_mode': 'create',
        'form_title': 'Send Notification',
        'form_description': (
            'Send an important alert or update to citizens.'
        ),
    }

    context.update(_admin_topbar_context(request))

    return render(
        request,
        'reports/admin/notification_form.html',
        context
    )


@admin_required
def admin_notification_detail(request, notification_id):

    notification = get_object_or_404(
        Notification.objects.select_related(
            'disaster',
            'published_by',
            'recipient',
        ),
        id=notification_id
    )

    context = {
        'notification': notification,
    }

    context.update(_admin_topbar_context(request))

    return render(
        request,
        'reports/admin/notification_detail.html',
        context
    )


# =========================================================
# FEEDBACK
# =========================================================

@admin_required
def admin_feedback(request):

    feedback_qs = (
        Feedback.objects
        .select_related('user')
        .order_by('-created_at')
    )

    search_query = request.GET.get('q', '').strip()

    if search_query:

        feedback_qs = feedback_qs.filter(
            Q(user__username__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(message__icontains=search_query)
        )

    rating_filter = request.GET.get('rating', 'ALL')

    if rating_filter != 'ALL':

        try:
            feedback_qs = feedback_qs.filter(
                rating=int(rating_filter)
            )
        except (TypeError, ValueError):
            rating_filter = 'ALL'

    paginator = Paginator(feedback_qs, 10)

    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'rating_filter': rating_filter,
        'total_feedback': Feedback.objects.count(),
    }

    context.update(_admin_topbar_context(request))

    return render(
        request,
        'reports/admin/feedback.html',
        context
    )


@admin_required
def admin_feedback_detail(request, feedback_id):

    feedback_item = get_object_or_404(
        Feedback.objects.select_related('user'),
        id=feedback_id
    )

    context = {
        'feedback_item': feedback_item,
    }

    context.update(_admin_topbar_context(request))

    return render(
        request,
        'reports/admin/feedback_detail.html',
        context
    )


# =========================================================
# SUPPORT REQUESTS
# =========================================================

@admin_required
def admin_support_requests(request):

    support_requests = (
        SupportRequest.objects
        .select_related('user')
        .order_by('-created_at')
    )

    search_query = request.GET.get('q', '').strip()

    if search_query:

        support_requests = support_requests.filter(
            Q(user__username__icontains=search_query)
            | Q(subject__icontains=search_query)
            | Q(description__icontains=search_query)
        )

    issue_type_filter = request.GET.get('issue_type', 'ALL').upper()

    valid_issue_types = [
        choice[0] for choice in SupportRequest.ISSUE_TYPE_CHOICES
    ]

    if issue_type_filter not in valid_issue_types:
        issue_type_filter = 'ALL'
    else:
        support_requests = support_requests.filter(
            issue_type=issue_type_filter
        )

    paginator = Paginator(support_requests, 10)

    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'issue_type_filter': issue_type_filter,
        'total_support_requests': SupportRequest.objects.count(),
    }

    context.update(_admin_topbar_context(request))

    return render(
        request,
        'reports/admin/support_requests.html',
        context
    )


@admin_required
def admin_support_request_detail(request, request_id):

    support_request = get_object_or_404(
        SupportRequest.objects.select_related('user'),
        id=request_id
    )

    response_form = AdminSupportRequestResponseForm(
        instance=support_request
    )

    context = {
        'support_request': support_request,
        'response_form': response_form,
    }

    context.update(_admin_topbar_context(request))

    return render(
        request,
        'reports/admin/support_request_detail.html',
        context
    )


# =========================================================
# ADMIN RESPONSE TO SUPPORT REQUEST (Phase A)
# =========================================================
#
# Lets an admin update a SupportRequest's status and/or write
# the reply the citizen sees on their own Help & Support page.
# Any authenticated admin/staff account may respond to any
# request (matching the existing admin_support_request_detail
# view -- there is no per-admin assignment concept in this
# project), but only an admin/staff account at all, enforced by
# @admin_required exactly like every other admin write.
#
# NOTIFICATION DE-DUPLICATION:
# A citizen-facing Notification (and `responded_at`) is only
# ever created/updated when the response TEXT actually changes
# to something non-empty -- never on every save. This means:
#   - Changing only `status` (e.g. OPEN -> IN_PROGRESS with no
#     reply yet) never fires a notification.
#   - Re-submitting the exact same, unchanged response text
#     (e.g. a page reload/duplicate submission) never fires a
#     second notification -- this mirrors the existing
#     "idempotent re-submission" pattern already used by
#     admin_report_update_status/admin_disaster_update_status.
#   - Editing an already-sent response to different wording
#     DOES fire a new notification, since that is a genuinely
#     new message the citizen hasn't seen yet.
# =========================================================

@admin_required
def admin_support_request_respond(request, request_id):

    # Destructive/state-changing action: POST only, never GET.
    if request.method != 'POST':
        return redirect(
            'admin_support_request_detail',
            request_id=request_id
        )

    support_request = get_object_or_404(
        SupportRequest.objects.select_related('user'),
        id=request_id
    )

    previous_response = support_request.admin_response

    form = AdminSupportRequestResponseForm(
        request.POST,
        instance=support_request
    )

    if not form.is_valid():

        messages.error(
            request,
            'Please fix the errors below and try again.'
        )

        context = {
            'support_request': support_request,
            'response_form': form,
        }

        context.update(_admin_topbar_context(request))

        return render(
            request,
            'reports/admin/support_request_detail.html',
            context
        )

    updated_request = form.save(commit=False)

    new_response = updated_request.admin_response

    response_changed = bool(
        new_response
        and new_response != (previous_response or '')
    )

    update_fields = ['status', 'admin_response']

    if response_changed:

        updated_request.responded_at = timezone.now()

        update_fields.append('responded_at')

    updated_request.save(update_fields=update_fields)

    if response_changed:

        # Reuses the existing Notification model exactly as
        # every other notification type does, via the same
        # models.py-helper-function pattern used by
        # create_disaster_alert_notification /
        # create_report_status_notification.
        create_support_response_notification(
            updated_request,
            request.user
        )

    messages.success(
        request,
        f'Support request #{updated_request.id} was updated.'
    )

    return redirect(
        'admin_support_request_detail',
        request_id=updated_request.id
    )


# =========================================================
# MARK SUPPORT REQUEST NOTIFICATION AS READ
# =========================================================
#
# Backs the "New Support Request" items in the admin alert
# dropdown (see _admin_topbar_context). Reuses the exact same
# Notification / NotificationRead models and the same
# "get_or_create on click, then redirect" pattern already used
# by reports.views.mark_notification_read on the citizen side --
# no new notification system, no new read/unread mechanism.
#
# Marking a notification read never touches the SupportRequest
# itself (status, assignment, etc. are untouched) -- only the
# NotificationRead row for this admin is created.
# =========================================================

@admin_required
def admin_mark_support_notification_read(request, notification_id):

    if request.method != 'POST':

        return HttpResponseForbidden(
            'Only POST requests are allowed.'
        )

    notification = get_object_or_404(
        Notification,
        id=notification_id
    )

    # A support-request notification is personal to the admin
    # it was created for -- unlike the citizen-facing broadcast
    # notifications, there is no "recipient is null" case here.
    if notification.recipient_id != request.user.id:

        return HttpResponseForbidden(
            'You are not authorized to access this notification.'
        )

    NotificationRead.objects.get_or_create(
        user=request.user,
        notification=notification
    )

    if notification.support_request_id is not None:

        return redirect(
            'admin_support_request_detail',
            request_id=notification.support_request_id
        )

    return redirect('admin_notifications')


# =========================================================
# ADMIN ACCOUNT — MY PROFILE
# =========================================================

@admin_required
def admin_profile(request):

    profile_form = ProfileUpdateForm(instance=request.user)
    avatar_form = AvatarUploadForm(instance=request.user)

    if request.method == 'POST' and request.POST.get('form') == 'profile':

        profile_form = ProfileUpdateForm(
            request.POST,
            instance=request.user
        )

        if profile_form.is_valid():

            profile_form.save()

            messages.success(
                request,
                'Your profile has been updated.'
            )

            return redirect('admin_profile')

    elif request.method == 'POST' and request.POST.get('form') == 'avatar':

        avatar_form = AvatarUploadForm(
            request.POST,
            request.FILES,
            instance=request.user
        )

        if avatar_form.is_valid():

            avatar_form.save()

            messages.success(
                request,
                'Your profile photo has been updated.'
            )

            return redirect('admin_profile')

    elif request.method == 'POST' and request.POST.get('form') == 'avatar_remove':

        # -----------------------------------------------------
        # REMOVE AVATAR
        #
        # AvatarUploadForm.clean_avatar() requires a file, so it
        # cannot express "clear the current photo" — this branch
        # mirrors the citizen-side remove_photo() view (same
        # delete/clear/save sequence) without adding a second
        # view or URL, keeping the single admin_profile()
        # POST-discriminator architecture intact.
        # -----------------------------------------------------

        if request.user.avatar:

            request.user.avatar.delete(
                save=False
            )

            request.user.avatar = None

            request.user.save()

            messages.success(
                request,
                'Your profile photo has been removed.'
            )

        return redirect('admin_profile')

    context = {
        'profile_form': profile_form,
        'avatar_form': avatar_form,
    }

    context.update(_admin_topbar_context(request))

    return render(
        request,
        'reports/admin/profile.html',
        context
    )


# =========================================================
# ADMIN ACCOUNT — SETTINGS
# =========================================================

@admin_required
def admin_settings(request):

    user_settings, _created = UserSettings.objects.get_or_create(
        user=request.user
    )

    settings_form = AdminSettingsForm(instance=user_settings)
    password_form = PasswordChangeForm(user=request.user)

    if request.method == 'POST' and request.POST.get('form') == 'settings':

        settings_form = AdminSettingsForm(
            request.POST,
            instance=user_settings
        )

        if settings_form.is_valid():

            settings_form.save()

            messages.success(
                request,
                'Your settings have been saved.'
            )

            return redirect('admin_settings')

    elif request.method == 'POST' and request.POST.get('form') == 'password':

        password_form = PasswordChangeForm(
            user=request.user,
            data=request.POST
        )

        if password_form.is_valid():

            password_form.save()

            update_session_auth_hash(request, password_form.user)

            messages.success(
                request,
                'Your password has been changed successfully.'
            )

            return redirect('admin_settings')

    context = {
        'settings_form': settings_form,
        'password_form': password_form,
    }

    context.update(_admin_topbar_context(request))

    return render(
        request,
        'reports/admin/settings.html',
        context
    )


# =========================================================
# ADMIN ACCOUNT — HELP & SUPPORT
# =========================================================

@admin_required
def admin_help_support(request):

    context = {}

    context.update(_admin_topbar_context(request))

    return render(
        request,
        'reports/admin/help_support.html',
        context
    )


# =========================================================
# ADMIN ACCOUNT — SEND FEEDBACK
# =========================================================

@admin_required
def admin_send_feedback(request):

    if request.method != 'POST':
        return redirect('admin_help_support')

    form = FeedbackForm(request.POST)

    if form.is_valid():

        feedback = form.save(commit=False)
        feedback.user = request.user
        feedback.save()

        messages.success(
            request,
            'Thank you — your feedback has been sent.'
        )

    else:

        messages.error(
            request,
            'Please enter a valid email and message before sending.'
        )

    return redirect('admin_help_support')