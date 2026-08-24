from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0127_user_hardcover_api_key"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="homescreenrow",
            name="home_screen_row_row_type_valid",
        ),
        migrations.AlterField(
            model_name="homescreenrow",
            name="row_type",
            field=models.CharField(
                choices=[
                    ("library_query", "Library Row"),
                    ("custom_list", "List / Smart List"),
                    ("recently_unrated", "Recently Played - Not Rated"),
                    ("up_next", "Up Next"),
                ],
                default="library_query",
                max_length=32,
            ),
        ),
        migrations.AddConstraint(
            model_name="homescreenrow",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    row_type__in=[
                        "library_query",
                        "custom_list",
                        "recently_unrated",
                        "up_next",
                    ]
                ),
                name="home_screen_row_row_type_valid",
            ),
        ),
    ]
