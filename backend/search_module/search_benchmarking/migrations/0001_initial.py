# Generated manually for search_benchmarking

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BenchmarkQuerySet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('description', models.TextField(blank=True)),
                ('category', models.CharField(max_length=100)),
                ('expected_results_count', models.IntegerField(default=10)),
                ('timeout_seconds', models.IntegerField(default=30)),
                ('version', models.CharField(default='1.0', max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'benchmark_query_sets',
                'verbose_name_plural': 'Benchmark Query Sets',
            },
        ),
        migrations.CreateModel(
            name='BenchmarkConfiguration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('description', models.TextField(blank=True)),
                ('search_mode', models.CharField(choices=[('lexical', 'Lexical'), ('semantic', 'Semantic'), ('hybrid', 'Hybrid')], max_length=20)),
                ('ranking_algorithm', models.CharField(choices=[('fast_ranking', 'Fast Ranking'), ('advanced_ranking', 'Advanced Ranking')], max_length=30)),
                ('ranking_config', models.JSONField(default=dict)),
                ('timeout_seconds', models.IntegerField(default=30)),
                ('max_results_per_query', models.IntegerField(default=100)),
                ('enable_performance_monitoring', models.BooleanField(default=True)),
                ('enable_quality_metrics', models.BooleanField(default=True)),
                ('enable_system_metrics', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('is_default', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('query_sets', models.ManyToManyField(blank=True, to='search_benchmarking.benchmarkqueryset')),
            ],
            options={
                'db_table': 'benchmark_configurations',
                'verbose_name_plural': 'Benchmark Configurations',
            },
        ),
        migrations.CreateModel(
            name='BenchmarkQuery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('query_text', models.TextField()),
                ('query_type', models.CharField(choices=[('exact_match', 'Exact Match'), ('semantic', 'Semantic'), ('hybrid', 'Hybrid'), ('complex', 'Complex')], default='hybrid', max_length=20)),
                ('expected_results', models.JSONField(default=list)),
                ('difficulty_level', models.IntegerField(choices=[(1, 'Very Easy'), (2, 'Easy'), (3, 'Medium'), (4, 'Hard'), (5, 'Very Hard')], default=3)),
                ('legal_domain', models.CharField(blank=True, max_length=100)),
                ('expected_latency_ms', models.IntegerField(default=1000)),
                ('min_relevance_score', models.FloatField(default=0.7)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('last_used', models.DateTimeField(blank=True, null=True)),
                ('query_set', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='queries', to='search_benchmarking.benchmarkqueryset')),
            ],
            options={
                'db_table': 'benchmark_queries',
                'verbose_name_plural': 'Benchmark Queries',
            },
        ),
        migrations.CreateModel(
            name='BenchmarkExecution',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('execution_name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('search_mode', models.CharField(choices=[('lexical', 'Lexical'), ('semantic', 'Semantic'), ('hybrid', 'Hybrid')], max_length=20)),
                ('ranking_algorithm', models.CharField(choices=[('fast_ranking', 'Fast Ranking'), ('advanced_ranking', 'Advanced Ranking')], max_length=30)),
                ('ranking_config', models.JSONField(default=dict)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('running', 'Running'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('total_queries', models.IntegerField(default=0)),
                ('successful_queries', models.IntegerField(default=0)),
                ('failed_queries', models.IntegerField(default=0)),
                ('average_latency_ms', models.FloatField(blank=True, null=True)),
                ('min_latency_ms', models.FloatField(blank=True, null=True)),
                ('max_latency_ms', models.FloatField(blank=True, null=True)),
                ('total_execution_time', models.FloatField(blank=True, null=True)),
                ('average_precision_at_10', models.FloatField(blank=True, null=True)),
                ('average_recall_at_10', models.FloatField(blank=True, null=True)),
                ('average_mrr', models.FloatField(blank=True, null=True)),
                ('average_ndcg_at_10', models.FloatField(blank=True, null=True)),
                ('memory_usage_mb', models.FloatField(blank=True, null=True)),
                ('cpu_usage_percent', models.FloatField(blank=True, null=True)),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('configuration', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='search_benchmarking.benchmarkconfiguration')),
                ('query_set', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='executions', to='search_benchmarking.benchmarkqueryset')),
            ],
            options={
                'db_table': 'benchmark_executions',
                'verbose_name_plural': 'Benchmark Executions',
            },
        ),
        migrations.CreateModel(
            name='BenchmarkResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('query_text', models.TextField()),
                ('search_mode', models.CharField(max_length=20)),
                ('ranking_algorithm', models.CharField(max_length=30)),
                ('returned_results', models.JSONField(default=list)),
                ('total_results_found', models.IntegerField(default=0)),
                ('execution_time_ms', models.FloatField(blank=True, null=True)),
                ('memory_usage_mb', models.FloatField(blank=True, null=True)),
                ('cpu_usage_percent', models.FloatField(blank=True, null=True)),
                ('precision_at_10', models.FloatField(blank=True, null=True)),
                ('recall_at_10', models.FloatField(blank=True, null=True)),
                ('mrr', models.FloatField(blank=True, null=True)),
                ('ndcg_at_10', models.FloatField(blank=True, null=True)),
                ('ranking_quality_score', models.FloatField(blank=True, null=True)),
                ('relevance_scores', models.JSONField(default=dict)),
                ('status', models.CharField(choices=[('success', 'Success'), ('error', 'Error'), ('timeout', 'Timeout')], default='success', max_length=20)),
                ('error_message', models.TextField(blank=True, null=True)),
                ('executed_at', models.DateTimeField(auto_now_add=True)),
                ('execution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='results', to='search_benchmarking.benchmarkexecution')),
                ('query', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='results', to='search_benchmarking.benchmarkquery')),
            ],
            options={
                'db_table': 'benchmark_results',
                'verbose_name_plural': 'Benchmark Results',
            },
        ),
        migrations.CreateModel(
            name='BenchmarkComparison',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('performance_improvement', models.FloatField(blank=True, null=True)),
                ('quality_improvement', models.FloatField(blank=True, null=True)),
                ('comparison_results', models.JSONField(default=dict)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('baseline_execution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='baseline_comparisons', to='search_benchmarking.benchmarkexecution')),
                ('comparison_executions', models.ManyToManyField(related_name='comparison_participants', to='search_benchmarking.benchmarkexecution')),
            ],
            options={
                'db_table': 'benchmark_comparisons',
                'verbose_name_plural': 'Benchmark Comparisons',
            },
        ),
        migrations.CreateModel(
            name='BenchmarkReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('report_name', models.CharField(max_length=255)),
                ('report_type', models.CharField(choices=[('summary', 'Summary'), ('detailed', 'Detailed'), ('performance', 'Performance'), ('quality', 'Quality'), ('comparison', 'Comparison')], max_length=20)),
                ('report_data', models.JSONField(default=dict)),
                ('report_html', models.TextField(blank=True)),
                ('report_pdf_path', models.CharField(blank=True, max_length=500)),
                ('is_generated', models.BooleanField(default=False)),
                ('generation_time', models.FloatField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('generated_at', models.DateTimeField(blank=True, null=True)),
                ('execution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reports', to='search_benchmarking.benchmarkexecution')),
            ],
            options={
                'db_table': 'benchmark_reports',
                'verbose_name_plural': 'Benchmark Reports',
            },
        ),
    ]
