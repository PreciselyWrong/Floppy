import json

from django.db import migrations
from django.utils import timezone

INTERVAL_HOURS = 6
TASK_NAME = "Refresh Plex library index"


def create_index_schedules(apps, schema_editor):
    PlexAccount = apps.get_model("integrations", "PlexAccount")
    IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    interval, _ = IntervalSchedule.objects.get_or_create(
        every=INTERVAL_HOURS,
        period="hours",
    )
    for account in PlexAccount.objects.exclude(plex_token="").iterator():
        kwargs = json.dumps({"user_id": account.user_id})
        if PeriodicTask.objects.filter(task=TASK_NAME, kwargs=kwargs).exists():
            continue
        PeriodicTask.objects.create(
            name=(
                f"{TASK_NAME} for {account.plex_username or account.user_id} "
                f"(every {INTERVAL_HOURS} hours)"
            ),
            task=TASK_NAME,
            interval=interval,
            kwargs=kwargs,
            start_time=timezone.now(),
            enabled=True,
        )


def delete_index_schedules(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(task=TASK_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("integrations", "0032_plexlibrarysection_plexlibraryitem_and_more"),
    ]

    operations = [
        migrations.RunPython(create_index_schedules, delete_index_schedules),
    ]
