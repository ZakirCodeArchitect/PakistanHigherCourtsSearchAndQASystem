"""
Tests for search benchmarking services
"""

from django.test import TestCase
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from search_benchmarking.models import (
    BenchmarkQuerySet, BenchmarkQuery, BenchmarkExecution, BenchmarkResult
)
from search_benchmarking.services.benchmark_collector import BenchmarkCollector
from search_benchmarking.services.relevance_evaluator import RelevanceEvaluator
from search_benchmarking.services.performance_analyzer import PerformanceAnalyzer


class BenchmarkCollectorServiceTest(TestCase):
    """Test cases for BenchmarkCollector service"""
    
    def setUp(self):
        self.query_set = BenchmarkQuerySet.objects.create(
            name='Test Query Set',
            category='legal_citations'
        )
        self.query = BenchmarkQuery.objects.create(
            query_set=self.query_set,
            query_text='PPC 302',
            query_type='exact_match',
            expected_results=[
                {'case_id': 1, 'relevance': 1.0},
                {'case_id': 2, 'relevance': 0.9}
            ]
        )
    
    @patch('search_benchmarking.services.benchmark_collector.QueryNormalizationService')
    @patch('search_benchmarking.services.benchmark_collector.HybridIndexingService')
    @patch('search_benchmarking.services.benchmark_collector.FastRankingService')
    def test_collector_initialization(self, mock_fast_ranking, mock_hybrid_service, mock_query_normalizer):
        """Test benchmark collector initialization"""
        collector = BenchmarkCollector()
        
        # Verify services are initialized
        mock_query_normalizer.assert_called_once()
        mock_hybrid_service.assert_called_once_with(use_pinecone=True)
        mock_fast_ranking.assert_called_once()
    
    @patch('search_benchmarking.services.benchmark_collector.QueryNormalizationService')
    @patch('search_benchmarking.services.benchmark_collector.HybridIndexingService')
    @patch('search_benchmarking.services.benchmark_collector.FastRankingService')
    def test_collect_benchmark_data(self, mock_fast_ranking, mock_hybrid_service, mock_query_normalizer):
        """Test collecting benchmark data"""
        # Mock the services
        mock_normalizer = Mock()
        mock_normalizer.normalize_query.return_value = {'normalized_query': 'ppc 302'}
        mock_query_normalizer.return_value = mock_normalizer
        
        mock_hybrid = Mock()
        mock_hybrid.keyword_service = Mock()
        mock_hybrid.keyword_service.search.return_value = [
            {'case_id': 1, 'rank': 0.9, 'case_number': 'Test Case 1'},
            {'case_id': 2, 'rank': 0.8, 'case_number': 'Test Case 2'}
        ]
        mock_hybrid_service.return_value = mock_hybrid
        
        mock_ranking = Mock()
        mock_ranking.rank_results.return_value = [
            {'case_id': 1, 'final_score': 0.9, 'case_number': 'Test Case 1'},
            {'case_id': 2, 'final_score': 0.8, 'case_number': 'Test Case 2'}
        ]
        mock_fast_ranking.return_value = mock_ranking
        
        # Create collector and run benchmark
        collector = BenchmarkCollector()
        
        with patch.object(collector, '_stop_performance_monitoring'):
            execution = collector.collect_benchmark_data(self.query_set.id)
        
        # Verify execution was created
        self.assertIsInstance(execution, BenchmarkExecution)
        self.assertEqual(execution.query_set, self.query_set)
        self.assertEqual(execution.status, 'completed')
        self.assertEqual(execution.total_queries, 1)
        self.assertEqual(execution.successful_queries, 1)
        
        # Verify result was created
        result = BenchmarkResult.objects.filter(execution=execution).first()
        self.assertIsNotNone(result)
        self.assertEqual(result.query, self.query)
        self.assertEqual(result.status, 'success')
    
    @patch('search_benchmarking.services.benchmark_collector.QueryNormalizationService')
    @patch('search_benchmarking.services.benchmark_collector.HybridIndexingService')
    @patch('search_benchmarking.services.benchmark_collector.FastRankingService')
    def test_execute_single_query_error_handling(self, mock_fast_ranking, mock_hybrid_service, mock_query_normalizer):
        """Test error handling in single query execution"""
        # Mock services to raise an error
        mock_normalizer = Mock()
        mock_normalizer.normalize_query.side_effect = Exception("Query normalization failed")
        mock_query_normalizer.return_value = mock_normalizer
        
        mock_hybrid = Mock()
        mock_hybrid_service.return_value = mock_hybrid
        
        mock_ranking = Mock()
        mock_fast_ranking.return_value = mock_ranking
        
        # Create execution
        execution = BenchmarkExecution.objects.create(
            query_set=self.query_set,
            execution_name='Test Execution',
            search_mode='lexical',
            ranking_algorithm='fast_ranking'
        )
        
        # Create collector and execute query
        collector = BenchmarkCollector()
        
        with patch.object(collector, '_stop_performance_monitoring'):
            result = collector._execute_single_query(self.query, execution, None)
        
        # Verify error result was created
        self.assertEqual(result.status, 'error')
        self.assertIn('Query normalization failed', result.error_message)


