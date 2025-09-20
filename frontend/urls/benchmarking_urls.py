from django.urls import path
from frontend.views import benchmarking_views

urlpatterns = [
    # Benchmarking pages
    path('benchmarking/', benchmarking_views.BenchmarkingDashboardView.as_view(), name='benchmarking_dashboard'),
    path('benchmarking/query-sets/', benchmarking_views.QuerySetsView.as_view(), name='benchmarking_query_sets'),
    path('benchmarking/query-sets/<int:query_set_id>/', benchmarking_views.QuerySetDetailView.as_view(), name='benchmarking_query_set_detail'),
    path('benchmarking/executions/', benchmarking_views.ExecutionsView.as_view(), name='benchmarking_executions'),
    path('benchmarking/executions/<int:execution_id>/', benchmarking_views.ExecutionDetailView.as_view(), name='benchmarking_execution_detail'),
    path('benchmarking/reports/', benchmarking_views.ReportsView.as_view(), name='benchmarking_reports'),
    
    # API endpoints
    path('api/benchmarking/statistics/', benchmarking_views.benchmark_statistics_api, name='benchmarking_statistics_api'),
    path('api/benchmarking/create-execution/', benchmarking_views.create_benchmark_execution_api, name='benchmarking_create_execution_api'),
    path('api/benchmarking/reports/', benchmarking_views.benchmark_reports_api, name='benchmarking_reports_api'),
]
