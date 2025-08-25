# Generated manually to avoid interactive prompts

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cases', '0002_pdf_models'),
    ]

    operations = [
        # Add new vocabulary models only
        migrations.CreateModel(
            name='Term',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(db_index=True, max_length=50)),
                ('canonical', models.CharField(db_index=True, max_length=500)),
                ('statute_code', models.CharField(blank=True, max_length=50, null=True)),
                ('section_num', models.CharField(blank=True, max_length=50, null=True)),
                ('first_seen', models.DateTimeField(auto_now_add=True)),
                ('last_seen', models.DateTimeField(auto_now=True)),
                ('occurrence_count', models.IntegerField(default=0)),
            ],
            options={
                'db_table': 'terms',
                'unique_together': {('type', 'canonical')},
            },
        ),
        migrations.CreateModel(
            name='TermOccurrence',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_char', models.IntegerField()),
                ('end_char', models.IntegerField()),
                ('page_no', models.IntegerField(blank=True, null=True)),
                ('surface', models.CharField(max_length=500)),
                ('confidence', models.FloatField(default=0.0)),
                ('source_rule', models.CharField(max_length=100)),
                ('rules_version', models.CharField(max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('case', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='term_occurrences', to='cases.case')),
                ('document', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='term_occurrences', to='cases.document')),
                ('term', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='occurrences', to='cases.term')),
            ],
            options={
                'db_table': 'term_occurrences',
                'unique_together': {('term', 'case', 'start_char', 'end_char')},
            },
        ),
        migrations.CreateModel(
            name='VocabularyProcessingLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rules_version', models.CharField(db_index=True, max_length=20)),
                ('text_hash', models.CharField(db_index=True, max_length=64)),
                ('terms_extracted', models.IntegerField(default=0)),
                ('processing_time', models.FloatField(default=0.0)),
                ('is_successful', models.BooleanField(default=True)),
                ('error_message', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('case', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='vocab_processing_logs', to='cases.case')),
                ('document', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='vocab_processing_logs', to='cases.document')),
            ],
            options={
                'db_table': 'vocabulary_processing_logs',
                'unique_together': {('rules_version', 'text_hash', 'case', 'document')},
            },
        ),
        migrations.AddIndex(
            model_name='term',
            index=models.Index(fields=['type'], name='terms_type_idx'),
        ),
        migrations.AddIndex(
            model_name='term',
            index=models.Index(fields=['canonical'], name='terms_canonical_idx'),
        ),
        migrations.AddIndex(
            model_name='term',
            index=models.Index(fields=['statute_code', 'section_num'], name='terms_statute_section_idx'),
        ),
        migrations.AddIndex(
            model_name='termoccurrence',
            index=models.Index(fields=['term_id'], name='term_occurrences_term_id_idx'),
        ),
        migrations.AddIndex(
            model_name='termoccurrence',
            index=models.Index(fields=['case_id'], name='term_occurrences_case_id_idx'),
        ),
        migrations.AddIndex(
            model_name='termoccurrence',
            index=models.Index(fields=['document_id'], name='term_occurrences_document_id_idx'),
        ),
        migrations.AddIndex(
            model_name='termoccurrence',
            index=models.Index(fields=['page_no'], name='term_occurrences_page_no_idx'),
        ),
        migrations.AddIndex(
            model_name='termoccurrence',
            index=models.Index(fields=['confidence'], name='term_occurrences_confidence_idx'),
        ),
        migrations.AddIndex(
            model_name='termoccurrence',
            index=models.Index(fields=['rules_version'], name='term_occurrences_rules_version_idx'),
        ),
        migrations.AddIndex(
            model_name='vocabularyprocessinglog',
            index=models.Index(fields=['rules_version'], name='vocab_processing_logs_rules_version_idx'),
        ),
        migrations.AddIndex(
            model_name='vocabularyprocessinglog',
            index=models.Index(fields=['text_hash'], name='vocab_processing_logs_text_hash_idx'),
        ),
        migrations.AddIndex(
            model_name='vocabularyprocessinglog',
            index=models.Index(fields=['is_successful'], name='vocab_processing_logs_is_successful_idx'),
        ),
    ]
