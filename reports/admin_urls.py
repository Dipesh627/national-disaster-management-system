from django.urls import path

from . import admin_views


urlpatterns = [

    # =========================================================
    # ADMIN AUTHENTICATION
    # =========================================================

    path(
        'login/',
        admin_views.admin_login,
        name='admin_login'
    ),

    path(
        'logout/',
        admin_views.admin_logout,
        name='admin_logout'
    ),


    # =========================================================
    # ADMIN DASHBOARD
    # =========================================================

    path(
        '',
        admin_views.admin_dashboard,
        name='admin_dashboard'
    ),

    path(
        'dashboard/',
        admin_views.admin_dashboard,
        name='admin_dashboard_explicit'
    ),


    # =========================================================
    # GLOBAL SEARCH
    # =========================================================

    path(
        'search/',
        admin_views.admin_global_search,
        name='admin_global_search'
    ),


    # =========================================================
    # USER MANAGEMENT
    # =========================================================

    path(
        'users/',
        admin_views.admin_users,
        name='admin_users'
    ),

    path(
        'users/<int:user_id>/',
        admin_views.admin_user_detail,
        name='admin_user_detail'
    ),

    path(
        'users/<int:user_id>/toggle-active/',
        admin_views.admin_user_toggle_active,
        name='admin_user_toggle_active'
    ),


    # =========================================================
    # DISASTER REPORTS
    # =========================================================

    path(
        'reports/',
        admin_views.admin_reports,
        name='admin_reports'
    ),

    path(
        'reports/<int:report_id>/',
        admin_views.admin_report_detail,
        name='admin_report_detail'
    ),

    path(
        'reports/<int:report_id>/update-status/',
        admin_views.admin_report_update_status,
        name='admin_report_update_status'
    ),


    # =========================================================
    # DISASTERS
    # =========================================================

    path(
        'disasters/',
        admin_views.admin_disasters,
        name='admin_disasters'
    ),

    path(
        'disasters/add/',
        admin_views.admin_disaster_create,
        name='admin_disaster_create'
    ),

    path(
        'disasters/<int:disaster_id>/',
        admin_views.admin_disaster_detail,
        name='admin_disaster_detail'
    ),

    path(
        'disasters/<int:disaster_id>/edit/',
        admin_views.admin_disaster_edit,
        name='admin_disaster_edit'
    ),

    path(
        'disasters/<int:disaster_id>/update-status/',
        admin_views.admin_disaster_update_status,
        name='admin_disaster_update_status'
    ),


    # =========================================================
    # DISASTER TYPES
    # =========================================================

    path(
        'disaster-types/',
        admin_views.admin_disaster_types,
        name='admin_disaster_types'
    ),

    path(
        'disaster-types/add/',
        admin_views.admin_disaster_type_create,
        name='admin_disaster_type_create'
    ),

    path(
        'disaster-types/<int:disaster_type_id>/edit/',
        admin_views.admin_disaster_type_edit,
        name='admin_disaster_type_edit'
    ),

    path(
        'disaster-types/<int:disaster_type_id>/toggle/',
        admin_views.admin_disaster_type_toggle,
        name='admin_disaster_type_toggle'
    ),

    path(
        'disaster-types/<int:disaster_type_id>/delete/',
        admin_views.admin_disaster_type_delete,
        name='admin_disaster_type_delete'
    ),


    # =========================================================
    # EMERGENCY AGENCIES
    # =========================================================

    path(
        'agencies/',
        admin_views.admin_agencies,
        name='admin_agencies'
    ),

    path(
        'agencies/add/',
        admin_views.admin_agency_create,
        name='admin_agency_create'
    ),

    path(
        'agencies/<int:agency_id>/edit/',
        admin_views.admin_agency_edit,
        name='admin_agency_edit'
    ),

    path(
        'agencies/<int:agency_id>/delete/',
        admin_views.admin_agency_delete,
        name='admin_agency_delete'
    ),


    # =========================================================
    # RESPONSE UPDATES
    # =========================================================

    path(
        'response-updates/',
        admin_views.admin_response_updates,
        name='admin_response_updates'
    ),

    path(
        'response-updates/create/',
        admin_views.admin_response_update_create,
        name='admin_response_update_create'
    ),

    path(
        'response-updates/<int:update_id>/edit/',
        admin_views.admin_response_update_edit,
        name='admin_response_update_edit'
    ),

    path(
        'response-updates/<int:update_id>/delete/',
        admin_views.admin_response_update_delete,
        name='admin_response_update_delete'
    ),


    # =========================================================
    # NOTIFICATIONS
    # =========================================================

    path(
        'notifications/',
        admin_views.admin_notifications,
        name='admin_notifications'
    ),

    path(
        'notifications/create/',
        admin_views.admin_notification_create,
        name='admin_notification_create'
    ),

    path(
        'notifications/<int:notification_id>/',
        admin_views.admin_notification_detail,
        name='admin_notification_detail'
    ),


    # =========================================================
    # FEEDBACK
    # =========================================================

    path(
        'feedback/',
        admin_views.admin_feedback,
        name='admin_feedback'
    ),

    path(
        'feedback/<int:feedback_id>/',
        admin_views.admin_feedback_detail,
        name='admin_feedback_detail'
    ),


    # =========================================================
    # SUPPORT REQUESTS
    # =========================================================

    path(
        'support-requests/',
        admin_views.admin_support_requests,
        name='admin_support_requests'
    ),

    path(
        'support-requests/<int:request_id>/',
        admin_views.admin_support_request_detail,
        name='admin_support_request_detail'
    ),

    path(
        'support-requests/<int:request_id>/respond/',
        admin_views.admin_support_request_respond,
        name='admin_support_request_respond'
    ),

    path(
        'support-notifications/<int:notification_id>/read/',
        admin_views.admin_mark_support_notification_read,
        name='admin_mark_support_notification_read'
    ),


    # =========================================================
    # ADMIN PROFILE
    # =========================================================

    path(
        'profile/',
        admin_views.admin_profile,
        name='admin_profile'
    ),


    # =========================================================
    # ADMIN SETTINGS
    # =========================================================

    path(
        'settings/',
        admin_views.admin_settings,
        name='admin_settings'
    ),


    # =========================================================
    # HELP & SUPPORT
    # =========================================================

    path(
        'help-support/',
        admin_views.admin_help_support,
        name='admin_help_support'
    ),

    path(
        'help-support/send-feedback/',
        admin_views.admin_send_feedback,
        name='admin_send_feedback'
    ),
]