# Generated manually to add Disaster location fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0015_alter_user_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='disaster',
            name='latitude',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AddField(
            model_name='disaster',
            name='longitude',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AddField(
            model_name='disaster',
            name='address',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]