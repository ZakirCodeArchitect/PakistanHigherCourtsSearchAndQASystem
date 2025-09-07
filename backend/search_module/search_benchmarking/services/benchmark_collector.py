"""
Benchmark Collector Service
Collects benchmark data by executing queries and measuring performance.
"""

import time
import logging
import threading

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from django.utils import timezone
from django.db import transaction

from search_benchmarking.models import (
    BenchmarkQuerySet, BenchmarkQuery, BenchmarkExecution, 
    BenchmarkResult, BenchmarkConfiguration
)
try:
    from search_indexing.services.query_normalization import QueryNormalizationService
    from search_indexing.services.hybrid_indexing import HybridIndexingService
    from search_indexing.services.fast_ranking import FastRankingService
    from search_indexing.services.advanced_ranking import AdvancedRankingService
except ImportError:
    # Fallback for development/testing
    QueryNormalizationService = None
    HybridIndexingService = None
    FastRankingService = None
    AdvancedRankingService = None

logger = logging.getLogger(__name__)


class BenchmarkCollector:
    """Service for collecting benchmark data by executing queries"""
    
    def __init__(self):
        if QueryNormalizationService is None:
            raise ImportError("Search indexing services are not available. Please ensure the search_indexing app is properly configured.")
        
        self.query_normalizer = QueryNormalizationService()
        self.hybrid_service = HybridIndexingService(use_pinecone=True)
        self.fast_ranking = FastRankingService()
        self.advanced_ranking = AdvancedRankingService()
        
        # Performance monitoring
        self.performance_monitor = PerformanceMonitor() if PSUTIL_AVAILABLE else None
        self._monitoring_active = False
        self._monitoring_thread = None
        self._system_metrics = []
    
    def collect_benchmark_data(self, 
                             query_set_id: int,
                             configuration: Optional[BenchmarkConfiguration] = None,
                             execution_name: str = None) -> BenchmarkExecution:
        """
        Collect benchmark data for a query set
        
        Args:
            query_set_id: ID of the benchmark query set
            configuration: Benchmark configuration to use
            execution_name: Name for this execution
            
        Returns:
            BenchmarkExecution object with results
        """
        try:
            # Get query set
            query_set = BenchmarkQuerySet.objects.get(id=query_set_id)
            
            # Create execution record
            execution = self._create_execution_record(
                query_set, configuration, execution_name
            )
            
            # Start performance monitoring
            self._start_performance_monitoring()
            
            try:
                # Execute all queries in the set
                results = self._execute_queries(query_set, execution, configuration)
                
                # Calculate summary metrics
                self._calculate_summary_metrics(execution, results)
                
                # Update execution status
                execution.status = 'completed'
                execution.completed_at = timezone.now()
                execution.save()
                
                logger.info(f"Benchmark execution completed: {execution.execution_name}")
                return execution
                
            except Exception as e:
                execution.status = 'failed'
                execution.completed_at = timezone.now()
                execution.save()
                logger.error(f"Benchmark execution failed: {str(e)}")
                raise
                
            finally:
                self._stop_performance_monitoring()
                
        except Exception as e:
            logger.error(f"Error collecting benchmark data: {str(e)}")
            raise
    
    def _create_execution_record(self, 
                               query_set: BenchmarkQuerySet,
                               configuration: Optional[BenchmarkConfiguration],
                               execution_name: str) -> BenchmarkExecution:
        """Create a new benchmark execution record"""
        
        if not execution_name:
            execution_name = f"{query_set.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Use configuration or intelligent defaults based on query set category
        if configuration:
            search_mode = configuration.search_mode
            ranking_algorithm = configuration.ranking_algorithm
            ranking_config = configuration.ranking_config
        else:
            # Intelligent mode selection based on query set category
            if query_set.category == 'exact_match':
                search_mode = 'lexical'  # Exact matches should use lexical search
            elif query_set.category == 'semantic':
                search_mode = 'semantic'  # Semantic queries should use semantic search
            elif query_set.category == 'lexical':
                search_mode = 'lexical'  # Lexical queries should use lexical search
            else:
                search_mode = 'hybrid'  # Complex and other queries use hybrid
            
            ranking_algorithm = 'fast_ranking'
            ranking_config = {}
        
        execution = BenchmarkExecution.objects.create(
            query_set=query_set,
            execution_name=execution_name,
            search_mode=search_mode,
            ranking_algorithm=ranking_algorithm,
            ranking_config=ranking_config,
            total_queries=query_set.queries.filter(is_active=True).count(),
            status='running'
        )
        
        return execution
    
    def _execute_queries(self, 
                        query_set: BenchmarkQuerySet,
                        execution: BenchmarkExecution,
                        configuration: Optional[BenchmarkConfiguration]) -> List[BenchmarkResult]:
        """Execute all queries in the query set"""
        
        results = []
        queries = query_set.queries.filter(is_active=True)
        
        for query in queries:
            try:
                result = self._execute_single_query(query, execution, configuration)
                results.append(result)
                execution.successful_queries += 1
                
            except Exception as e:
                logger.error(f"Error executing query {query.id}: {str(e)}")
                # Create failed result record
                result = BenchmarkResult.objects.create(
                    execution=execution,
                    query=query,
                    query_text=query.query_text,
                    search_mode=execution.search_mode,
                    ranking_algorithm=execution.ranking_algorithm,
                    status='error',
                    error_message=str(e)
                )
                results.append(result)
                execution.failed_queries += 1
            
            # Update query last_used timestamp
            query.last_used = timezone.now()
            query.save(update_fields=['last_used'])
        
        return results
    
    def _execute_single_query(self, 
                            query: BenchmarkQuery,
                            execution: BenchmarkExecution,
                            configuration: Optional[BenchmarkConfiguration]) -> BenchmarkResult:
        """Execute a single benchmark query"""
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        start_cpu = psutil.Process().cpu_percent()
        
        try:
            # Normalize query
            query_info = self.query_normalizer.normalize_query(query.query_text)
            
            # Execute search based on mode
            if execution.search_mode == 'lexical':
                search_results = self._perform_lexical_search(query.query_text, query_info)
            elif execution.search_mode == 'semantic':
                search_results = self._perform_semantic_search(query.query_text, query_info)
            else:  # hybrid
                search_results = self._perform_hybrid_search(query.query_text, query_info)
            
            # Apply ranking
            if execution.ranking_algorithm == 'advanced_ranking':
                ranked_results = self.advanced_ranking.rank_results(
                    search_results.get('vector_results', []),
                    search_results.get('keyword_results', []),
                    query_info,
                    top_k=100
                )
            else:  # fast_ranking
                ranked_results = self.fast_ranking.rank_results(
                    search_results.get('vector_results', []),
                    search_results.get('keyword_results', []),
                    query.query_text,
                    top_k=100
                )
            
            # Calculate execution metrics
            execution_time = (time.time() - start_time) * 1000  # Convert to ms
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            end_cpu = psutil.Process().cpu_percent()
            
            # Extract results data
            returned_results = []
            for result in ranked_results:
                returned_results.append({
                    'case_id': result.get('case_id'),
                    'score': result.get('final_score', result.get('rank', 0)),
                    'case_number': result.get('case_number', ''),
                    'case_title': result.get('case_title', ''),
                    'court': result.get('court', '')
                })
            
            # Calculate quality metrics
            quality_metrics = self._calculate_quality_metrics(
                query, returned_results
            )
            
            # Create result record
            result = BenchmarkResult.objects.create(
                execution=execution,
                query=query,
                query_text=query.query_text,
                search_mode=execution.search_mode,
                ranking_algorithm=execution.ranking_algorithm,
                returned_results=returned_results,
                total_results_found=len(returned_results),
                execution_time_ms=execution_time,
                precision_at_10=quality_metrics['precision_at_10'],
                recall_at_10=quality_metrics['recall_at_10'],
                mrr=quality_metrics['mrr'],
                ndcg_at_10=quality_metrics['ndcg_at_10'],
                relevance_scores=quality_metrics['relevance_scores'],
                ranking_quality_score=quality_metrics['ranking_quality_score'],
                memory_usage_mb=end_memory - start_memory,
                cpu_usage_percent=end_cpu - start_cpu,
                status='success'
            )
            
            return result
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Error executing query {query.id}: {str(e)}")
            
            # Create error result
            result = BenchmarkResult.objects.create(
                execution=execution,
                query=query,
                query_text=query.query_text,
                search_mode=execution.search_mode,
                ranking_algorithm=execution.ranking_algorithm,
                execution_time_ms=execution_time,
                status='error',
                error_message=str(e)
            )
            
            return result
    
    def _perform_lexical_search(self, query: str, query_info: Dict) -> Dict:
        """Perform lexical search"""
        try:
            keyword_results = self.hybrid_service.keyword_service.search(
                query, top_k=100
            )
            return {
                'vector_results': [],
                'keyword_results': keyword_results
            }
        except Exception as e:
            logger.error(f"Lexical search error: {str(e)}")
            return {'vector_results': [], 'keyword_results': []}
    
    def _perform_semantic_search(self, query: str, query_info: Dict) -> Dict:
        """Perform semantic search"""
        try:
            vector_results = self.hybrid_service.vector_service.search(
                query, top_k=100
            )
            return {
                'vector_results': vector_results,
                'keyword_results': []
            }
        except Exception as e:
            logger.error(f"Semantic search error: {str(e)}")
            return {'vector_results': [], 'keyword_results': []}
    
    def _perform_hybrid_search(self, query: str, query_info: Dict) -> Dict:
        """Perform hybrid search"""
        try:
            hybrid_results = self.hybrid_service.hybrid_search(
                query, top_k=100
            )
            
            # Convert to expected format
            vector_results = []
            keyword_results = []
            
            for result in hybrid_results:
                vector_score = result.get('vector_score', 0)
                keyword_score = result.get('keyword_score', 0)
                
                if vector_score > 0:
                    vector_results.append({
                        'case_id': result['case_id'],
                        'similarity': vector_score,
                        'case_number': result.get('case_number', ''),
                        'case_title': result.get('case_title', ''),
                        'court': result.get('court', ''),
                        'status': result.get('status', ''),
                        'institution_date': result.get('institution_date'),
                        'hearing_date': result.get('hearing_date')
                    })
                
                if keyword_score > 0:
                    keyword_results.append({
                        'case_id': result['case_id'],
                        'rank': keyword_score,
                        'case_number': result.get('case_number', ''),
                        'case_title': result.get('case_title', ''),
                        'court': result.get('court', ''),
                        'status': result.get('status', ''),
                        'institution_date': result.get('institution_date'),
                        'hearing_date': result.get('hearing_date')
                    })
            
            return {
                'vector_results': vector_results,
                'keyword_results': keyword_results
            }
            
        except Exception as e:
            logger.error(f"Hybrid search error: {str(e)}")
            return {'vector_results': [], 'keyword_results': []}
    
    def _calculate_quality_metrics(self, 
                                 query: BenchmarkQuery, 
                                 returned_results: List[Dict]) -> Dict[str, Any]:
        """Calculate quality metrics for a query result"""
        
        expected_case_ids = [item['case_id'] for item in query.expected_results]
        returned_case_ids = [item['case_id'] for item in returned_results[:10]]  # Top 10
        
        # Calculate precision@10
        relevant_returned = set(returned_case_ids).intersection(set(expected_case_ids))
        precision_at_10 = len(relevant_returned) / 10.0 if len(returned_case_ids) > 0 else 0.0
        
        # Calculate recall@10
        recall_at_10 = len(relevant_returned) / len(expected_case_ids) if len(expected_case_ids) > 0 else 0.0
        
        # Calculate MRR (Mean Reciprocal Rank)
        mrr = 0.0
        for i, case_id in enumerate(returned_case_ids):
            if case_id in expected_case_ids:
                mrr = 1.0 / (i + 1)
                break
        
        # Calculate NDCG@10 (simplified version)
        ndcg_at_10 = self._calculate_ndcg(expected_case_ids, returned_case_ids, 10)
        
        # Calculate relevance scores
        relevance_scores = []
        for i, result in enumerate(returned_results[:10]):
            case_id = result['case_id']
            relevance = 1.0 if case_id in expected_case_ids else 0.0
            relevance_scores.append({
                'position': i + 1,
                'case_id': case_id,
                'relevance': relevance,
                'score': result.get('score', 0)
            })
        
        # Calculate overall ranking quality score
        ranking_quality_score = (precision_at_10 + recall_at_10 + mrr + ndcg_at_10) / 4.0
        
        return {
            'precision_at_10': precision_at_10,
            'recall_at_10': recall_at_10,
            'mrr': mrr,
            'ndcg_at_10': ndcg_at_10,
            'relevance_scores': relevance_scores,
            'ranking_quality_score': ranking_quality_score
        }
    
    def _calculate_ndcg(self, expected: List[int], returned: List[int], k: int) -> float:
        """Calculate Normalized Discounted Cumulative Gain at k"""
        if not expected or not returned:
            return 0.0
        
        # Calculate DCG
        dcg = 0.0
        for i, case_id in enumerate(returned[:k]):
            if case_id in expected:
                dcg += 1.0 / (i + 1)
        
        # Calculate IDCG (ideal DCG)
        idcg = 0.0
        for i in range(min(len(expected), k)):
            idcg += 1.0 / (i + 1)
        
        return dcg / idcg if idcg > 0 else 0.0
    
    def _calculate_summary_metrics(self, 
                                 execution: BenchmarkExecution, 
                                 results: List[BenchmarkResult]):
        """Calculate summary metrics for the execution"""
        
        if not results:
            return
        
        # Performance metrics
        latencies = [r.execution_time_ms for r in results if r.execution_time_ms > 0]
        if latencies:
            execution.average_latency_ms = sum(latencies) / len(latencies)
            execution.min_latency_ms = min(latencies)
            execution.max_latency_ms = max(latencies)
        
        # Quality metrics
        precisions = [r.precision_at_10 for r in results if r.precision_at_10 is not None]
        recalls = [r.recall_at_10 for r in results if r.recall_at_10 is not None]
        mrrs = [r.mrr for r in results if r.mrr is not None]
        ndcgs = [r.ndcg_at_10 for r in results if r.ndcg_at_10 is not None]
        
        if precisions:
            execution.average_precision_at_10 = sum(precisions) / len(precisions)
        if recalls:
            execution.average_recall_at_10 = sum(recalls) / len(recalls)
        if mrrs:
            execution.average_mrr = sum(mrrs) / len(mrrs)
        if ndcgs:
            execution.average_ndcg_at_10 = sum(ndcgs) / len(ndcgs)
        
        # System metrics
        memory_usage = [r.memory_usage_mb for r in results if r.memory_usage_mb > 0]
        cpu_usage = [r.cpu_usage_percent for r in results if r.cpu_usage_percent > 0]
        
        if memory_usage:
            execution.memory_usage_mb = sum(memory_usage) / len(memory_usage)
        if cpu_usage:
            execution.cpu_usage_percent = sum(cpu_usage) / len(cpu_usage)
        
        # Total execution time
        if execution.completed_at and execution.started_at:
            execution.total_execution_time = (execution.completed_at - execution.started_at).total_seconds()
        
        execution.save()
    
    def _start_performance_monitoring(self):
        """Start system performance monitoring"""
        if not PSUTIL_AVAILABLE:
            logger.warning("psutil not available, skipping performance monitoring")
            return
            
        self._monitoring_active = True
        self._system_metrics = []
        
        def monitor():
            while self._monitoring_active:
                try:
                    if PSUTIL_AVAILABLE:
                        cpu_percent = psutil.cpu_percent()
                        memory = psutil.virtual_memory()
                        self._system_metrics.append({
                            'timestamp': time.time(),
                            'cpu_percent': cpu_percent,
                            'memory_percent': memory.percent,
                            'memory_available_mb': memory.available / 1024 / 1024
                        })
                    time.sleep(1)  # Monitor every second
                except Exception as e:
                    logger.error(f"Performance monitoring error: {str(e)}")
                    break
        
        self._monitoring_thread = threading.Thread(target=monitor, daemon=True)
        self._monitoring_thread.start()
    
    def _stop_performance_monitoring(self):
        """Stop system performance monitoring"""
        self._monitoring_active = False
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=2)
    
    def get_system_metrics(self) -> List[Dict]:
        """Get collected system metrics"""
        return self._system_metrics.copy()


