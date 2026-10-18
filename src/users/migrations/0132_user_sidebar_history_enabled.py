from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("users", "0131_user_home_media_type_chip_preferences")]

    operations = [
        migrations.AddField(
            model_name="user",
            name="sidebar_history_enabled",
            field=models.BooleanField(
                default=True,
                help_text="Show History in the sidebar navigation",
            ),
        ),
    ]
