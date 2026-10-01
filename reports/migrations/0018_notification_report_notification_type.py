# Adds the two fields the NDMS Citizen Notification System needs
# to support report-status-lifecycle notifications (Report
# Received / Under Review / Verified / Rejected):
#
#   - Notification.report:
#       optional link back to the DisasterReport a notification
#       is about, so the topbar dropdown / Alerts page / detail
#       page can route straight to the existing Report Details
#       page instead of guessing a report id out of the message
#       text.
#
#   - Notification.notification_type:
#       lets the citizen notification UI pick the right icon and
#       contextual color (received / under review / verified /
#       rejected / disaster alert / general) without inspecting
#       title/message strings.
#
# Both fields are additive and default-safe: every existing
# Notification row becomes notification_type='GENERAL',
# report=NULL, so no existing behaviour (disaster broadcasts,
# read/unread state, etc.) changes.
#
# Written by hand, following the same manual-migration style
# already used in this project (see 0016/0017), since this
# environment has no network access to run
# `manage.py makemigrations` directly -- see the final summary
# for the exact commands to run to verify this against the real
# project database.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0017_disasterreport_reported_severity'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='report',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='notifications',
                to='reports.disasterreport',
            ),
        ),
        migrations.AddField(
            model_name='notification',
            name='notification_type',
            field=models.CharField(
                choices=[
                    ('REPORT_RECEIVED', 'Report Received'),
                    ('REPORT_UNDER_REVIEW', 'Report Under Review'),
                    ('REPORT_VERIFIED', 'Report Verified'),
                    ('REPORT_REJECTED', 'Report Rejected'),
                    ('DISASTER_ALERT', 'Disaster Alert'),
                    ('GENERAL', 'General NDMS'),
                ],
                default='GENERAL',
                max_length=30,
            ),
        ),
    ]
