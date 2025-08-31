# Generated manually to increase canonical_term field length
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('search_indexing', '0002_add_normalized_facet_tables'),
    ]

    operations = [
        migrations.AlterField(
            model_name='facetterm',
            name='canonical_term',
            field=models.CharField(db_index=True, max_length=500),
        ),
    ]
