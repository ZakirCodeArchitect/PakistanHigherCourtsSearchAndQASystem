from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("search_indexing", "0007_documentchunk_searchmetadata_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="searchmetadata",
            name="court_normalized",
            field=models.CharField(db_index=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="searchmetadata",
            name="procedural_stage",
            field=models.CharField(blank=True, db_index=True, max_length=100),
        ),
    ]

