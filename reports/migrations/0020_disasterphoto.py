import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0019_disasterreport_incident_start_date'),
    ]

    operations = [
        migrations.CreateModel(
            name='DisasterPhoto',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='disasters/')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('disaster', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='photos', to='reports.disaster')),
                ('source_report_photo', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='disaster_photos', to='reports.disasterreportphoto')),
            ],
        ),
    ]