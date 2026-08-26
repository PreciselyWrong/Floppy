from django.db import migrations


CONTENT_DEFAULTS = {
    "media": ["notes", "related", "cast", "crew", "recommendations"],
    "series": [
        "notes",
        "seasons",
        "episodes",
        "cast",
        "crew",
        "recommendations",
    ],
    "episode": ["notes", "cast", "crew"],
}


def move_review_preferences(apps, schema_editor):
    user_model = apps.get_model("users", "User")
    users = []
    for user in user_model.objects.all().iterator():
        layouts = dict(user.detail_page_layouts or {})
        for family, default_sections in CONTENT_DEFAULTS.items():
            family_layout = dict(layouts.get(family) or {})
            sections = list(family_layout.get("content", default_sections))
            sections = [section for section in sections if section != "reviews"]
            if user.show_public_reviews:
                if user.public_reviews_position == "top":
                    sections.insert(0, "reviews")
                else:
                    sections.append("reviews")
            family_layout["content"] = sections
            layouts[family] = family_layout
        user.detail_page_layouts = layouts
        users.append(user)
    user_model.objects.bulk_update(users, ["detail_page_layouts"], batch_size=500)


class Migration(migrations.Migration):
    dependencies = [("users", "0145_merge_public_reviews")]

    operations = [migrations.RunPython(move_review_preferences, migrations.RunPython.noop)]
