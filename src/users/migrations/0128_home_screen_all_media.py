from django.db import migrations, models


HOME_MEDIA_TYPES = [
    "all",
    "tv",
    "season",
    "movie",
    "anime",
    "manga",
    "game",
    "book",
    "comic",
    "comicissue",
    "boardgame",
    "music",
    "podcast",
]


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0127_user_hardcover_api_key"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="homescreenrow",
            name="home_screen_row_media_type_valid",
        ),
        migrations.AlterField(
            model_name="homescreenrow",
            name="media_type",
            field=models.CharField(
                choices=[
                    ("all", "All media"),
                    ("tv", "TV Show"),
                    ("season", "TV Season"),
                    ("episode", "Episode"),
                    ("movie", "Movie"),
                    ("anime", "Anime"),
                    ("manga", "Manga"),
                    ("game", "Game"),
                    ("book", "Book"),
                    ("comic", "Comic"),
                    ("comicissue", "Comic Issue"),
                    ("boardgame", "Board Game"),
                    ("music", "Music"),
                    ("podcast", "Podcast"),
                ],
                max_length=16,
            ),
        ),
        migrations.AddConstraint(
            model_name="homescreenrow",
            constraint=models.CheckConstraint(
                condition=models.Q(media_type__in=HOME_MEDIA_TYPES),
                name="home_screen_row_media_type_valid",
            ),
        ),
    ]

