from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("search_indexing", "0005_update_embedding_model_to_mpnet"),
    ]

    operations = [
        migrations.AlterField(
            model_name="facetterm",
            name="canonical_term",
            field=models.CharField(db_index=True, max_length=1000),
        ),
    ]


