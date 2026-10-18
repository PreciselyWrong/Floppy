from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0127_user_hardcover_api_key"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="theme",
            field=models.CharField(
                choices=[
                    ("system", "System default"),
                    ("dark", "Dark"),
                    ("light", "Light"),
                    ("projector", "Projector"),
                    ("video_store", "Video store"),
                    ("custom", "Custom palette"),
                ],
                default="system",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="custom_theme",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Validated custom application color palette",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="detail_page_layouts",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Visible and ordered sections for each detail page family",
            ),
        ),
    ]
