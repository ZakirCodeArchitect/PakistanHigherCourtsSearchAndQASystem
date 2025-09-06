"""
Tests for search benchmarking models
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from search_benchmarking.models import (
    BenchmarkQuerySet, BenchmarkQuery, BenchmarkExecution,
    BenchmarkResult, BenchmarkComparison, BenchmarkConfiguration
)


class BenchmarkQuerySetModelTest(TestCase):
    """Test cases for BenchmarkQuerySet model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_query_set(self):
        """Test creating a benchmark query set"""
        query_set = BenchmarkQuerySet.objects.create(
            name='Test Query Set',
            description='Test description',
            category='legal_citations',
            expected_results_count=10,
            timeout_seconds=30,
            created_by=self.user
        )
        
        self.assertEqual(query_set.name, 'Test Query Set')
        self.assertEqual(query_set.category, 'legal_citations')
        self.assertEqual(query_set.is_active, True)
        self.assertEqual(query_set.version, '1.0')
    
    def test_query_set_str_representation(self):
        """Test string representation of query set"""
        query_set = BenchmarkQuerySet.objects.create(
            name='Test Query Set',
            category='semantic_queries'
        )
        
        expected = 'Test Query Set (semantic_queries)'
        self.assertEqual(str(query_set), expected)
    
    def test_query_set_validation(self):
        """Test query set validation"""
        # Test required fields
        with self.assertRaises(ValidationError):
            query_set = BenchmarkQuerySet()
            query_set.full_clean()
    
    def test_query_set_defaults(self):
        """Test query set default values"""
        query_set = BenchmarkQuerySet.objects.create(
            name='Test Query Set',
            category='legal_citations'
        )
        
        self.assertTrue(query_set.is_active)
        self.assertEqual(query_set.version, '1.0')
        self.assertEqual(query_set.expected_results_count, 10)
        self.assertEqual(query_set.timeout_seconds, 30)


class BenchmarkQueryModelTest(TestCase):
    """Test cases for BenchmarkQuery model"""
    
    def setUp(self):
        self.query_set = BenchmarkQuerySet.objects.create(
            name='Test Query Set',
            category='legal_citations'
        )
    
    def test_create_query(self):
        """Test creating a benchmark query"""
        query = BenchmarkQuery.objects.create(
            query_set=self.query_set,
            query_text='PPC 302',
            query_type='exact_match',
            expected_results=[
                {'case_id': 1, 'relevance': 1.0},
                {'case_id': 2, 'relevance': 0.9}
            ],
            difficulty_level=3,
            legal_domain='criminal'
        )
        
        self.assertEqual(query.query_text, 'PPC 302')
        self.assertEqual(query.query_type, 'exact_match')
        self.assertEqual(len(query.expected_results), 2)
        self.assertEqual(query.difficulty_level, 3)
        self.assertEqual(query.legal_domain, 'criminal')
        self.assertTrue(query.is_active)
    
    def test_query_str_representation(self):
        """Test string representation of query"""
        query = BenchmarkQuery.objects.create(
            query_set=self.query_set,
            query_text='Very long query text that should be truncated in string representation',
            query_type='semantic'
        )
        
        expected = 'Very long query text that should be truncate... (semantic)'
        self.assertEqual(str(query), expected)
    
    def test_query_defaults(self):
        """Test query default values"""
        query = BenchmarkQuery.objects.create(
            query_set=self.query_set,
            query_text='Test query'
        )
        
        self.assertEqual(query.query_type, 'hybrid')
        self.assertEqual(query.difficulty_level, 3)
        self.assertEqual(query.expected_latency_ms, 1000)
        self.assertEqual(query.min_relevance_score, 0.7)
        self.assertTrue(query.is_active)
    
    def test_query_validation(self):
        """Test query validation"""
        # Test required fields
        with self.assertRaises(ValidationError):
            query = BenchmarkQuery()
            query.full_clean()


