# Generated manually for normalized facet tables
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('search_indexing', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='FacetTerm',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('facet_type', models.CharField(db_index=True, max_length=50)),
                ('canonical_term', models.CharField(db_index=True, max_length=200)),
                ('occurrence_count', models.IntegerField(default=0)),
                ('case_count', models.IntegerField(default=0)),
                ('boost_factor', models.FloatField(default=1.0)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'facet_terms',
            },
        ),
        migrations.CreateModel(
            name='FacetMapping',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('case_id', models.IntegerField(db_index=True)),
                ('occurrence_count', models.IntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('facet_term', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mappings', to='search_indexing.facetterm')),
            ],
            options={
                'db_table': 'facet_mappings',
            },
        ),
        migrations.AlterUniqueTogether(
            name='facetterm',
            unique_together={('facet_type', 'canonical_term')},
        ),
        migrations.AlterUniqueTogether(
            name='facetmapping',
            unique_together={('facet_term', 'case_id')},
        ),
        migrations.AddIndex(
            model_name='facetterm',
            index=models.Index(fields=['facet_type', 'occurrence_count'], name='facet_terms_facet_t_occurre_7b8c8c_idx'),
        ),
        migrations.AddIndex(
            model_name='facetterm',
            index=models.Index(fields=['facet_type', 'case_count'], name='facet_terms_facet_t_case_c_8c9c9c_idx'),
        ),
        migrations.AddIndex(
            model_name='facetterm',
            index=models.Index(fields=['canonical_term'], name='facet_terms_canonic_9d0d0d_idx'),
        ),
        migrations.AddIndex(
            model_name='facetmapping',
            index=models.Index(fields=['case_id'], name='facet_mappin_case_i_0e1e1e_idx'),
        ),
        migrations.AddIndex(
            model_name='facetmapping',
            index=models.Index(fields=['facet_term', 'case_id'], name='facet_mappin_facet__1f2f2f_idx'),
        ),
    ]
