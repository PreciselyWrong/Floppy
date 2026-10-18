from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("users", "0130_home_screen_companion_parity")]

    operations = [
        migrations.AddField(
            model_name="user",
            name="home_media_type_chips_enabled",
            field=models.BooleanField(
                default=True,
                help_text="Show media-type labels on mixed in-progress and finished Home rows",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="home_media_type_chip_style",
            field=models.CharField(
                choices=[
                    ("solid", "Solid"),
                    ("soft", "Soft"),
                    ("outline", "Outline"),
                ],
                default="soft",
                help_text="Appearance of media-type labels on mixed Home rows",
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="home_media_type_chip_colors",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Custom hexadecimal label colors keyed by media type",
            ),
        ),
    ]