class RelevanceEvaluatorServiceTest(TestCase):
    """Test cases for RelevanceEvaluator service"""
    
    def setUp(self):
        self.query_set = BenchmarkQuerySet.objects.create(
            name='Test Query Set',
            category='legal_citations'
        )
        self.query = BenchmarkQuery.objects.create(
            query_set=self.query_set,
            query_text='PPC 302',
            query_type='exact_match',
            expected_results=[
                {'case_id': 1, 'relevance': 1.0},
                {'case_id': 2, 'relevance': 0.9},
                {'case_id': 3, 'relevance': 0.8}
            ]
        )
    
    def test_evaluate_query_relevance(self):
        """Test evaluating query relevance"""
        evaluator = RelevanceEvaluator()
        
        # Mock returned results
        returned_results = [
            {'case_id': 1, 'score': 0.95},
            {'case_id': 2, 'score': 0.85},
            {'case_id': 4, 'score': 0.75},  # Not in expected results
            {'case_id': 5, 'score': 0.65}   # Not in expected results
        ]
        
        metrics = evaluator.evaluate_query_relevance(self.query, returned_results)
        
        # Verify metrics
        self.assertIn('precision_at_10', metrics)
        self.assertIn('recall_at_10', metrics)
        self.assertIn('mrr', metrics)
        self.assertIn('ndcg_at_10', metrics)
        
        # Precision@10 should be 2/4 = 0.5 (2 relevant out of 4 returned)
        self.assertEqual(metrics['precision_at_10'], 0.5)
        
        # Recall@10 should be 2/3 = 0.667 (2 found out of 3 expected)
        self.assertAlmostEqual(metrics['recall_at_10'], 2/3, places=2)
        
        # MRR should be 1 (first result is relevant)
        self.assertEqual(metrics['mrr'], 1.0)
    
    def test_evaluate_query_relevance_empty_expected(self):
        """Test evaluating query relevance with no expected results"""
        evaluator = RelevanceEvaluator()
        
        # Query with no expected results
        empty_query = BenchmarkQuery.objects.create(
            query_set=self.query_set,
            query_text='Empty query',
            expected_results=[]
        )
        
        returned_results = [
            {'case_id': 1, 'score': 0.95},
            {'case_id': 2, 'score': 0.85}
        ]
        
        metrics = evaluator.evaluate_query_relevance(empty_query, returned_results)
        
        # All metrics should be 0 for empty expected results
        self.assertEqual(metrics['precision_at_10'], 0.0)
        self.assertEqual(metrics['recall_at_10'], 0.0)
        self.assertEqual(metrics['mrr'], 0.0)
        self.assertEqual(metrics['ndcg_at_10'], 0.0)
    
    def test_evaluate_execution_quality(self):
        """Test evaluating execution quality"""
        evaluator = RelevanceEvaluator()
        
        # Create mock results
        execution = BenchmarkExecution.objects.create(
            query_set=self.query_set,
            execution_name='Test Execution'
        )
        
        result1 = BenchmarkResult.objects.create(
            execution=execution,
            query=self.query,
            query_text='Test query 1',
            search_mode='hybrid',
            ranking_algorithm='fast_ranking',
            precision_at_10=0.8,
            recall_at_10=0.7,
            mrr=0.75,
            ndcg_at_10=0.72,
            ranking_quality_score=0.8,
            execution_time_ms=500.0,
            status='success'
        )
        
        result2 = BenchmarkResult.objects.create(
            execution=execution,
            query=self.query,
            query_text='Test query 2',
            search_mode='hybrid',
            ranking_algorithm='fast_ranking',
            precision_at_10=0.6,
            recall_at_10=0.5,
            mrr=0.65,
            ndcg_at_10=0.62,
            ranking_quality_score=0.6,
            execution_time_ms=750.0,
            status='success'
        )
        
        results = [result1, result2]
        quality_metrics = evaluator.evaluate_execution_quality(results)
        
        # Verify aggregate metrics
        self.assertIn('precision_at_10_mean', quality_metrics)
        self.assertIn('recall_at_10_mean', quality_metrics)
        self.assertIn('mrr_mean', quality_metrics)
        self.assertIn('ndcg_at_10_mean', quality_metrics)
        self.assertIn('overall_quality_score', quality_metrics)
        
        # Average precision should be (0.8 + 0.6) / 2 = 0.7
        self.assertEqual(quality_metrics['precision_at_10_mean'], 0.7)
        
        # Average recall should be (0.7 + 0.5) / 2 = 0.6
        self.assertEqual(quality_metrics['recall_at_10_mean'], 0.6)
        
        # Overall quality score should be (0.8 + 0.6) / 2 = 0.7
        self.assertEqual(quality_metrics['overall_quality_score'], 0.7)


