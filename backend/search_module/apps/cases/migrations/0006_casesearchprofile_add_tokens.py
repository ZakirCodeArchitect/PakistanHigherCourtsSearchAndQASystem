from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0005_casesearchprofile"),
    ]

    operations = [
        migrations.AddField(
            model_name="casesearchprofile",
            name="case_number_tokens",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="casesearchprofile",
            name="section_tags",
            field=models.JSONField(blank=True, default=list),
        ),
    ]

