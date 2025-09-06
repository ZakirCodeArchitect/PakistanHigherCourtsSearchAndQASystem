"""
Search Benchmarking API Views
API endpoints for benchmark management and execution.
"""

import logging
from typing import Dict, List, Any
from datetime import datetime

from django.http import JsonResponse, FileResponse, Http404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import os
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Max, Min

from search_benchmarking.models import (
    BenchmarkQuerySet, BenchmarkQuery, BenchmarkExecution, 
    BenchmarkResult, BenchmarkComparison, BenchmarkConfiguration, BenchmarkReport
)
from search_benchmarking.services.benchmark_collector import BenchmarkCollector
from search_benchmarking.services.relevance_evaluator import RelevanceEvaluator
from search_benchmarking.services.performance_analyzer import PerformanceAnalyzer
from search_benchmarking.services.comparison_engine import ComparisonEngine
from search_benchmarking.services.report_generator import ReportGenerator

logger = logging.getLogger(__name__)


class BenchmarkQuerySetAPIView(APIView):
    """API for managing benchmark query sets"""
    
    def get(self, request, query_set_id=None):
        """Get all benchmark query sets or a specific query set"""
        if query_set_id:
            return self._get_query_set_detail(request, query_set_id)
        else:
            return self._get_query_sets_list(request)
    
    def _get_query_set_detail(self, request, query_set_id):
        """Get details for a specific query set"""
        try:
            query_set = BenchmarkQuerySet.objects.get(id=query_set_id)
            
            return Response({
                'id': query_set.id,
                'name': query_set.name,
                'description': query_set.description,
                'category': query_set.category,
                'is_active': query_set.is_active,
                'version': query_set.version,
                'query_count': query_set.queries.filter(is_active=True).count(),
                'execution_count': query_set.executions.count(),
                'created_at': query_set.created_at,
                'updated_at': query_set.updated_at
            }, status=status.HTTP_200_OK)
            
        except BenchmarkQuerySet.DoesNotExist:
            return Response({
                'error': 'Query set not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error getting query set detail: {str(e)}")
            return Response({
                'error': 'Failed to retrieve query set details',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_query_sets_list(self, request):
        """Get all benchmark query sets with optional filtering"""
        try:
            # Parse query parameters
            category = request.GET.get('category')
            is_active = request.GET.get('is_active', 'true').lower() == 'true'
            search = request.GET.get('search', '').strip()
            
            # Build queryset
            queryset = BenchmarkQuerySet.objects.all()
            
            if category:
                queryset = queryset.filter(category=category)
            
            if is_active:
                queryset = queryset.filter(is_active=True)
            
            if search:
                queryset = queryset.filter(
                    Q(name__icontains=search) | 
                    Q(description__icontains=search)
                )
            
            # Pagination
            page = int(request.GET.get('page', 1))
            page_size = min(int(request.GET.get('page_size', 20)), 100)
            
            paginator = Paginator(queryset.order_by('-created_at'), page_size)
            page_obj = paginator.get_page(page)
            
            # Serialize data
            query_sets = []
            for qs in page_obj:
                query_sets.append({
                    'id': qs.id,
                    'name': qs.name,
                    'description': qs.description,
                    'category': qs.category,
                    'is_active': qs.is_active,
                    'version': qs.version,
                    'query_count': qs.queries.filter(is_active=True).count(),
                    'execution_count': qs.executions.count(),
                    'created_at': qs.created_at,
                    'updated_at': qs.updated_at
                })
            
            return Response({
                'query_sets': query_sets,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_pages': paginator.num_pages,
                    'total_count': paginator.count,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous()
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting benchmark query sets: {str(e)}")
            return Response({
                'error': 'Failed to retrieve benchmark query sets',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """Create a new benchmark query set"""
        try:
            data = request.data
            
            # Validate required fields
            required_fields = ['name', 'category']
            for field in required_fields:
                if field not in data or not data[field]:
                    return Response({
                        'error': f'Missing required field: {field}'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create query set
            query_set = BenchmarkQuerySet.objects.create(
                name=data['name'],
                description=data.get('description', ''),
                category=data['category'],
                expected_results_count=data.get('expected_results_count', 10),
                timeout_seconds=data.get('timeout_seconds', 30),
                version=data.get('version', '1.0'),
                is_active=data.get('is_active', True)
            )
            
            return Response({
                'id': query_set.id,
                'name': query_set.name,
                'message': 'Benchmark query set created successfully'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating benchmark query set: {str(e)}")
            return Response({
                'error': 'Failed to create benchmark query set',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BenchmarkQueryAPIView(APIView):
    """API for managing benchmark queries"""
    
    def get(self, request, query_set_id):
        """Get all queries for a specific query set"""
        try:
            query_set = BenchmarkQuerySet.objects.get(id=query_set_id)
            
            # Parse query parameters
            is_active = request.GET.get('is_active', 'true').lower() == 'true'
            query_type = request.GET.get('query_type')
            difficulty_level = request.GET.get('difficulty_level')
            
            # Build queryset
            queryset = query_set.queries.all()
            
            if is_active:
                queryset = queryset.filter(is_active=True)
            
            if query_type:
                queryset = queryset.filter(query_type=query_type)
            
            if difficulty_level:
                queryset = queryset.filter(difficulty_level=int(difficulty_level))
            
            # Serialize data
            queries = []
            for query in queryset.order_by('query_text'):
                queries.append({
                    'id': query.id,
                    'query_text': query.query_text,
                    'query_type': query.query_type,
                    'difficulty_level': query.difficulty_level,
                    'legal_domain': query.legal_domain,
                    'expected_results_count': len(query.expected_results),
                    'expected_latency_ms': query.expected_latency_ms,
                    'min_relevance_score': query.min_relevance_score,
                    'is_active': query.is_active,
                    'last_used': query.last_used,
                    'created_at': query.created_at
                })
            
            return Response({
                'query_set': {
                    'id': query_set.id,
                    'name': query_set.name,
                    'description': query_set.description,
                    'category': query_set.category
                },
                'queries': queries,
                'total_count': len(queries)
            }, status=status.HTTP_200_OK)
            
        except BenchmarkQuerySet.DoesNotExist:
            return Response({
                'error': 'Benchmark query set not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error getting benchmark queries: {str(e)}")
            return Response({
                'error': 'Failed to retrieve benchmark queries',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request, query_set_id):
        """Create a new benchmark query"""
        try:
            query_set = BenchmarkQuerySet.objects.get(id=query_set_id)
            data = request.data
            
            # Validate required fields
            if 'query_text' not in data or not data['query_text']:
                return Response({
                    'error': 'Missing required field: query_text'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create query
            query = BenchmarkQuery.objects.create(
                query_set=query_set,
                query_text=data['query_text'],
                query_type=data.get('query_type', 'hybrid'),
                expected_results=data.get('expected_results', []),
                difficulty_level=data.get('difficulty_level', 3),
                legal_domain=data.get('legal_domain', ''),
                expected_latency_ms=data.get('expected_latency_ms', 1000),
                min_relevance_score=data.get('min_relevance_score', 0.7),
                is_active=data.get('is_active', True)
            )
            
            return Response({
                'id': query.id,
                'query_text': query.query_text,
                'message': 'Benchmark query created successfully'
            }, status=status.HTTP_201_CREATED)
            
        except BenchmarkQuerySet.DoesNotExist:
            return Response({
                'error': 'Benchmark query set not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error creating benchmark query: {str(e)}")
            return Response({
                'error': 'Failed to create benchmark query',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class BenchmarkExecutionAPIView(APIView):
    """API for managing benchmark executions"""
    
    def get(self, request):
        """Get all benchmark executions with optional filtering"""
        try:
            # Parse query parameters
            query_set_id = request.GET.get('query_set_id')
            status_filter = request.GET.get('status')
            search_mode = request.GET.get('search_mode')
            ranking_algorithm = request.GET.get('ranking_algorithm')
            
            # Build queryset
            queryset = BenchmarkExecution.objects.all()
            
            if query_set_id:
                queryset = queryset.filter(query_set_id=query_set_id)
            
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            
            if search_mode:
                queryset = queryset.filter(search_mode=search_mode)
            
            if ranking_algorithm:
                queryset = queryset.filter(ranking_algorithm=ranking_algorithm)
            
            # Pagination
            page = int(request.GET.get('page', 1))
            page_size = min(int(request.GET.get('page_size', 20)), 100)
            
            paginator = Paginator(queryset.order_by('-started_at'), page_size)
            page_obj = paginator.get_page(page)
            
            # Serialize data
            executions = []
            for execution in page_obj:
                executions.append({
                    'id': execution.id,
                    'execution_name': execution.execution_name,
                    'description': execution.description,
                    'query_set': {
                        'id': execution.query_set.id,
                        'name': execution.query_set.name,
                        'category': execution.query_set.category
                    },
                    'search_mode': execution.search_mode,
                    'ranking_algorithm': execution.ranking_algorithm,
                    'status': execution.status,
                    'total_queries': execution.total_queries,
                    'successful_queries': execution.successful_queries,
                    'failed_queries': execution.failed_queries,
                    'success_rate': execution.success_rate,
                    'average_latency_ms': execution.average_latency_ms,
                    'average_precision_at_10': execution.average_precision_at_10,
                    'average_recall_at_10': execution.average_recall_at_10,
                    'average_mrr': execution.average_mrr,
                    'average_ndcg_at_10': execution.average_ndcg_at_10,
                    'total_execution_time': execution.total_execution_time,
                    'started_at': execution.started_at,
                    'completed_at': execution.completed_at,
                    'duration': execution.duration
                })
            
            return Response({
                'executions': executions,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_pages': paginator.num_pages,
                    'total_count': paginator.count,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous()
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting benchmark executions: {str(e)}")
            return Response({
                'error': 'Failed to retrieve benchmark executions',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """Start a new benchmark execution"""
        try:
            data = request.data
            
            # Validate required fields
            if 'query_set_id' not in data:
                return Response({
                    'error': 'Missing required field: query_set_id'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get query set
            try:
                query_set = BenchmarkQuerySet.objects.get(id=data['query_set_id'])
            except BenchmarkQuerySet.DoesNotExist:
                return Response({
                    'error': 'Benchmark query set not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get configuration if provided
            configuration = None
            if 'configuration_id' in data:
                try:
                    configuration = BenchmarkConfiguration.objects.get(id=data['configuration_id'])
                except BenchmarkConfiguration.DoesNotExist:
                    return Response({
                        'error': 'Benchmark configuration not found'
                    }, status=status.HTTP_404_NOT_FOUND)
            
            # Start benchmark collection
            collector = BenchmarkCollector()
            execution = collector.collect_benchmark_data(
                query_set_id=data['query_set_id'],
                configuration=configuration,
                execution_name=data.get('execution_name')
            )
            
            return Response({
                'id': execution.id,
                'execution_name': execution.execution_name,
                'status': execution.status,
                'message': 'Benchmark execution started successfully'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error starting benchmark execution: {str(e)}")
            return Response({
                'error': 'Failed to start benchmark execution',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BenchmarkExecutionDetailAPIView(APIView):
    """API for individual benchmark execution details"""
    
    def get(self, request, execution_id):
        """Get detailed information about a specific execution"""
        try:
            execution = BenchmarkExecution.objects.get(id=execution_id)
            
            # Get results
            results = execution.results.all()
            
            # Calculate additional metrics
            performance_analyzer = PerformanceAnalyzer()
            performance_analysis = performance_analyzer.analyze_execution_performance(execution)
            
            relevance_evaluator = RelevanceEvaluator()
            quality_analysis = relevance_evaluator.evaluate_execution_quality(list(results))
            
            # Serialize execution data
            execution_data = {
                'id': execution.id,
                'execution_name': execution.execution_name,
                'description': execution.description,
                'query_set': {
                    'id': execution.query_set.id,
                    'name': execution.query_set.name,
                    'description': execution.query_set.description,
                    'category': execution.query_set.category
                },
                'configuration': {
                    'search_mode': execution.search_mode,
                    'ranking_algorithm': execution.ranking_algorithm,
                    'ranking_config': execution.ranking_config
                },
                'status': execution.status,
                'summary': {
                    'total_queries': execution.total_queries,
                    'successful_queries': execution.successful_queries,
                    'failed_queries': execution.failed_queries,
                    'success_rate': execution.success_rate,
                    'total_execution_time': execution.total_execution_time,
                    'average_latency_ms': execution.average_latency_ms,
                    'average_precision_at_10': execution.average_precision_at_10,
                    'average_recall_at_10': execution.average_recall_at_10,
                    'average_mrr': execution.average_mrr,
                    'average_ndcg_at_10': execution.average_ndcg_at_10
                },
                'performance_analysis': performance_analysis,
                'quality_analysis': quality_analysis,
                'started_at': execution.started_at,
                'completed_at': execution.completed_at,
                'duration': execution.duration
            }
            
            return Response(execution_data, status=status.HTTP_200_OK)
            
        except BenchmarkExecution.DoesNotExist:
            return Response({
                'error': 'Benchmark execution not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error getting execution details: {str(e)}")
            return Response({
                'error': 'Failed to retrieve execution details',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BenchmarkComparisonAPIView(APIView):
    """API for benchmark comparisons"""
    
    def get(self, request):
        """Get all benchmark comparisons"""
        try:
            # Parse query parameters
            baseline_execution_id = request.GET.get('baseline_execution_id')
            
            # Build queryset
            queryset = BenchmarkComparison.objects.all()
            
            if baseline_execution_id:
                queryset = queryset.filter(baseline_execution_id=baseline_execution_id)
            
            # Pagination
            page = int(request.GET.get('page', 1))
            page_size = min(int(request.GET.get('page_size', 20)), 100)
            
            paginator = Paginator(queryset.order_by('-created_at'), page_size)
            page_obj = paginator.get_page(page)
            
            # Serialize data
            comparisons = []
            for comparison in page_obj:
                comparisons.append({
                    'id': comparison.id,
                    'name': comparison.name,
                    'description': comparison.description,
                    'baseline_execution': {
                        'id': comparison.baseline_execution.id,
                        'name': comparison.baseline_execution.execution_name
                    },
                    'comparison_executions_count': comparison.comparison_executions.count(),
                    'performance_improvement': comparison.performance_improvement,
                    'quality_improvement': comparison.quality_improvement,
                    'is_active': comparison.is_active,
                    'created_at': comparison.created_at
                })
            
            return Response({
                'comparisons': comparisons,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_pages': paginator.num_pages,
                    'total_count': paginator.count,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous()
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting benchmark comparisons: {str(e)}")
            return Response({
                'error': 'Failed to retrieve benchmark comparisons',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """Create a new benchmark comparison"""
        try:
            data = request.data
            
            # Validate required fields
            if 'baseline_execution_id' not in data:
                return Response({
                    'error': 'Missing required field: baseline_execution_id'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if 'comparison_execution_ids' not in data or not data['comparison_execution_ids']:
                return Response({
                    'error': 'Missing required field: comparison_execution_ids'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create comparison
            comparison_engine = ComparisonEngine()
            comparison = comparison_engine.compare_executions(
                baseline_execution_id=data['baseline_execution_id'],
                comparison_execution_ids=data['comparison_execution_ids'],
                comparison_name=data.get('comparison_name')
            )
            
            return Response({
                'id': comparison.id,
                'name': comparison.name,
                'performance_improvement': comparison.performance_improvement,
                'quality_improvement': comparison.quality_improvement,
                'message': 'Benchmark comparison created successfully'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating benchmark comparison: {str(e)}")
            return Response({
                'error': 'Failed to create benchmark comparison',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class BenchmarkReportAPIView(APIView):
    """API for generating benchmark reports"""
    
    def post(self, request):
        """Generate a benchmark report"""
        try:
            data = request.data
            
            # Validate required fields
            if 'execution_id' not in data:
                return Response({
                    'error': 'Missing required field: execution_id'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Generate report
            report_generator = ReportGenerator()
            report = report_generator.generate_execution_report(
                execution_id=data['execution_id'],
                report_type=data.get('report_type', 'detailed'),
                format=data.get('format', 'html')
            )
            
            return Response({
                'id': report.id,
                'report_name': report.report_name,
                'report_type': report.report_type,
                'is_generated': report.is_generated,
                'generated_at': report.generated_at.isoformat() if report.generated_at else None,
                'message': 'Report generated successfully'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error generating benchmark report: {str(e)}")
            return Response({
                'error': 'Failed to generate benchmark report',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BenchmarkStatisticsAPIView(APIView):
    """API for benchmark statistics and analytics"""
    
    def get(self, request):
        """Get benchmark statistics"""
        try:
            # Get basic statistics
            total_query_sets = BenchmarkQuerySet.objects.count()
            total_queries = BenchmarkQuery.objects.count()
            total_executions = BenchmarkExecution.objects.count()
            total_comparisons = BenchmarkComparison.objects.count()
            
            # Get recent activity
            recent_executions = BenchmarkExecution.objects.filter(
                started_at__gte=timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            ).count()
            
            # Get average performance metrics
            avg_metrics = BenchmarkExecution.objects.filter(
                status='completed'
            ).aggregate(
                avg_latency=Avg('average_latency_ms'),
                avg_precision=Avg('average_precision_at_10'),
                avg_recall=Avg('average_recall_at_10'),
                avg_mrr=Avg('average_mrr')
            )
            
            # Get query set distribution
            query_set_categories = BenchmarkQuerySet.objects.values('category').annotate(
                count=Count('id')
            ).order_by('-count')
            
            # Get execution status distribution
            execution_statuses = BenchmarkExecution.objects.values('status').annotate(
                count=Count('id')
            ).order_by('-count')
            
            statistics = {
                'overview': {
                    'total_query_sets': total_query_sets,
                    'total_queries': total_queries,
                    'total_executions': total_executions,
                    'total_comparisons': total_comparisons,
                    'recent_executions_today': recent_executions
                },
                'performance_metrics': {
                    'average_latency_ms': round(avg_metrics['avg_latency'] or 0, 2),
                    'average_precision_at_10': round(avg_metrics['avg_precision'] or 0, 3),
                    'average_recall_at_10': round(avg_metrics['avg_recall'] or 0, 3),
                    'average_mrr': round(avg_metrics['avg_mrr'] or 0, 3)
                },
                'query_set_categories': list(query_set_categories),
                'execution_statuses': list(execution_statuses)
            }
            
            return Response(statistics, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting benchmark statistics: {str(e)}")
            return Response({
                'error': 'Failed to retrieve benchmark statistics',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReportViewerView(View):
    """View to serve generated benchmark reports"""
    
    def get(self, request, report_filename):
        """Serve a benchmark report file"""
        try:
            # Sanitize filename to prevent directory traversal
            safe_filename = os.path.basename(report_filename)
            
            # Construct file path
            reports_dir = os.path.join(settings.MEDIA_ROOT, 'benchmark_reports')
            file_path = os.path.join(reports_dir, safe_filename)
            
            # Check if file exists
            if not os.path.exists(file_path):
                raise Http404("Report file not found")
            
            # Check if it's a valid report file
            if not safe_filename.endswith('.html'):
                raise Http404("Invalid report file format")
            
            # Serve the file with download headers
            response = FileResponse(
                open(file_path, 'rb'),
                content_type='text/html',
                filename=safe_filename
            )
            # Set headers to force download
            response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
            response['Content-Type'] = 'application/octet-stream'
            return response
            
        except Exception as e:
            logger.error(f"Error serving report file {report_filename}: {str(e)}")
            raise Http404("Error serving report file")