class BenchmarkExecutionModelTest(TestCase):
    """Test cases for BenchmarkExecution model"""
    
    def setUp(self):
        self.query_set = BenchmarkQuerySet.objects.create(
            name='Test Query Set',
            category='legal_citations'
        )
    
    def test_create_execution(self):
        """Test creating a benchmark execution"""
        execution = BenchmarkExecution.objects.create(
            query_set=self.query_set,
            execution_name='Test Execution',
            search_mode='hybrid',
            ranking_algorithm='fast_ranking',
            total_queries=10,
            successful_queries=8,
            failed_queries=2
        )
        
        self.assertEqual(execution.execution_name, 'Test Execution')
        self.assertEqual(execution.search_mode, 'hybrid')
        self.assertEqual(execution.ranking_algorithm, 'fast_ranking')
        self.assertEqual(execution.status, 'pending')
        self.assertEqual(execution.total_queries, 10)
        self.assertEqual(execution.successful_queries, 8)
        self.assertEqual(execution.failed_queries, 2)
    
    def test_execution_str_representation(self):
        """Test string representation of execution"""
        execution = BenchmarkExecution.objects.create(
            query_set=self.query_set,
            execution_name='Test Execution',
            status='completed'
        )
        
        expected = 'Test Execution (completed)'
        self.assertEqual(str(execution), expected)
    
    def test_execution_success_rate(self):
        """Test execution success rate calculation"""
        execution = BenchmarkExecution.objects.create(
            query_set=self.query_set,
            execution_name='Test Execution',
            total_queries=10,
            successful_queries=8,
            failed_queries=2
        )
        
        self.assertEqual(execution.success_rate, 80.0)
        
        # Test with zero total queries
        execution.total_queries = 0
        self.assertEqual(execution.success_rate, 0.0)
    
    def test_execution_duration(self):
        """Test execution duration calculation"""
        from datetime import datetime, timedelta
        from django.utils import timezone
        
        start_time = timezone.now()
        end_time = start_time + timedelta(minutes=5)
        
        execution = BenchmarkExecution.objects.create(
            query_set=self.query_set,
            execution_name='Test Execution',
            started_at=start_time,
            completed_at=end_time
        )
        
        self.assertEqual(execution.duration, 300.0)  # 5 minutes in seconds
        
        # Test with no completed_at
        execution.completed_at = None
        self.assertIsNone(execution.duration)


class BenchmarkResultModelTest(TestCase):
    """Test cases for BenchmarkResult model"""
    
    def setUp(self):
        self.query_set = BenchmarkQuerySet.objects.create(
            name='Test Query Set',
            category='legal_citations'
        )
        self.query = BenchmarkQuery.objects.create(
            query_set=self.query_set,
            query_text='Test query'
        )
        self.execution = BenchmarkExecution.objects.create(
            query_set=self.query_set,
            execution_name='Test Execution'
        )
    
    def test_create_result(self):
        """Test creating a benchmark result"""
        result = BenchmarkResult.objects.create(
            execution=self.execution,
            query=self.query,
            query_text='Test query',
            search_mode='hybrid',
            ranking_algorithm='fast_ranking',
            returned_results=[
                {'case_id': 1, 'score': 0.9},
                {'case_id': 2, 'score': 0.8}
            ],
            total_results_found=2,
            execution_time_ms=500.0,
            precision_at_10=0.8,
            recall_at_10=0.7,
            mrr=0.75,
            ndcg_at_10=0.72,
            status='success'
        )
        
        self.assertEqual(result.execution, self.execution)
        self.assertEqual(result.query, self.query)
        self.assertEqual(result.total_results_found, 2)
        self.assertEqual(result.execution_time_ms, 500.0)
        self.assertEqual(result.status, 'success')
    
    def test_result_str_representation(self):
        """Test string representation of result"""
        result = BenchmarkResult.objects.create(
            execution=self.execution,
            query=self.query,
            query_text='Very long query that should be truncated',
            status='success'
        )
        
        expected = 'Very long query that should be trun... (success)'
        self.assertEqual(str(result), expected)


class BenchmarkConfigurationModelTest(TestCase):
    """Test cases for BenchmarkConfiguration model"""
    
    def test_create_configuration(self):
        """Test creating a benchmark configuration"""
        config = BenchmarkConfiguration.objects.create(
            name='Test Configuration',
            description='Test configuration description',
            search_mode='hybrid',
            ranking_algorithm='fast_ranking',
            ranking_config={
                'vector_weight': 0.6,
                'keyword_weight': 0.4,
                'exact_match_boost': 2.0
            },
            timeout_seconds=30,
            max_results_per_query=100
        )
        
        self.assertEqual(config.name, 'Test Configuration')
        self.assertEqual(config.search_mode, 'hybrid')
        self.assertEqual(config.ranking_algorithm, 'fast_ranking')
        self.assertEqual(config.ranking_config['vector_weight'], 0.6)
        self.assertTrue(config.is_active)
        self.assertFalse(config.is_default)
    
    def test_configuration_str_representation(self):
        """Test string representation of configuration"""
        config = BenchmarkConfiguration.objects.create(
            name='Test Configuration',
            search_mode='hybrid',
            ranking_algorithm='fast_ranking'
        )
        
        expected = 'Test Configuration (hybrid/fast_ranking)'
        self.assertEqual(str(config), expected)
    
    def test_configuration_defaults(self):
        """Test configuration default values"""
        config = BenchmarkConfiguration.objects.create(
            name='Test Configuration',
            search_mode='hybrid',
            ranking_algorithm='fast_ranking'
        )
        
        self.assertTrue(config.is_active)
        self.assertFalse(config.is_default)
        self.assertEqual(config.timeout_seconds, 30)
        self.assertEqual(config.max_results_per_query, 100)
        self.assertTrue(config.enable_performance_monitoring)
        self.assertTrue(config.enable_quality_metrics)
        self.assertFalse(config.enable_system_metrics)

