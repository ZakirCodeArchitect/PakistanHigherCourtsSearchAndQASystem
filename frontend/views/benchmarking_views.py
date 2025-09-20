"""
Benchmarking Module Views
Views for the Search Benchmarking system frontend
"""

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views import View
import json
import logging

logger = logging.getLogger(__name__)


class BenchmarkingDashboardView(View):
    """Benchmarking dashboard"""
    
    def get(self, request):
        """Display benchmarking dashboard"""
        context = {
            'title': 'Search Benchmarking Dashboard',
            'description': 'Monitor and analyze search performance benchmarks'
        }
        return render(request, 'benchmarking/dashboard.html', context)


class QuerySetsView(View):
    """Query Sets management interface"""
    
    def get(self, request):
        """Display query sets management interface"""
        context = {
            'title': 'Benchmark Query Sets',
            'description': 'Manage benchmark query sets for performance testing'
        }
        return render(request, 'benchmarking/query_sets.html', context)


class QuerySetDetailView(View):
    """Query Set detail page"""
    
    def get(self, request, query_set_id):
        """Display query set detail page"""
        context = {
            'title': f'Query Set {query_set_id} Details',
            'description': 'Detailed view of benchmark query set',
            'query_set_id': query_set_id
        }
        return render(request, 'benchmarking/query_set_detail.html', context)


class ExecutionsView(View):
    """Benchmark executions interface"""
    
    def get(self, request):
        """Display benchmark executions interface"""
        context = {
            'title': 'Benchmark Executions',
            'description': 'View and manage benchmark execution history'
        }
        return render(request, 'benchmarking/executions.html', context)


class ExecutionDetailView(View):
    """Execution detail page"""
    
    def get(self, request, execution_id):
        """Display execution detail page"""
        context = {
            'title': f'Execution {execution_id} Details',
            'description': 'Detailed view of benchmark execution results',
            'execution_id': execution_id
        }
        return render(request, 'benchmarking/execution_detail.html', context)


class ReportsView(View):
    """Benchmark reports interface"""
    
    def get(self, request):
        """Display benchmark reports interface"""
        context = {
            'title': 'Benchmark Reports',
            'description': 'Generate and view benchmark performance reports'
        }
        return render(request, 'benchmarking/reports.html', context)


# API Views for Benchmarking
@csrf_exempt
@require_http_methods(["GET"])
def benchmark_statistics_api(request):
    """API endpoint for benchmark statistics"""
    try:
        # Mock statistics - in real implementation, query the database
        statistics = {
            'total_executions': 150,
            'avg_response_time': 2.5,
            'success_rate': 0.95,
            'total_queries': 1250
        }
        
        return JsonResponse(statistics)
        
    except Exception as e:
        logger.error(f"Error in benchmark statistics API: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def create_benchmark_execution_api(request):
    """API endpoint to create benchmark execution"""
    try:
        data = json.loads(request.body)
        query_set_id = data.get('query_set_id')
        
        # Mock execution creation - in real implementation, create execution
        response = {
            'execution_id': 123,
            'status': 'created',
            'message': f'Benchmark execution created for query set {query_set_id}'
        }
        
        return JsonResponse(response)
        
    except Exception as e:
        logger.error(f"Error in create benchmark execution API: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def benchmark_reports_api(request):
    """API endpoint for benchmark reports"""
    try:
        # Mock reports - in real implementation, query the database
        reports = [
            {
                'id': 1,
                'name': 'Weekly Performance Report',
                'created_at': '2025-09-20',
                'status': 'completed'
            },
            {
                'id': 2,
                'name': 'Monthly Benchmark Analysis',
                'created_at': '2025-09-15',
                'status': 'completed'
            }
        ]
        
        return JsonResponse({'reports': reports})
        
    except Exception as e:
        logger.error(f"Error in benchmark reports API: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)