class PerformanceMonitor:
    """System performance monitoring using psutil"""
    
    def __init__(self):
        self.process = psutil.Process()
        self.initial_cpu = self.process.cpu_percent()
        self.initial_memory = self.process.memory_info()
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current system performance metrics"""
        try:
            return {
                'cpu_percent': self.process.cpu_percent(),
                'memory_mb': self.process.memory_info().rss / 1024 / 1024,
                'memory_percent': self.process.memory_percent(),
                'timestamp': timezone.now().isoformat()
            }
        except Exception as e:
            logger.warning(f"Failed to get system metrics: {e}")
            return {
                'cpu_percent': 0,
                'memory_mb': 0,
                'memory_percent': 0,
                'timestamp': timezone.now().isoformat(),
                'error': str(e)
            }
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        try:
            return {
                'cpu_count': psutil.cpu_count(),
                'total_memory_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024,
                'available_memory_gb': psutil.virtual_memory().available / 1024 / 1024 / 1024,
                'disk_usage_percent': psutil.disk_usage('/').percent if hasattr(psutil, 'disk_usage') else 0
            }
        except Exception as e:
            logger.warning(f"Failed to get system info: {e}")
            return {
                'cpu_count': 1,
                'total_memory_gb': 0,
                'available_memory_gb': 0,
                'disk_usage_percent': 0,
                'error': str(e)
            }

