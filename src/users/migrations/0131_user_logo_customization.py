from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0130_user_theme_collection"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="logo_style",
            field=models.CharField(
                choices=[
                    ("colorful", "Original color"),
                    ("monochrome", "Monochrome"),
                    ("text", "Text"),
                    ("custom", "Custom image"),
                    ("hidden", "Hidden"),
                ],
                default="colorful",
                help_text="Preferred Floppy logo style",
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="logo_text",
            field=models.CharField(
                default="Floppy",
                help_text="Short navigation wordmark",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="custom_logo_data",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Normalized custom navigation logo",
            ),
        ),
    ]
