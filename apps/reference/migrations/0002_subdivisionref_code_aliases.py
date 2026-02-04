from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("reference", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="subdivisionref",
            name="code",
            field=models.CharField(blank=True, max_length=100, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="subdivisionref",
            name="aliases",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
