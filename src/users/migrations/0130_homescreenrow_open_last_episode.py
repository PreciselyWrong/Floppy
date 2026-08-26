from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("users", "0129_homepinneditem")]

    operations = [
        migrations.AddField(
            model_name="homescreenrow",
            name="open_last_episode",
            field=models.BooleanField(
                default=True,
                help_text="Open the episode to continue from In Progress Home rows",
            ),
        ),
    ]
