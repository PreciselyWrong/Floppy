from django.db import migrations


def pin_existing_up_next_rows(apps, schema_editor):
    """Move rows made before the episode-feed Up Next existed to their new type."""
    HomeScreenRow = apps.get_model("users", "HomeScreenRow")
    HomeScreenRow.objects.using(schema_editor.connection.alias).filter(
        row_type="up_next",
    ).update(row_type="pinned_up_next", sort_by="recent")


def restore_up_next_rows(apps, schema_editor):
    HomeScreenRow = apps.get_model("users", "HomeScreenRow")
    HomeScreenRow.objects.using(schema_editor.connection.alias).filter(
        row_type="pinned_up_next",
    ).update(row_type="up_next")


class Migration(migrations.Migration):
    dependencies = [
        (
            "users",
            "0154_remove_homescreenrow_home_screen_row_row_type_valid_and_more",
        ),
    ]

    operations = [
        migrations.RunPython(pin_existing_up_next_rows, restore_up_next_rows),
    ]
