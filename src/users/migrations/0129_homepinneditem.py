import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0145_alter_metadatabackfillstate_field"),
        ("users", "0128_add_up_next_home_row_type"),
    ]

    operations = [
        migrations.CreateModel(
            name="HomePinnedItem",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("pinned_at", models.DateTimeField(auto_now_add=True)),
                (
                    "item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="home_pins",
                        to="app.item",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="home_pinned_items",
                        to="users.user",
                    ),
                ),
            ],
            options={
                "ordering": ["-pinned_at", "-id"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("user", "item"),
                        name="unique_home_pinned_item_per_user",
                    ),
                ],
            },
        ),
    ]
