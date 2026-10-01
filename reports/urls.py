from django.urls import path
from django.contrib.auth import views as auth_views

from . import views


urlpatterns = [

    # =====================================================
    # PUBLIC
    # =====================================================

    path(
        '',
        views.home,
        name='home'
    ),

    path(
        'about/',
        views.about,
        name='about'
    ),

    path(
        'feedback/',
        views.submit_feedback,
        name='submit_feedback'
    ),

    path(
        'disasters/',
        views.disaster_list,
        name='disaster_list'
    ),

    path(
        'disasters/guidelines/',
        views.disaster_guidelines,
        name='disaster_guidelines'
    ),

    path(
        'disasters/<int:disaster_id>/',
        views.disaster_detail,
        name='disaster_detail'
    ),

    path(
        'emergency-agencies/',
        views.emergency_agencies,
        name='emergency_agencies'
    ),

    path(
        'terms/',
        views.terms,
        name='terms'
    ),

    path(
        'privacy/',
        views.privacy,
        name='privacy'
    ),


    # =====================================================
    # AUTHENTICATION
    # =====================================================

    path(
        'register/',
        views.register,
        name='register'
    ),

    path(
        'login/',
        views.user_login,
        name='login'
    ),

    path(
        'logout/',
        views.user_logout,
        name='logout'
    ),


    # =====================================================
    # GOOGLE SIGN-IN ("Continue with Google")
    # =====================================================

    path(
        'login/google/',
        views.google_login,
        name='google_login'
    ),

    path(
        'login/google/callback/',
        views.google_callback,
        name='google_callback'
    ),

    path(
        'login/google/confirm/',
        views.google_signup_confirm,
        name='google_signup_confirm'
    ),

    # Live "Username available" hint for the Complete Your NDMS
    # Profile page above. Advisory only; see views.google_username_check.
    path(
        'login/google/confirm/username-check/',
        views.google_username_check,
        name='google_username_check'
    ),


    # =====================================================
    # FORGOT PASSWORD / PASSWORD RESET
    # =====================================================

    path(
        'forgot-password/',
        auth_views.PasswordResetView.as_view(
            template_name='reports/forgot_password.html',
            email_template_name='reports/password_reset_email.html',
            subject_template_name='reports/password_reset_subject.txt',
            success_url='/password-reset-sent/'
        ),
        name='password_reset'
    ),

    path(
        'password-reset-sent/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='reports/password_reset_sent.html'
        ),
        name='password_reset_done'
    ),

    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='reports/password_reset_confirm.html',
            success_url='/password-reset-complete/'
        ),
        name='password_reset_confirm'
    ),

    path(
        'password-reset-complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='reports/password_reset_complete.html'
        ),
        name='password_reset_complete'
    ),


    # =====================================================
    # DASHBOARD
    # =====================================================

    path(
        'dashboard/',
        views.dashboard,
        name='dashboard'
    ),


    # =====================================================
    # CITIZEN REPORTING
    # =====================================================

    path(
        'report/',
        views.create_disaster_report,
        name='create_disaster_report'
    ),

    path(
        'my-reports/',
        views.my_reports,
        name='my_reports'
    ),

    path(
        'report/<int:report_id>/',
        views.report_detail,
        name='report_detail'
    ),

    path(
        'report/<int:report_id>/delete/',
        views.delete_report,
        name='delete_report'
    ),


    # =====================================================
    # ALERTS
    # =====================================================

    path(
        'alerts/',
        views.alerts,
        name='alerts'
    ),


    # =====================================================
    # MY PROFILE
    # =====================================================

    path(
        'profile/',
        views.profile,
        name='profile'
    ),

    path(
        'profile/change-photo/',
        views.change_photo,
        name='change_photo'
    ),

    path(
        'profile/remove-photo/',
        views.remove_photo,
        name='remove_photo'
    ),

    path(
        'profile/change-password/',
        views.NDMSPasswordChangeView.as_view(),
        name='password_change'
    ),


    # =====================================================
    # SETTINGS
    # =====================================================

    path(
        'settings/',
        views.settings_view,
        name='settings'
    ),


    # =====================================================
    # HELP & SUPPORT
    # =====================================================

    path(
        'help-support/',
        views.help_support,
        name='help_support'
    ),


    # =====================================================
    # NOTIFICATIONS
    # =====================================================

    path(
        'notification/<int:notification_id>/read/',
        views.mark_notification_read,
        name='mark_notification_read'
    ),

    path(
        'notification/<int:notification_id>/',
        views.notification_detail,
        name='notification_detail'
    ),

    path(
        'notifications/read-all/',
        views.mark_all_notifications_read,
        name='mark_all_notifications_read'
    ),

    path(
        'disasters/mark-alerts-read/',
        views.mark_disaster_alerts_read,
        name='mark_disaster_alerts_read'
    ),

]