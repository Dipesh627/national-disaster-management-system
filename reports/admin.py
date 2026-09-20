from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    User,
    DisasterType,
    DisasterReport,
    DisasterReportPhoto,
    Disaster,
    EmergencyAgency,
    DisasterUpdate,
    Notification,
    Feedback,
    UserSettings,
    SupportRequest,
)

class DisasterReportPhotoInline(admin.TabularInline):
    model = DisasterReportPhoto
    extra = 0
    readonly_fields = (
        'uploaded_at',
    )

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        'username',
        'full_name',
        'email',
        'phone',
        'role',
        'is_active',
    ) 

    list_filter = (
        'role',
        'is_active',
    )

    search_fields = (
        'username',
        'full_name',
        'email',
        'phone',
    )


@admin.register(DisasterType)
class DisasterTypeAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'is_active',
        'created_date',
    )

    list_filter = (
        'is_active',
    )

    search_fields = (
        'name',
        'description',
    )

    ordering = (
        'name',
    )


@admin.register(DisasterReport)
class DisasterReportAdmin(admin.ModelAdmin):
    inlines = (
        DisasterReportPhotoInline,
    )

    list_display = (
        'id',
        'user',
        'disaster_type',
        'reported_severity',
        'disaster',
        'status',
        'report_date',
    )

    list_filter = (
        'status',
        'reported_severity',
        'disaster_type',
        'disaster',
    )

    search_fields = (
        'description',
        'address',
        'user__username',
        'user__full_name',
        'disaster__title',
    )

    ordering = (
        '-report_date',
    )

    readonly_fields = (
        'report_date',
    )


@admin.register(Disaster)
class DisasterAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'disaster_type',
        'severity',
        'status',
        'start_date',
    )

    list_filter = (
        'disaster_type',
        'severity',
        'status',
    )

    search_fields = (
        'title',
        'description',
    )

    ordering = (
        '-start_date',
    )



@admin.register(EmergencyAgency)
class EmergencyAgencyAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'agency_name',
        'agency_type',
        'contact_number',
    )

    list_filter = (
        'agency_type',
    )

    search_fields = (
        'agency_name',
        'agency_type',
        'contact_number',
    )

    ordering = (
        'agency_name',
    )



@admin.register(DisasterUpdate)
class DisasterUpdateAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'disaster',
        'agency',
        'updated_by',
        'response_status',
        'update_date',
    )

    list_filter = (
        'response_status',
        'agency',
    )

    search_fields = (
        'disaster__title',
        'agency__agency_name',
        'updated_by__username',
        'update_details',
    )

    ordering = (
        '-update_date',
    )

    readonly_fields = (
        'update_date',
    )



@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'disaster',
        'published_by',
        'publish_date',
    )

    list_filter = (
        'disaster',
        'publish_date',
    )

    search_fields = (
        'title',
        'message',
        'disaster__title',
        'published_by__username',
    )

    readonly_fields = (
        'publish_date',
    )

    ordering = (
        '-publish_date',
    )


@admin.register(DisasterReportPhoto)
class DisasterReportPhotoAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'report',
        'uploaded_at',
    )

    list_filter = (
        'uploaded_at',
    )

    search_fields = (
        'report__id',
        'report__description',
        'report__user__username',
    )

    ordering = (
        '-uploaded_at',
    )

    readonly_fields = (
        'uploaded_at',
    )


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'user',
        'email',
        'rating',
        'message',
        'created_at',
    )

    list_filter = (
        'rating',
        'created_at',
    )

    search_fields = (
        'user__username',
        'email',
        'message',
    )

    ordering = (
        '-created_at',
    )

    readonly_fields = (
        'created_at',
    )

@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'user',
        'language',
        'time_zone',
        'date_format',
        'updated_at',
    )

    list_filter = (
        'language',
    )

    search_fields = (
        'user__username',
        'user__full_name',
    )

    ordering = (
        '-updated_at',
    )

    readonly_fields = (
        'updated_at',
    )


@admin.register(SupportRequest)
class SupportRequestAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'user',
        'issue_type',
        'subject',
        'created_at',
    )

    list_filter = (
        'issue_type',
        'created_at',
    )

    search_fields = (
        'user__username',
        'user__full_name',
        'subject',
        'description',
    )

    ordering = (
        '-created_at',
    )

    readonly_fields = (
        'created_at',
    )