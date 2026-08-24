from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0129_user_glass_theme"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="theme",
            field=models.CharField(
                choices=[
                    ("system", "System default"),
                    ("light", "Light"),
                    ("dark", "Dark"),
                    ("catppuccin_mocha", "Catppuccin Mocha"),
                    ("dracula", "Dracula"),
                    ("nord", "Nord"),
                    ("gruvbox", "Gruvbox"),
                    ("oled", "OLED"),
                    ("glass", "Glass cinema"),
                    ("plex", "Plex inspired"),
                    ("projector", "Projector"),
                    ("video_store", "Video store"),
                    ("custom", "Custom palette"),
                ],
                default="system",
                max_length=20,
            ),
        ),
    ]
