from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0023_notification_support_request'),
    ]

    operations = [
        migrations.AddField(
            model_name='emergencyagency',
            name='location',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
    ]