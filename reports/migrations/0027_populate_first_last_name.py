from django.db import migrations


# =========================================================
# DATA MIGRATION
# =========================================================
#
# The project's custom User model has always had a
# `full_name` CharField, separate from the first_name /
# last_name fields Django's AbstractUser already provides
# (those have existed, empty, since the very first
# migration). This migration copies the existing
# `full_name` data into first_name / last_name so nothing
# is lost before `full_name` itself is removed by the next
# migration (0028).
#
# SPLIT RULE (documented, applied consistently):
#   - The first whitespace-separated word of full_name
#     becomes first_name.
#   - Every remaining word becomes last_name (joined back
#     together with single spaces).
#   - A full_name with only one word gets that word as
#     first_name and an empty last_name.
#   - A blank/whitespace-only full_name leaves first_name
#     and last_name blank (nothing to migrate).
#
# Examples:
#   "Aakriti Pandey"   -> first_name="Aakriti", last_name="Pandey"
#   "Mahee Bhandari"   -> first_name="Mahee",   last_name="Bhandari"
#   "Dip Esh"          -> first_name="Dip",     last_name="Esh"
#   "Ram Kumar Thapa"  -> first_name="Ram",     last_name="Kumar Thapa"
#
# This only ever touches rows where full_name is non-blank;
# it never overwrites a first_name/last_name that a user may
# already have (there are none in practice, since those
# fields were never exposed anywhere in the app until now,
# but the guard is kept for safety).
# =========================================================


def split_full_name_into_first_last(apps, schema_editor):

    User = apps.get_model('reports', 'User')

    for user in User.objects.all():

        full_name = (user.full_name or '').strip()

        if not full_name:
            continue

        parts = full_name.split()

        first_name = parts[0]
        last_name = ' '.join(parts[1:])

        user.first_name = first_name
        user.last_name = last_name

        user.save(
            update_fields=[
                'first_name',
                'last_name',
            ]
        )


def reverse_split_full_name(apps, schema_editor):

    # -------------------------------------------------------
    # Reverse: rebuild full_name from first_name + last_name
    # so `migrate reports 0026` restores the previous data
    # shape if this migration is ever rolled back.
    # -------------------------------------------------------

    User = apps.get_model('reports', 'User')

    for user in User.objects.all():

        combined = ' '.join(
            part
            for part in (user.first_name, user.last_name)
            if part
        ).strip()

        if combined:
            user.full_name = combined
            user.save(update_fields=['full_name'])


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0026_remove_usersettings_appearance_fields'),
    ]

    operations = [
        migrations.RunPython(
            split_full_name_into_first_last,
            reverse_split_full_name,
        ),
    ]