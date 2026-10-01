from django.db import migrations, models


# =========================================================
# FACEBOOK SIGN-IN -- STABLE IDENTITY (facebook_id)
# =========================================================
#
# Purely additive, exactly like 0030_user_google_sub: one new,
# nullable, unique column on the user table. Every existing account
# gets facebook_id = NULL, which is NOT treated as a duplicate by
# unique=True (NULL != NULL at the database level), so this cannot
# collide with -- or affect -- any existing row. No existing field
# (including google_sub) is touched, renamed or backfilled.
# =========================================================


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0030_user_google_sub'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='facebook_id',
            field=models.CharField(
                blank=True, max_length=255, null=True, unique=True,
            ),
        ),
    ]