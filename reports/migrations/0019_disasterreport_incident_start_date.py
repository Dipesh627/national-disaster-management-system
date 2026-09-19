# Generated manually to add the citizen-selected "Incident Start
# Date & Time" field to DisasterReport (Report Incident form).
#
# This is intentionally separate from `report_date`
# (auto_now_add=True), which continues to record when the
# citizen submitted the report to NDMS. `incident_start_date`
# instead records when the citizen says the actual incident
# began, and is captured on the DisasterReportForm.
#
# null=True/blank=True only exists so this migration is safe
# for existing DisasterReport rows created before this field
# existed -- it is NOT a default used for new submissions. The
# citizen-facing form always requires an explicit selection and
# never auto-fills this value (see
# DisasterReportForm.clean_incident_start_date()); no
# default=timezone.now or auto_now_add is used here on purpose.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0018_notification_report_notification_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='disasterreport',
            name='incident_start_date',
            field=models.DateTimeField(
                blank=True,
                help_text=(
                    'When did the incident begin? Select the '
                    'actual or best-estimated start date and time.'
                ),
                null=True,
            ),
        ),
    ]