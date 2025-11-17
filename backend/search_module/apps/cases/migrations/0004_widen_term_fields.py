from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0003_legal_vocabulary_models"),
    ]

    operations = [
        migrations.AlterField(
            model_name="term",
            name="canonical",
            field=models.CharField(db_index=True, max_length=1000),
        ),
        migrations.AlterField(
            model_name="termoccurrence",
            name="surface",
            field=models.CharField(max_length=1000),
        ),
    ]


