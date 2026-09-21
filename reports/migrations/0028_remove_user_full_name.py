from django.db import migrations


# =========================================================
# SCHEMA MIGRATION
# =========================================================
#
# Removes the obsolete `full_name` column. This MUST run
# after 0027_populate_first_last_name, which already copied
# every existing full_name value into first_name/last_name.
# Nothing else touches `full_name` (models.py no longer
# declares it, and every view/form/template/admin reference
# has been switched to first_name/last_name or
# get_full_name()), so it is now safe to drop.
# =========================================================


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0027_populate_first_last_name'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='full_name',
        ),
    ]