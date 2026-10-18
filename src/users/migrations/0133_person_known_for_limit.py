from django.db import migrations, models
from django.core.validators import MaxValueValidator, MinValueValidator


class Migration(migrations.Migration):
    dependencies = [("users", "0132_user_sidebar_history_enabled")]

    operations = [
        migrations.AddField(
            model_name="user",
            name="person_known_for_limit",
            field=models.PositiveSmallIntegerField(
                default=3,
                help_text="Number of watched titles shown under each detail credit card",
                validators=[MinValueValidator(0), MaxValueValidator(10)],
            ),
        ),
    ]
