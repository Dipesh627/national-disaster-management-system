from django.db import migrations, models


# =========================================================
# TERMS & PRIVACY ACCEPTANCE RECORD
# =========================================================
#
# Purely additive: two new columns on the user table. Both are
# nullable/blank-safe, so every existing account keeps working
# untouched. Existing users simply have terms_accepted_at = NULL
# and terms_version = '' (meaning: registered before the Terms
# were introduced -- no acceptance is recorded or pretended).
# =========================================================


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0028_remove_user_full_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='terms_accepted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='terms_version',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
    ]