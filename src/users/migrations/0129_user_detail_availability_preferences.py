from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0128_user_ui_language"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="detail_availability_enabled",
            field=models.BooleanField(
                default=True,
                help_text="Show local service availability on private media details",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="detail_availability_plex_enabled",
            field=models.BooleanField(
                default=True,
                help_text="Show Plex availability on private media details",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="detail_availability_radarr_enabled",
            field=models.BooleanField(
                default=True,
                help_text="Show Radarr availability on private media details",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="detail_availability_sonarr_enabled",
            field=models.BooleanField(
                default=True,
                help_text="Show Sonarr availability on private media details",
            ),
        ),
    ]
