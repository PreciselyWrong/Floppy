from django.db import migrations, models


def _column_exists(schema_editor, table_name, column_name):
    connection = schema_editor.connection
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = current_schema() "
                "AND table_name = %s AND column_name = %s",
                [table_name, column_name],
            )
            return cursor.fetchone() is not None
    with connection.cursor() as cursor:
        description = connection.introspection.get_table_description(cursor, table_name)
        columns = {getattr(column, "name", column[0]) for column in description}
        return column_name in columns


class AddFieldIfNotExists(migrations.AddField):
    """Preserve an existing column while updating Django migration state."""

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        field = model._meta.get_field(self.name)
        if _column_exists(schema_editor, model._meta.db_table, field.column):
            return
        super().database_forwards(app_label, schema_editor, from_state, to_state)


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0150_alter_user_logo_style"),
    ]

    operations = [
        AddFieldIfNotExists(
            model_name="user",
            name="logo_text_color_end",
            field=models.CharField(
                default="#2563eb",
                help_text="Custom wordmark gradient end",
                max_length=7,
            ),
        ),
        AddFieldIfNotExists(
            model_name="user",
            name="logo_text_color_start",
            field=models.CharField(
                default="#1f2937",
                help_text="Custom wordmark color or gradient start",
                max_length=7,
            ),
        ),
        AddFieldIfNotExists(
            model_name="user",
            name="logo_text_fill",
            field=models.CharField(
                choices=[
                    ("theme_solid", "Theme color"),
                    ("custom_solid", "Custom color"),
                    ("theme_gradient", "Theme gradient"),
                    ("custom_gradient", "Custom gradient"),
                ],
                default="theme_gradient",
                help_text="Color treatment used by the navigation wordmark",
                max_length=16,
            ),
        ),
    ]
