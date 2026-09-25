from django.db import migrations


# =========================================================
# FACEBOOK SIGN-IN REMOVED -- DROP facebook_id
# =========================================================
#
# "Continue with Facebook" has been removed from NDMS (see
# reports/models.py, reports/urls.py, ndms/settings.py). This
# migration drops the facebook_id column added in
# 0031_user_facebook_id. It does not touch google_sub or any
# other field; that migration itself is left in place as history.
# At the time this was written, facebook_id had 0 non-null rows,
# so nothing is lost.
# =========================================================


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0031_user_facebook_id'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='facebook_id',
        ),
    ]