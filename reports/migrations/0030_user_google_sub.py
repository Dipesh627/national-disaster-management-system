from django.db import migrations, models


# =========================================================
# GOOGLE SIGN-IN -- STABLE IDENTITY (google_sub)
# =========================================================
#
# Purely additive: one new, nullable, unique column on the user
# table. Every existing account gets google_sub = NULL, which is
# NOT treated as a duplicate by unique=True (NULL != NULL at the
# database level), so this cannot collide with -- or affect -- any
# existing row. No existing field is touched, renamed or backfilled.
# =========================================================


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0029_user_terms_acceptance'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='google_sub',
            field=models.CharField(
                blank=True, max_length=255, null=True, unique=True,
            ),
        ),
    ]