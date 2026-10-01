from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0025_disaster_resolved_date_supportrequest_response'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='usersettings',
            name='theme',
        ),
        migrations.RemoveField(
            model_name='usersettings',
            name='font_size',
        ),
        migrations.RemoveField(
            model_name='usersettings',
            name='reduce_motion',
        ),
        migrations.RemoveField(
            model_name='usersettings',
            name='high_contrast',
        ),
        migrations.RemoveField(
            model_name='usersettings',
            name='dashboard_view',
        ),
    ]