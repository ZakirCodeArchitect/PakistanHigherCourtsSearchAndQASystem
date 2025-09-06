"""
Search Benchmarking Admin Configuration
Django admin interface for benchmark management.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import (
    BenchmarkQuerySet, BenchmarkQuery, BenchmarkExecution,
    BenchmarkResult, BenchmarkComparison, BenchmarkConfiguration, BenchmarkReport
)


@admin.register(BenchmarkQuerySet)
class BenchmarkQuerySetAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'version', 'query_count', 'execution_count', 'is_active', 'created_at']
    list_filter = ['category', 'is_active', 'version', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'category', 'version')
        }),
        ('Configuration', {
            'fields': ('expected_results_count', 'timeout_seconds')
        }),
        ('Status', {
            'fields': ('is_active', 'created_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def query_count(self, obj):
        return obj.queries.filter(is_active=True).count()
    query_count.short_description = 'Active Queries'
    
    def execution_count(self, obj):
        return obj.executions.count()
    execution_count.short_description = 'Executions'


@admin.register(BenchmarkQuery)
class BenchmarkQueryAdmin(admin.ModelAdmin):
    list_display = ['query_text_preview', 'query_set', 'query_type', 'difficulty_level', 'legal_domain', 'expected_count', 'is_active']
    list_filter = ['query_set', 'query_type', 'difficulty_level', 'legal_domain', 'is_active', 'created_at']
    search_fields = ['query_text', 'legal_domain']
    readonly_fields = ['created_at', 'updated_at', 'last_used']
    
    fieldsets = (
        ('Query Information', {
            'fields': ('query_set', 'query_text', 'query_type', 'legal_domain')
        }),
        ('Expected Results', {
            'fields': ('expected_results', 'expected_latency_ms', 'min_relevance_score')
        }),
        ('Difficulty', {
            'fields': ('difficulty_level',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_used'),
            'classes': ('collapse',)
        })
    )
    
    def query_text_preview(self, obj):
        return obj.query_text[:50] + '...' if len(obj.query_text) > 50 else obj.query_text
    query_text_preview.short_description = 'Query Text'
    
    def expected_count(self, obj):
        return len(obj.expected_results)
    expected_count.short_description = 'Expected Results'


@admin.register(BenchmarkExecution)
class BenchmarkExecutionAdmin(admin.ModelAdmin):
    list_display = ['execution_name', 'query_set', 'search_mode', 'ranking_algorithm', 'status', 'success_rate', 'avg_latency', 'started_at']
    list_filter = ['status', 'search_mode', 'ranking_algorithm', 'started_at', 'query_set']
    search_fields = ['execution_name', 'description']
    readonly_fields = ['started_at', 'completed_at', 'duration', 'success_rate']
    
    fieldsets = (
        ('Execution Information', {
            'fields': ('execution_name', 'description', 'query_set', 'status')
        }),
        ('Configuration', {
            'fields': ('search_mode', 'ranking_algorithm', 'ranking_config')
        }),
        ('Results Summary', {
            'fields': ('total_queries', 'successful_queries', 'failed_queries', 'success_rate')
        }),
        ('Performance Metrics', {
            'fields': ('average_latency_ms', 'min_latency_ms', 'max_latency_ms', 'total_execution_time')
        }),
        ('Quality Metrics', {
            'fields': ('average_precision_at_10', 'average_recall_at_10', 'average_mrr', 'average_ndcg_at_10')
        }),
        ('System Metrics', {
            'fields': ('memory_usage_mb', 'cpu_usage_percent'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('started_at', 'completed_at', 'duration'),
            'classes': ('collapse',)
        })
    )
    
    def avg_latency(self, obj):
        return f"{obj.average_latency_ms:.1f}ms" if obj.average_latency_ms else "N/A"
    avg_latency.short_description = 'Avg Latency'
    
    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status == 'completed':
            return self.readonly_fields + ['total_queries', 'successful_queries', 'failed_queries']
        return self.readonly_fields


@admin.register(BenchmarkResult)
class BenchmarkResultAdmin(admin.ModelAdmin):
    list_display = ['query_preview', 'execution', 'status', 'execution_time', 'precision_at_10', 'ranking_quality']
    list_filter = ['status', 'search_mode', 'ranking_algorithm', 'executed_at', 'execution']
    search_fields = ['query_text', 'execution__execution_name']
    readonly_fields = ['executed_at']
    
    fieldsets = (
        ('Result Information', {
            'fields': ('execution', 'query', 'query_text', 'status', 'error_message')
        }),
        ('Configuration', {
            'fields': ('search_mode', 'ranking_algorithm')
        }),
        ('Results', {
            'fields': ('returned_results', 'total_results_found')
        }),
        ('Performance', {
            'fields': ('execution_time_ms', 'memory_usage_mb', 'cpu_usage_percent')
        }),
        ('Quality Metrics', {
            'fields': ('precision_at_10', 'recall_at_10', 'mrr', 'ndcg_at_10', 'ranking_quality_score')
        }),
        ('Detailed Analysis', {
            'fields': ('relevance_scores',),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('executed_at',)
        })
    )
    
    def query_preview(self, obj):
        return obj.query_text[:30] + '...' if len(obj.query_text) > 30 else obj.query_text
    query_preview.short_description = 'Query'
    
    def execution_time(self, obj):
        return f"{obj.execution_time_ms:.1f}ms" if obj.execution_time_ms else "N/A"
    execution_time.short_description = 'Time'
    
    def ranking_quality(self, obj):
        if obj.ranking_quality_score is not None:
            color = 'green' if obj.ranking_quality_score >= 0.7 else 'orange' if obj.ranking_quality_score >= 0.5 else 'red'
            return format_html('<span style="color: {};">{:.3f}</span>', color, obj.ranking_quality_score)
        return "N/A"
    ranking_quality.short_description = 'Quality'


@admin.register(BenchmarkComparison)
class BenchmarkComparisonAdmin(admin.ModelAdmin):
    list_display = ['name', 'baseline_execution', 'comparison_count', 'performance_improvement', 'quality_improvement', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Comparison Information', {
            'fields': ('name', 'description', 'baseline_execution', 'comparison_executions')
        }),
        ('Results', {
            'fields': ('performance_improvement', 'quality_improvement', 'comparison_results')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def comparison_count(self, obj):
        return obj.comparison_executions.count()
    comparison_count.short_description = 'Comparisons'


@admin.register(BenchmarkConfiguration)
class BenchmarkConfigurationAdmin(admin.ModelAdmin):
    list_display = ['name', 'search_mode', 'ranking_algorithm', 'query_sets_count', 'is_default', 'is_active']
    list_filter = ['search_mode', 'ranking_algorithm', 'is_default', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['query_sets']
    
    fieldsets = (
        ('Configuration Information', {
            'fields': ('name', 'description')
        }),
        ('Search Configuration', {
            'fields': ('search_mode', 'ranking_algorithm', 'ranking_config')
        }),
        ('Benchmark Settings', {
            'fields': ('query_sets', 'timeout_seconds', 'max_results_per_query')
        }),
        ('Monitoring Settings', {
            'fields': ('enable_performance_monitoring', 'enable_quality_metrics', 'enable_system_metrics')
        }),
        ('Status', {
            'fields': ('is_active', 'is_default')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def query_sets_count(self, obj):
        return obj.query_sets.count()
    query_sets_count.short_description = 'Query Sets'


@admin.register(BenchmarkReport)
class BenchmarkReportAdmin(admin.ModelAdmin):
    list_display = ['report_name', 'execution', 'report_type', 'is_generated', 'generated_at']
    list_filter = ['report_type', 'is_generated', 'generated_at', 'created_at']
    search_fields = ['report_name', 'execution__execution_name']
    readonly_fields = ['created_at', 'generated_at', 'generation_time']
    
    fieldsets = (
        ('Report Information', {
            'fields': ('execution', 'report_name', 'report_type')
        }),
        ('Content', {
            'fields': ('report_data', 'report_html', 'report_pdf_path')
        }),
        ('Status', {
            'fields': ('is_generated', 'generation_time')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'generated_at'),
            'classes': ('collapse',)
        })
    )
    
    def has_add_permission(self, request):
        # Reports should be generated through the API, not created manually
        return False

