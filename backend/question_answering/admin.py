"""
Question-Answering System Admin Interface
Django admin configuration for QA models
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
import json

from .models import (
    QASession, QAQuery, QAResponse, QAKnowledgeBase, 
    QAFeedback, QAConfiguration, QAMetrics
)


@admin.register(QASession)
class QASessionAdmin(admin.ModelAdmin):
    list_display = [
        'session_id_short', 'user', 'title', 'total_queries', 
        'success_rate_display', 'user_satisfaction_score', 'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'is_archived', 'created_at', 'user']
    search_fields = ['session_id', 'title', 'user__username']
    readonly_fields = ['session_id', 'created_at', 'updated_at', 'last_activity']
    
    fieldsets = (
        ('Session Information', {
            'fields': ('session_id', 'user', 'title', 'description')
        }),
        ('Session Data', {
            'fields': ('context_data', 'conversation_history')
        }),
        ('Status & Metrics', {
            'fields': ('is_active', 'is_archived', 'total_queries', 'successful_queries', 'user_satisfaction_score')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_activity'),
            'classes': ('collapse',)
        }),
    )
    
    def session_id_short(self, obj):
        return obj.session_id[:12] + '...' if len(obj.session_id) > 12 else obj.session_id
    session_id_short.short_description = 'Session ID'
    
    def success_rate_display(self, obj):
        rate = obj.success_rate
        color = 'green' if rate >= 80 else 'orange' if rate >= 60 else 'red'
        return format_html('<span style="color: {};">{:.1f}%</span>', color, rate)
    success_rate_display.short_description = 'Success Rate'


@admin.register(QAQuery)
class QAQueryAdmin(admin.ModelAdmin):
    list_display = [
        'query_text_short', 'session', 'query_type', 'status', 
        'processing_time', 'created_at'
    ]
    list_filter = ['query_type', 'status', 'created_at', 'session__user']
    search_fields = ['query_text', 'session__session_id', 'session__user__username']
    readonly_fields = ['created_at', 'processed_at']
    
    fieldsets = (
        ('Query Information', {
            'fields': ('session', 'query_text', 'query_type', 'processed_query')
        }),
        ('Processing', {
            'fields': ('query_intent', 'query_confidence', 'context_window', 'user_context')
        }),
        ('Performance', {
            'fields': ('processing_time', 'retrieval_time', 'generation_time')
        }),
        ('Status', {
            'fields': ('status', 'error_message')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'processed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def query_text_short(self, obj):
        return obj.query_text[:50] + '...' if len(obj.query_text) > 50 else obj.query_text
    query_text_short.short_description = 'Query Text'


@admin.register(QAResponse)
class QAResponseAdmin(admin.ModelAdmin):
    list_display = [
        'query_short', 'answer_type', 'confidence_score', 
        'user_rating', 'created_at'
    ]
    list_filter = ['answer_type', 'user_rating', 'created_at']
    search_fields = ['answer_text', 'query__query_text', 'query__session__user__username']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Response Content', {
            'fields': ('query', 'answer_text', 'answer_type', 'reasoning_chain')
        }),
        ('Sources', {
            'fields': ('source_documents', 'source_cases', 'source_citations')
        }),
        ('Quality Metrics', {
            'fields': ('confidence_score', 'relevance_score', 'completeness_score', 'accuracy_score')
        }),
        ('User Feedback', {
            'fields': ('user_rating', 'user_feedback', 'feedback_timestamp')
        }),
        ('Metadata', {
            'fields': ('answer_metadata', 'limitations'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def query_short(self, obj):
        return obj.query.query_text[:40] + '...' if len(obj.query.query_text) > 40 else obj.query.query_text
    query_short.short_description = 'Query'


@admin.register(QAKnowledgeBase)
class QAKnowledgeBaseAdmin(admin.ModelAdmin):
    list_display = [
        'title_short', 'source_type', 'court', 'legal_domain', 
        'is_indexed', 'content_quality_score', 'created_at'
    ]
    list_filter = ['source_type', 'court', 'legal_domain', 'is_indexed', 'created_at']
    search_fields = ['title', 'content_text', 'case_number', 'case_title', 'judge_name']
    readonly_fields = ['content_hash', 'created_at', 'updated_at', 'indexed_at']
    
    fieldsets = (
        ('Source Information', {
            'fields': ('source_type', 'source_id', 'source_case_id', 'source_document_id')
        }),
        ('Content', {
            'fields': ('title', 'content_text', 'content_summary')
        }),
        ('Legal Metadata', {
            'fields': ('court', 'case_number', 'case_title', 'judge_name', 'date_decided')
        }),
        ('Legal Classification', {
            'fields': ('legal_domain', 'legal_concepts', 'legal_entities', 'citations')
        }),
        ('Vector Information', {
            'fields': ('vector_id', 'embedding_model', 'embedding_dimension')
        }),
        ('Quality Metrics', {
            'fields': ('content_quality_score', 'legal_relevance_score', 'completeness_score')
        }),
        ('Processing Status', {
            'fields': ('is_indexed', 'is_processed', 'processing_error')
        }),
        ('System Data', {
            'fields': ('content_hash', 'created_at', 'updated_at', 'indexed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def title_short(self, obj):
        return obj.title[:40] + '...' if len(obj.title) > 40 else obj.title
    title_short.short_description = 'Title'


@admin.register(QAFeedback)
class QAFeedbackAdmin(admin.ModelAdmin):
    list_display = [
        'response_query_short', 'user', 'rating', 'feedback_type', 
        'is_helpful', 'created_at'
    ]
    list_filter = ['rating', 'feedback_type', 'is_helpful', 'created_at']
    search_fields = ['feedback_text', 'response__query__query_text', 'user__username']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Feedback Information', {
            'fields': ('response', 'user', 'feedback_type')
        }),
        ('Ratings', {
            'fields': ('rating', 'accuracy_rating', 'relevance_rating', 'completeness_rating', 'clarity_rating')
        }),
        ('Feedback Content', {
            'fields': ('feedback_text', 'is_helpful', 'would_recommend')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def response_query_short(self, obj):
        return obj.response.query.query_text[:30] + '...' if len(obj.response.query.query_text) > 30 else obj.response.query.query_text
    response_query_short.short_description = 'Response Query'


@admin.register(QAConfiguration)
class QAConfigurationAdmin(admin.ModelAdmin):
    list_display = [
        'config_name', 'config_type', 'embedding_model', 
        'generation_model', 'is_active', 'is_default'
    ]
    list_filter = ['config_type', 'is_active', 'is_default']
    search_fields = ['config_name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Configuration', {
            'fields': ('config_name', 'config_type', 'description', 'config_data')
        }),
        ('Model Settings', {
            'fields': ('embedding_model', 'generation_model', 'max_tokens', 'temperature')
        }),
        ('Retrieval Settings', {
            'fields': ('top_k_documents', 'similarity_threshold', 'max_context_length')
        }),
        ('Status', {
            'fields': ('is_active', 'is_default')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(QAMetrics)
class QAMetricsAdmin(admin.ModelAdmin):
    list_display = [
        'metric_name', 'metric_type', 'metric_value', 
        'metric_unit', 'period_start', 'recorded_at'
    ]
    list_filter = ['metric_type', 'metric_name', 'recorded_at']
    search_fields = ['metric_name', 'metric_data']
    readonly_fields = ['recorded_at']
    
    fieldsets = (
        ('Metric Information', {
            'fields': ('metric_name', 'metric_type', 'metric_value', 'metric_unit')
        }),
        ('Time Period', {
            'fields': ('period_start', 'period_end')
        }),
        ('Data & Context', {
            'fields': ('metric_data', 'context_data')
        }),
        ('Timestamp', {
            'fields': ('recorded_at',)
        }),
    )
