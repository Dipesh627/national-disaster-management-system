# Adds ONE additive, nullable field:
#
#   - Notification.support_request:
#       optional link back to the SupportRequest a notification
#       is about, so the admin notification dropdown / detail
#       page can route straight to the existing Admin Support
#       Request Detail page. Mirrors Notification.report (see
#       migration 0018) exactly -- same pattern, same
#       on_delete/related_name/blank/null shape.
#
# Default-safe: every existing Notification row becomes
# support_request=NULL, so no existing notification (disaster
# broadcasts, report-lifecycle notifications, general
# notifications, read/unread state, etc.) changes in any way.
#
# Written by hand, following the same manual-migration style
# already used in this project (see 0016/0017/0018), since this
# environment has no network access to run
# `manage.py makemigrations` directly -- see the final summary
# for the exact command to run to verify this against the real
# project database.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0022_usersettings_theme'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='support_request',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='notifications',
                to='reports.supportrequest',
            ),
        ),
    ]