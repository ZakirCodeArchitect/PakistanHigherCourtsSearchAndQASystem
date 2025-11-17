"""
Search Benchmarking Models
Database models for storing benchmark queries, results, and performance metrics.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User
import json
from datetime import datetime, timedelta


class BenchmarkQuerySet(models.Model):
    """A collection of benchmark queries for evaluation"""
    
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100, choices=[
        ('legal_citations', 'Legal Citations'),
        ('semantic_queries', 'Semantic Queries'),
        ('complex_queries', 'Complex Queries'),
        ('edge_cases', 'Edge Cases'),
        ('user_generated', 'User Generated'),
        ('performance', 'Performance Tests'),
    ])
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    version = models.CharField(max_length=20, default="1.0")
    
    # Configuration
    expected_results_count = models.IntegerField(default=10, help_text="Expected number of results per query")
    timeout_seconds = models.IntegerField(default=30, help_text="Timeout for query execution")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.category})"
    
    class Meta:
        db_table = "benchmark_query_sets"
        ordering = ['-created_at']


class BenchmarkQuery(models.Model):
    """Individual benchmark query with expected results"""
    
    query_set = models.ForeignKey(BenchmarkQuerySet, on_delete=models.CASCADE, related_name='queries')
    
    # Query information
    query_text = models.TextField()
    query_type = models.CharField(max_length=50, choices=[
        ('exact_match', 'Exact Match'),
        ('semantic', 'Semantic'),
        ('hybrid', 'Hybrid'),
        ('faceted', 'Faceted'),
        ('complex', 'Complex'),
    ])
    
    # Expected results (JSON field storing case IDs and relevance scores)
    expected_results = models.JSONField(default=list, help_text="List of expected case IDs with relevance scores")
    
    # Query metadata
    difficulty_level = models.IntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Query difficulty (1=very easy, 5=very hard)"
    )
    legal_domain = models.CharField(max_length=100, blank=True, help_text="Legal domain (criminal, civil, constitutional, etc.)")
    
    # Performance expectations
    expected_latency_ms = models.IntegerField(default=1000, help_text="Expected response time in milliseconds")
    min_relevance_score = models.FloatField(default=0.7, help_text="Minimum expected relevance score")
    
    # Status
    is_active = models.BooleanField(default=True)
    last_used = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.query_text[:50]}... ({self.query_type})"
    
    class Meta:
        db_table = "benchmark_queries"
        unique_together = ['query_set', 'query_text']
        ordering = ['query_set', 'query_text']


class BenchmarkExecution(models.Model):
    """Record of a benchmark execution run"""
    
    query_set = models.ForeignKey(BenchmarkQuerySet, on_delete=models.CASCADE, related_name='executions')
    
    # Execution metadata
    execution_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Configuration used
    search_mode = models.CharField(max_length=20, choices=[
        ('lexical', 'Lexical'),
        ('semantic', 'Semantic'),
        ('hybrid', 'Hybrid'),
    ])
    ranking_algorithm = models.CharField(max_length=50, choices=[
        ('fast_ranking', 'Fast Ranking'),
        ('advanced_ranking', 'Advanced Ranking'),
    ])
    ranking_config = models.JSONField(default=dict, help_text="Ranking configuration parameters")
    
    # Execution status
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], default='pending')
    
    # Results summary
    total_queries = models.IntegerField(default=0)
    successful_queries = models.IntegerField(default=0)
    failed_queries = models.IntegerField(default=0)
    
    # Performance metrics
    total_execution_time = models.FloatField(default=0.0, help_text="Total execution time in seconds")
    average_latency_ms = models.FloatField(default=0.0, help_text="Average query latency in milliseconds")
    min_latency_ms = models.FloatField(default=0.0)
    max_latency_ms = models.FloatField(default=0.0)
    
    # Quality metrics
    average_precision_at_10 = models.FloatField(default=0.0)
    average_recall_at_10 = models.FloatField(default=0.0)
    average_mrr = models.FloatField(default=0.0, help_text="Mean Reciprocal Rank")
    average_ndcg_at_10 = models.FloatField(default=0.0, help_text="Normalized Discounted Cumulative Gain")
    
    # System metrics
    memory_usage_mb = models.FloatField(default=0.0)
    cpu_usage_percent = models.FloatField(default=0.0)
    
    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.execution_name} ({self.status})"
    
    @property
    def duration(self):
        """Calculate execution duration"""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    @property
    def success_rate(self):
        """Calculate success rate percentage"""
        if self.total_queries > 0:
            return (self.successful_queries / self.total_queries) * 100
        return 0.0
    
    class Meta:
        db_table = "benchmark_executions"
        ordering = ['-started_at']


class BenchmarkResult(models.Model):
    """Individual query result from a benchmark execution"""
    
    execution = models.ForeignKey(BenchmarkExecution, on_delete=models.CASCADE, related_name='results')
    query = models.ForeignKey(BenchmarkQuery, on_delete=models.CASCADE, related_name='results')
    
    # Query execution details
    query_text = models.TextField()  # Store actual query text used
    search_mode = models.CharField(max_length=20)
    ranking_algorithm = models.CharField(max_length=50)
    
    # Results
    returned_results = models.JSONField(default=list, help_text="List of returned case IDs with scores")
    total_results_found = models.IntegerField(default=0)
    execution_time_ms = models.FloatField(default=0.0)
    
    # Quality metrics
    precision_at_10 = models.FloatField(default=0.0)
    recall_at_10 = models.FloatField(default=0.0)
    mrr = models.FloatField(default=0.0)
    ndcg_at_10 = models.FloatField(default=0.0)
    
    # Detailed scoring
    relevance_scores = models.JSONField(default=list, help_text="Relevance scores for each result")
    ranking_quality_score = models.FloatField(default=0.0, help_text="Overall ranking quality (0-1)")
    
    # Performance metrics
    memory_usage_mb = models.FloatField(default=0.0)
    cpu_usage_percent = models.FloatField(default=0.0)
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('success', 'Success'),
        ('timeout', 'Timeout'),
        ('error', 'Error'),
        ('no_results', 'No Results'),
    ], default='success')
    error_message = models.TextField(blank=True, null=True)
    
    # Timestamps
    executed_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.query.query_text[:30]}... ({self.status})"
    
    class Meta:
        db_table = "benchmark_results"
        unique_together = ['execution', 'query']
        ordering = ['execution', 'query']


class BenchmarkComparison(models.Model):
    """Comparison between different benchmark executions"""
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Executions being compared
    baseline_execution = models.ForeignKey(
        BenchmarkExecution, 
        on_delete=models.CASCADE, 
        related_name='baseline_comparisons'
    )
    comparison_executions = models.ManyToManyField(
        BenchmarkExecution, 
        related_name='comparison_analyses'
    )
    
    # Comparison metrics
    performance_improvement = models.FloatField(default=0.0, help_text="Percentage improvement in performance")
    quality_improvement = models.FloatField(default=0.0, help_text="Percentage improvement in quality")
    
    # Detailed comparison results
    comparison_results = models.JSONField(default=dict, help_text="Detailed comparison metrics")
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} (vs {self.baseline_execution.execution_name})"
    
    class Meta:
        db_table = "benchmark_comparisons"
        ordering = ['-created_at']


class BenchmarkConfiguration(models.Model):
    """Saved benchmark configurations for reuse"""
    
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    
    # Search configuration
    search_mode = models.CharField(max_length=20)
    ranking_algorithm = models.CharField(max_length=50)
    ranking_config = models.JSONField(default=dict)
    
    # Benchmark settings
    query_sets = models.ManyToManyField(BenchmarkQuerySet, blank=True)
    timeout_seconds = models.IntegerField(default=30)
    max_results_per_query = models.IntegerField(default=100)
    
    # Performance settings
    enable_performance_monitoring = models.BooleanField(default=True)
    enable_quality_metrics = models.BooleanField(default=True)
    enable_system_metrics = models.BooleanField(default=False)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.search_mode}/{self.ranking_algorithm})"
    
    class Meta:
        db_table = "benchmark_configurations"
        ordering = ['-is_default', 'name']


class BenchmarkReport(models.Model):
    """Generated benchmark reports"""
    
    execution = models.ForeignKey(BenchmarkExecution, on_delete=models.CASCADE, related_name='reports')
    
    # Report metadata
    report_name = models.CharField(max_length=200)
    report_type = models.CharField(max_length=50, choices=[
        ('summary', 'Summary'),
        ('detailed', 'Detailed'),
        ('comparison', 'Comparison'),
        ('performance', 'Performance'),
        ('quality', 'Quality'),
    ])
    
    # Report content
    report_data = models.JSONField(default=dict, help_text="Report data and metrics")
    report_html = models.TextField(blank=True, help_text="HTML formatted report")
    report_pdf_path = models.CharField(max_length=500, blank=True, help_text="Path to PDF report file")
    
    # Status
    is_generated = models.BooleanField(default=False)
    generation_time = models.FloatField(default=0.0, help_text="Time to generate report in seconds")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    generated_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.report_name} ({self.report_type})"
    
    class Meta:
        db_table = "benchmark_reports"
        ordering = ['-created_at']

