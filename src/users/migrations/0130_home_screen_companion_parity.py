from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("users", "0129_series_person_display_preferences")]

    operations = [
        migrations.AddField(
            model_name="user",
            name="home_binge_grouping_enabled",
            field=models.BooleanField(
                default=True,
                help_text="Group consecutive episodes of the same series into a single expandable card in the home activity journal",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="home_stale_days_threshold",
            field=models.PositiveIntegerField(
                default=21,
                help_text="Number of inactive days before an in-progress title is considered stale",
            ),
        ),
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
                    ("watch_history", "Activity Journal"),
                    ("shelf_resume", "Resume"),
                    ("shelf_stale", "Stale"),
                    ("shelf_unstarted", "Unstarted"),
                    ("shelf_finished", "Finished"),
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
                        "watch_history",
                        "shelf_resume",
                        "shelf_stale",
                        "shelf_unstarted",
                        "shelf_finished",
                    ]
                ),
                name="home_screen_row_row_type_valid",
            ),
        ),
    ]
