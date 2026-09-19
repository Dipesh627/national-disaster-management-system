from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0012_usersettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='avatar',
            field=models.ImageField(blank=True, null=True, upload_to='avatars/'),
        ),
    ]