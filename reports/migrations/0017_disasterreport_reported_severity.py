# Generated manually to add the citizen-reported severity field
# to DisasterReport (Citizen "Report Incident" redesign).
#
# Uses a fixed, sensible default ('MEDIUM') purely so existing
# DisasterReport rows created before this field existed remain
# valid after this migration runs. It does NOT change how new
# reports are created: the citizen-facing form always requires
# an explicit severity selection (see DisasterReportForm), the
# model default only exists to satisfy the migration itself.
#
# This field is intentionally separate from Disaster.severity
# (added in an earlier migration) -- see the comments on
# DisasterReport.SEVERITY_CHOICES in reports/models.py.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0016_disaster_location_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='disasterreport',
            name='reported_severity',
            field=models.CharField(
                choices=[
                    ('LOW', 'Low'),
                    ('MEDIUM', 'Medium'),
                    ('HIGH', 'High'),
                    ('CRITICAL', 'Critical'),
                ],
                default='MEDIUM',
                help_text='Severity level as reported by the citizen.',
                max_length=20,
            ),
        ),
    ]