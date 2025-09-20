"""
Search Benchmarking URL Configuration
URL patterns for benchmark management and execution APIs.
"""

from django.urls import path, include
from django.views.generic import TemplateView
from . import views

app_name = 'search_benchmarking'

urlpatterns = [
    # API Endpoints
           path('api/query-sets/', views.BenchmarkQuerySetAPIView.as_view(), name='api_query_sets'),
           path('api/query-sets/<int:query_set_id>/', views.BenchmarkQuerySetAPIView.as_view(), name='api_query_set_detail'),
    path('api/query-sets/<int:query_set_id>/queries/', views.BenchmarkQueryAPIView.as_view(), name='api_queries'),
    path('api/executions/', views.BenchmarkExecutionAPIView.as_view(), name='api_executions'),
    path('api/executions/<int:execution_id>/', views.BenchmarkExecutionDetailAPIView.as_view(), name='api_execution_detail'),
    path('api/comparisons/', views.BenchmarkComparisonAPIView.as_view(), name='api_comparisons'),
    path('api/reports/', views.BenchmarkReportAPIView.as_view(), name='api_reports'),
    path('api/statistics/', views.BenchmarkStatisticsAPIView.as_view(), name='api_statistics'),
    
    # Frontend Views
    path('', TemplateView.as_view(template_name='benchmarking/dashboard.html'), name='dashboard'),
    path('dashboard/', TemplateView.as_view(template_name='benchmarking/dashboard.html'), name='dashboard'),
    path('query-sets/', TemplateView.as_view(template_name='benchmarking/query_sets.html'), name='query_sets'),
    path('executions/', TemplateView.as_view(template_name='benchmarking/executions.html'), name='executions'),
           path('executions/<int:execution_id>/', TemplateView.as_view(template_name='benchmarking/execution_detail.html'), name='execution_detail'),
           path('query-sets/<int:query_set_id>/', TemplateView.as_view(template_name='benchmarking/query_set_detail.html'), name='query_set_detail'),
           path('reports/', TemplateView.as_view(template_name='benchmarking/reports.html'), name='reports'),
           path('reports/view/<str:report_filename>', views.ReportViewerView.as_view(), name='view_report'),
       ]

