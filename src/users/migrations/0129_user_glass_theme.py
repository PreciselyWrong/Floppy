from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0128_user_appearance"),
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
                    ("glass", "Glass cinema"),
                    ("projector", "Projector"),
                    ("video_store", "Video store"),
                    ("custom", "Custom palette"),
                ],
                default="system",
                max_length=20,
            ),
        ),
    ]
