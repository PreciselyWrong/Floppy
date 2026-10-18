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
        ("app", "0180_remove_item_app_item_source_valid_and_more"),
    ]

    operations = [
        AddFieldIfNotExists(
            model_name="applicationsettings",
            name="public_branding",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
