from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0024_emergencyagency_location'),
    ]

    operations = [
        migrations.AddField(
            model_name='disaster',
            name='resolved_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='supportrequest',
            name='status',
            field=models.CharField(
                choices=[
                    ('OPEN', 'Open'),
                    ('IN_PROGRESS', 'In Progress'),
                    ('RESOLVED', 'Resolved'),
                ],
                default='OPEN',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='supportrequest',
            name='admin_response',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='supportrequest',
            name='responded_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]