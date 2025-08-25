# Generated manually to avoid conflicts with existing models

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cases', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file_path', models.CharField(max_length=1000, unique=True)),
                ('file_name', models.CharField(max_length=255)),
                ('file_size', models.BigIntegerField()),
                ('sha256_hash', models.CharField(max_length=64, unique=True)),
                ('total_pages', models.IntegerField(blank=True, null=True)),
                ('original_url', models.URLField(max_length=1000)),
                ('download_date', models.DateTimeField(auto_now_add=True)),
                ('is_downloaded', models.BooleanField(default=False)),
                ('is_processed', models.BooleanField(default=False)),
                ('is_cleaned', models.BooleanField(default=False)),
                ('download_error', models.TextField(blank=True)),
                ('processing_error', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'documents',
            },
        ),
        migrations.CreateModel(
            name='CaseDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_table', models.CharField(max_length=50)),
                ('source_row_id', models.BigIntegerField()),
                ('source_link_index', models.IntegerField(default=0)),
                ('document_type', models.CharField(blank=True, max_length=50)),
                ('document_title', models.CharField(blank=True, max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('case', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='case_documents', to='cases.case')),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='case_documents', to='cases.document')),
            ],
            options={
                'db_table': 'case_documents',
                'unique_together': {('case', 'document', 'source_table', 'source_row_id', 'source_link_index')},
            },
        ),
        migrations.CreateModel(
            name='DocumentText',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('page_number', models.IntegerField()),
                ('raw_text', models.TextField()),
                ('clean_text', models.TextField(blank=True)),
                ('extraction_method', models.CharField(default='pymupdf', max_length=20)),
                ('confidence_score', models.FloatField(blank=True, null=True)),
                ('processing_time', models.FloatField(blank=True, null=True)),
                ('has_text', models.BooleanField(default=True)),
                ('needs_ocr', models.BooleanField(default=False)),
                ('is_cleaned', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='document_texts', to='cases.document')),
            ],
            options={
                'db_table': 'document_texts',
                'unique_together': {('document', 'page_number')},
            },
        ),
        migrations.CreateModel(
            name='UnifiedCaseView',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('case_metadata', models.JSONField(default=dict)),
                ('pdf_content_summary', models.JSONField(default=dict)),
                ('has_pdf', models.BooleanField(default=False)),
                ('text_extracted', models.BooleanField(default=False)),
                ('text_cleaned', models.BooleanField(default=False)),
                ('metadata_complete', models.BooleanField(default=False)),
                ('is_processed', models.BooleanField(default=False)),
                ('processing_error', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('case', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='unified_view', to='cases.case')),
            ],
            options={
                'db_table': 'unified_case_views',
            },
        ),
        migrations.AddIndex(
            model_name='document',
            index=models.Index(fields=['sha256_hash'], name='documents_sha256_ha_123456_idx'),
        ),
        migrations.AddIndex(
            model_name='document',
            index=models.Index(fields=['is_downloaded'], name='documents_is_downl_123456_idx'),
        ),
        migrations.AddIndex(
            model_name='document',
            index=models.Index(fields=['is_processed'], name='documents_is_proce_123456_idx'),
        ),
        migrations.AddIndex(
            model_name='document',
            index=models.Index(fields=['is_cleaned'], name='documents_is_clean_123456_idx'),
        ),
        migrations.AddIndex(
            model_name='casedocument',
            index=models.Index(fields=['source_table'], name='case_docume_source__123456_idx'),
        ),
        migrations.AddIndex(
            model_name='casedocument',
            index=models.Index(fields=['document_type'], name='case_docume_documen_123456_idx'),
        ),
        migrations.AddIndex(
            model_name='documenttext',
            index=models.Index(fields=['page_number'], name='document_t_page_nu_123456_idx'),
        ),
        migrations.AddIndex(
            model_name='documenttext',
            index=models.Index(fields=['extraction_method'], name='document_t_extract_123456_idx'),
        ),
        migrations.AddIndex(
            model_name='documenttext',
            index=models.Index(fields=['has_text'], name='document_t_has_tex_123456_idx'),
        ),
        migrations.AddIndex(
            model_name='documenttext',
            index=models.Index(fields=['needs_ocr'], name='document_t_needs_o_123456_idx'),
        ),
        migrations.AddIndex(
            model_name='unifiedcaseview',
            index=models.Index(fields=['has_pdf'], name='unified_cas_has_pdf_123456_idx'),
        ),
        migrations.AddIndex(
            model_name='unifiedcaseview',
            index=models.Index(fields=['text_extracted'], name='unified_cas_text_ex_123456_idx'),
        ),
        migrations.AddIndex(
            model_name='unifiedcaseview',
            index=models.Index(fields=['text_cleaned'], name='unified_cas_text_cl_123456_idx'),
        ),
        migrations.AddIndex(
            model_name='unifiedcaseview',
            index=models.Index(fields=['metadata_complete'], name='unified_cas_metadat_123456_idx'),
        ),
        migrations.AddIndex(
            model_name='unifiedcaseview',
            index=models.Index(fields=['is_processed'], name='unified_cas_is_proc_123456_idx'),
        ),
    ]
