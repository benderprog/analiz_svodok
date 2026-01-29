from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Pu",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("short_name", models.CharField(max_length=100)),
                ("full_name", models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name="SubdivisionRef",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("short_name", models.CharField(max_length=100)),
                ("full_name", models.CharField(max_length=255)),
                ("pu", models.ForeignKey(on_delete=models.deletion.CASCADE, to="reference.pu")),
            ],
        ),
    ]
