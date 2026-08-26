from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("users", "0128_user_ui_language")]

    operations = [
        migrations.AddField(
            model_name="user",
            name="public_reviews_position",
            field=models.CharField(
                choices=[("top", "Top"), ("bottom", "Bottom")],
                default="bottom",
                help_text="Place public reviews before or after other detail sections",
                max_length=6,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="show_public_reviews",
            field=models.BooleanField(
                default=True,
                help_text="Show public reviews on supported detail pages",
            ),
        ),
    ]