class PerformanceAnalyzerServiceTest(TestCase):
    """Test cases for PerformanceAnalyzer service"""
    
    def setUp(self):
        self.query_set = BenchmarkQuerySet.objects.create(
            name='Test Query Set',
            category='legal_citations'
        )
        self.execution = BenchmarkExecution.objects.create(
            query_set=self.query_set,
            execution_name='Test Execution',
            search_mode='hybrid',
            ranking_algorithm='fast_ranking'
        )
    
    def test_analyze_execution_performance(self):
        """Test analyzing execution performance"""
        analyzer = PerformanceAnalyzer()
        
        # Create mock results with different performance characteristics
        result1 = BenchmarkResult.objects.create(
            execution=self.execution,
            query=BenchmarkQuery.objects.create(
                query_set=self.query_set,
                query_text='Fast query',
                expected_results=[]
            ),
            query_text='Fast query',
            search_mode='hybrid',
            ranking_algorithm='fast_ranking',
            execution_time_ms=300.0,  # Fast
            memory_usage_mb=50.0,     # Low memory
            cpu_usage_percent=10.0,   # Low CPU
            status='success'
        )
        
        result2 = BenchmarkResult.objects.create(
            execution=self.execution,
            query=BenchmarkQuery.objects.create(
                query_set=self.query_set,
                query_text='Slow query',
                expected_results=[]
            ),
            query_text='Slow query',
            search_mode='hybrid',
            ranking_algorithm='fast_ranking',
            execution_time_ms=1500.0,  # Slow
            memory_usage_mb=200.0,     # High memory
            cpu_usage_percent=50.0,    # High CPU
            status='success'
        )
        
        results = [result1, result2]
        performance_analysis = analyzer.analyze_execution_performance(self.execution)
        
        # Verify analysis structure
        self.assertIn('execution_summary', performance_analysis)
        self.assertIn('latency_analysis', performance_analysis)
        self.assertIn('memory_analysis', performance_analysis)
        self.assertIn('cpu_analysis', performance_analysis)
        self.assertIn('throughput_analysis', performance_analysis)
        self.assertIn('bottleneck_analysis', performance_analysis)
        self.assertIn('recommendations', performance_analysis)
        
        # Verify latency analysis
        latency_analysis = performance_analysis['latency_analysis']
        self.assertIn('count', latency_analysis)
        self.assertIn('mean_ms', latency_analysis)
        self.assertIn('min_ms', latency_analysis)
        self.assertIn('max_ms', latency_analysis)
        
        # Average latency should be (300 + 1500) / 2 = 900
        self.assertEqual(latency_analysis['mean_ms'], 900.0)
        self.assertEqual(latency_analysis['min_ms'], 300.0)
        self.assertEqual(latency_analysis['max_ms'], 1500.0)
    
    def test_analyze_execution_performance_empty_results(self):
        """Test analyzing execution performance with no results"""
        analyzer = PerformanceAnalyzer()
        
        performance_analysis = analyzer.analyze_execution_performance(self.execution)
        
        # Should return empty analysis structure
        self.assertIn('execution_summary', performance_analysis)
        self.assertIn('latency_analysis', performance_analysis)
        self.assertIn('recommendations', performance_analysis)
        
        # Latency analysis should have error
        self.assertIn('error', performance_analysis['latency_analysis'])
    
    def test_categorize_latency_performance(self):
        """Test categorizing latency performance"""
        analyzer = PerformanceAnalyzer()
        
        # Test with mixed latencies
        latencies = [300.0, 800.0, 1200.0, 2500.0]  # excellent, good, acceptable, poor
        
        categories = analyzer._categorize_latency_performance(latencies)
        
        self.assertEqual(categories['excellent'], 1)  # 300ms
        self.assertEqual(categories['good'], 1)       # 800ms
        self.assertEqual(categories['acceptable'], 1) # 1200ms
        self.assertEqual(categories['poor'], 1)       # 2500ms
        self.assertEqual(categories['total'], 4)
    
    def test_percentile_calculation(self):
        """Test percentile calculation"""
        analyzer = PerformanceAnalyzer()
        
        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        
        self.assertEqual(analyzer._percentile(data, 50), 5)  # Median
        self.assertEqual(analyzer._percentile(data, 90), 9)  # 90th percentile
        self.assertEqual(analyzer._percentile(data, 95), 10) # 95th percentile
        self.assertEqual(analyzer._percentile(data, 99), 10) # 99th percentile
    
    def test_percentile_empty_data(self):
        """Test percentile calculation with empty data"""
        analyzer = PerformanceAnalyzer()
        
        self.assertEqual(analyzer._percentile([], 50), 0.0)

