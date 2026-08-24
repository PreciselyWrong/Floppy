import users.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("users", "0128_home_screen_all_media")]

    operations = [
        migrations.AddField(
            model_name="user",
            name="show_season_enrichment",
            field=models.BooleanField(default=True, help_text="Show season progress, resume and upcoming indicators"),
        ),
        migrations.AddField(
            model_name="user",
            name="show_episode_public_ratings",
            field=models.BooleanField(default=True, help_text="Show public episode ratings"),
        ),
        migrations.AddField(
            model_name="user",
            name="show_personal_rating_trend",
            field=models.BooleanField(default=True, help_text="Show the personal episode rating trend"),
        ),
        migrations.AddField(
            model_name="user",
            name="obfuscate_episode_titles",
            field=models.BooleanField(default=False, help_text="Hide unseen episode titles to avoid spoilers"),
        ),
        migrations.AddField(
            model_name="user",
            name="show_skipped_episodes",
            field=models.BooleanField(default=True, help_text="Show detected skipped episodes"),
        ),
        migrations.AddField(
            model_name="user",
            name="show_remaining_time",
            field=models.BooleanField(default=True, help_text="Show remaining time and estimated finish"),
        ),
        migrations.AddField(
            model_name="user",
            name="person_sections_order",
            field=models.JSONField(default=users.models.default_person_sections_order, blank=True),
        ),
        migrations.AddField(
            model_name="user",
            name="person_hidden_sections",
            field=models.JSONField(default=list, blank=True),
        ),
    ]
