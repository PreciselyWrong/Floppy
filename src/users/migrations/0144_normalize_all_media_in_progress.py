from django.db import migrations


def normalize_all_media_in_progress(apps, schema_editor):
    HomeScreenRow = apps.get_model("users", "HomeScreenRow")
    rows = HomeScreenRow.objects.filter(
        media_type="all",
        row_type="library_query",
    )
    for row in rows.iterator():
        filters = row.filters if isinstance(row.filters, dict) else {}
        raw_status = filters.get("status")
        statuses = raw_status if isinstance(raw_status, list) else [raw_status]
        statuses = [str(value or "").strip() for value in statuses]
        if statuses != ["In progress"]:
            continue
        if str(filters.get("progress") or "all").strip().casefold() != "all":
            continue
        row.filters = {**filters, "progress": "not_caught_up"}
        row.save(update_fields=["filters"])


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0143_merge_home_resume_navigation"),
    ]

    operations = [
        migrations.RunPython(normalize_all_media_in_progress, migrations.RunPython.noop),
    ]
