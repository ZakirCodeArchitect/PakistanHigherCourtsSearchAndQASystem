"""
Django management command to create sample benchmark data
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
import json
from datetime import datetime

from search_benchmarking.models import (
    BenchmarkQuerySet, BenchmarkQuery, BenchmarkConfiguration
)


class Command(BaseCommand):
    help = 'Create sample benchmark data for testing and demonstration'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset existing data before creating new sample data'
        )
        parser.add_argument(
            '--query-sets-only',
            action='store_true',
            help='Create only query sets and queries (no configurations)'
        )
    
    def handle(self, *args, **options):
        try:
            if options['reset']:
                self.reset_data()
            
            self.create_sample_query_sets()
            
            if not options['query_sets_only']:
                self.create_sample_configurations()
            
            self.stdout.write(self.style.SUCCESS('Sample benchmark data created successfully!'))
            
        except Exception as e:
            raise CommandError(f'Error creating sample data: {str(e)}')
    
    def reset_data(self):
        """Reset existing benchmark data"""
        self.stdout.write('Resetting existing benchmark data...')
        
        # Delete in reverse order to avoid foreign key constraints
        BenchmarkQuery.objects.all().delete()
        BenchmarkQuerySet.objects.all().delete()
        BenchmarkConfiguration.objects.all().delete()
        
        self.stdout.write(self.style.WARNING('Existing benchmark data reset'))
    
    def create_sample_query_sets(self):
        """Create sample benchmark query sets"""
        self.stdout.write('Creating sample query sets...')
        
        # Legal Citations Query Set
        legal_citations_set = BenchmarkQuerySet.objects.create(
            name='Legal Citations Benchmark',
            description='Benchmark queries for legal citations and case references',
            category='legal_citations',
            expected_results_count=5,
            timeout_seconds=30,
            version='1.0'
        )
        
        legal_citation_queries = [
            {
                'query_text': 'PPC 302',
                'query_type': 'exact_match',
                'expected_results': [
                    {'case_id': 1, 'relevance': 1.0},
                    {'case_id': 15, 'relevance': 1.0},
                    {'case_id': 23, 'relevance': 0.9}
                ],
                'difficulty_level': 2,
                'legal_domain': 'criminal'
            },
            {
                'query_text': 'CrPC 497',
                'query_type': 'exact_match',
                'expected_results': [
                    {'case_id': 5, 'relevance': 1.0},
                    {'case_id': 12, 'relevance': 0.8}
                ],
                'difficulty_level': 2,
                'legal_domain': 'criminal'
            },
            {
                'query_text': 'CPC 151',
                'query_type': 'exact_match',
                'expected_results': [
                    {'case_id': 8, 'relevance': 1.0},
                    {'case_id': 19, 'relevance': 0.9},
                    {'case_id': 31, 'relevance': 0.7}
                ],
                'difficulty_level': 3,
                'legal_domain': 'civil'
            },
            {
                'query_text': 'Case No. 123/2024',
                'query_type': 'exact_match',
                'expected_results': [
                    {'case_id': 123, 'relevance': 1.0}
                ],
                'difficulty_level': 1,
                'legal_domain': 'general'
            }
        ]
        
        for query_data in legal_citation_queries:
            BenchmarkQuery.objects.create(
                query_set=legal_citations_set,
                query_text=query_data['query_text'],
                query_type=query_data['query_type'],
                expected_results=query_data['expected_results'],
                difficulty_level=query_data['difficulty_level'],
                legal_domain=query_data['legal_domain'],
                expected_latency_ms=500,
                min_relevance_score=0.8
            )
        
        # Semantic Queries Query Set
        semantic_set = BenchmarkQuerySet.objects.create(
            name='Semantic Search Benchmark',
            description='Benchmark queries for semantic similarity search',
            category='semantic_queries',
            expected_results_count=10,
            timeout_seconds=45,
            version='1.0'
        )
        
        semantic_queries = [
            {
                'query_text': 'murder case',
                'query_type': 'semantic',
                'expected_results': [
                    {'case_id': 1, 'relevance': 1.0},
                    {'case_id': 15, 'relevance': 0.9},
                    {'case_id': 23, 'relevance': 0.8},
                    {'case_id': 45, 'relevance': 0.7}
                ],
                'difficulty_level': 3,
                'legal_domain': 'criminal'
            },
            {
                'query_text': 'property dispute',
                'query_type': 'semantic',
                'expected_results': [
                    {'case_id': 8, 'relevance': 1.0},
                    {'case_id': 19, 'relevance': 0.9},
                    {'case_id': 31, 'relevance': 0.8},
                    {'case_id': 52, 'relevance': 0.7}
                ],
                'difficulty_level': 4,
                'legal_domain': 'civil'
            },
            {
                'query_text': 'constitutional rights violation',
                'query_type': 'semantic',
                'expected_results': [
                    {'case_id': 67, 'relevance': 1.0},
                    {'case_id': 89, 'relevance': 0.9},
                    {'case_id': 101, 'relevance': 0.8}
                ],
                'difficulty_level': 5,
                'legal_domain': 'constitutional'
            },
            {
                'query_text': 'contract breach',
                'query_type': 'semantic',
                'expected_results': [
                    {'case_id': 25, 'relevance': 1.0},
                    {'case_id': 38, 'relevance': 0.9},
                    {'case_id': 44, 'relevance': 0.8},
                    {'case_id': 56, 'relevance': 0.7}
                ],
                'difficulty_level': 4,
                'legal_domain': 'civil'
            }
        ]
        
        for query_data in semantic_queries:
            BenchmarkQuery.objects.create(
                query_set=semantic_set,
                query_text=query_data['query_text'],
                query_type=query_data['query_type'],
                expected_results=query_data['expected_results'],
                difficulty_level=query_data['difficulty_level'],
                legal_domain=query_data['legal_domain'],
                expected_latency_ms=1000,
                min_relevance_score=0.7
            )
        
        # Complex Queries Query Set
        complex_set = BenchmarkQuerySet.objects.create(
            name='Complex Queries Benchmark',
            description='Benchmark queries for complex multi-faceted searches',
            category='complex_queries',
            expected_results_count=15,
            timeout_seconds=60,
            version='1.0'
        )
        
        complex_queries = [
            {
                'query_text': 'murder case in Supreme Court 2023',
                'query_type': 'complex',
                'expected_results': [
                    {'case_id': 15, 'relevance': 1.0},
                    {'case_id': 23, 'relevance': 0.9},
                    {'case_id': 45, 'relevance': 0.8}
                ],
                'difficulty_level': 5,
                'legal_domain': 'criminal'
            },
            {
                'query_text': 'property dispute between family members',
                'query_type': 'complex',
                'expected_results': [
                    {'case_id': 19, 'relevance': 1.0},
                    {'case_id': 31, 'relevance': 0.9},
                    {'case_id': 52, 'relevance': 0.8}
                ],
                'difficulty_level': 4,
                'legal_domain': 'civil'
            },
            {
                'query_text': 'constitutional petition against government',
                'query_type': 'complex',
                'expected_results': [
                    {'case_id': 67, 'relevance': 1.0},
                    {'case_id': 89, 'relevance': 0.9},
                    {'case_id': 101, 'relevance': 0.8}
                ],
                'difficulty_level': 5,
                'legal_domain': 'constitutional'
            }
        ]
        
        for query_data in complex_queries:
            BenchmarkQuery.objects.create(
                query_set=complex_set,
                query_text=query_data['query_text'],
                query_type=query_data['query_type'],
                expected_results=query_data['expected_results'],
                difficulty_level=query_data['difficulty_level'],
                legal_domain=query_data['legal_domain'],
                expected_latency_ms=2000,
                min_relevance_score=0.8
            )
        
        # Edge Cases Query Set
        edge_cases_set = BenchmarkQuerySet.objects.create(
            name='Edge Cases Benchmark',
            description='Benchmark queries for edge cases and error conditions',
            category='edge_cases',
            expected_results_count=5,
            timeout_seconds=30,
            version='1.0'
        )
        
        edge_case_queries = [
            {
                'query_text': 'a',
                'query_type': 'semantic',
                'expected_results': [],
                'difficulty_level': 5,
                'legal_domain': 'general'
            },
            {
                'query_text': 'very long query with many terms that should test the system limits and performance under extreme conditions',
                'query_type': 'semantic',
                'expected_results': [
                    {'case_id': 1, 'relevance': 0.5}
                ],
                'difficulty_level': 5,
                'legal_domain': 'general'
            },
            {
                'query_text': 'nonexistent_case_number_999999',
                'query_type': 'exact_match',
                'expected_results': [],
                'difficulty_level': 1,
                'legal_domain': 'general'
            }
        ]
        
        for query_data in edge_case_queries:
            BenchmarkQuery.objects.create(
                query_set=edge_cases_set,
                query_text=query_data['query_text'],
                query_type=query_data['query_type'],
                expected_results=query_data['expected_results'],
                difficulty_level=query_data['difficulty_level'],
                legal_domain=query_data['legal_domain'],
                expected_latency_ms=1000,
                min_relevance_score=0.5
            )
        
        self.stdout.write(f'Created {BenchmarkQuerySet.objects.count()} query sets with {BenchmarkQuery.objects.count()} total queries')
    
    def create_sample_configurations(self):
        """Create sample benchmark configurations"""
        self.stdout.write('Creating sample configurations...')
        
        # Get query sets
        query_sets = BenchmarkQuerySet.objects.all()
        
        # Fast Hybrid Configuration
        fast_hybrid_config = BenchmarkConfiguration.objects.create(
            name='Fast Hybrid Configuration',
            description='Fast hybrid search with basic ranking for performance testing',
            search_mode='hybrid',
            ranking_algorithm='fast_ranking',
            ranking_config={
                'vector_weight': 0.6,
                'keyword_weight': 0.4,
                'exact_match_boost': 2.0,
                'max_boost': 3.0
            },
            timeout_seconds=30,
            max_results_per_query=50,
            enable_performance_monitoring=True,
            enable_quality_metrics=True,
            enable_system_metrics=False,
            is_default=True
        )
        fast_hybrid_config.query_sets.set(query_sets)
        
        # Advanced Hybrid Configuration
        advanced_hybrid_config = BenchmarkConfiguration.objects.create(
            name='Advanced Hybrid Configuration',
            description='Advanced hybrid search with sophisticated ranking for quality testing',
            search_mode='hybrid',
            ranking_algorithm='advanced_ranking',
            ranking_config={
                'semantic_weight': 0.6,
                'lexical_weight': 0.4,
                'exact_match_boost': 3.0,
                'citation_boost': 2.0,
                'legal_term_boost': 1.5,
                'recency_decay_factor': 0.1,
                'diversity_threshold': 0.7,
                'mmr_lambda': 0.5
            },
            timeout_seconds=45,
            max_results_per_query=100,
            enable_performance_monitoring=True,
            enable_quality_metrics=True,
            enable_system_metrics=True
        )
        advanced_hybrid_config.query_sets.set(query_sets)
        
        # Semantic Only Configuration
        semantic_config = BenchmarkConfiguration.objects.create(
            name='Semantic Only Configuration',
            description='Semantic search only for similarity testing',
            search_mode='semantic',
            ranking_algorithm='fast_ranking',
            ranking_config={
                'vector_weight': 1.0,
                'keyword_weight': 0.0,
                'exact_match_boost': 1.5,
                'max_boost': 2.0
            },
            timeout_seconds=40,
            max_results_per_query=75,
            enable_performance_monitoring=True,
            enable_quality_metrics=True,
            enable_system_metrics=False
        )
        semantic_config.query_sets.set(query_sets.filter(category='semantic_queries'))
        
        # Lexical Only Configuration
        lexical_config = BenchmarkConfiguration.objects.create(
            name='Lexical Only Configuration',
            description='Lexical search only for exact matching testing',
            search_mode='lexical',
            ranking_algorithm='fast_ranking',
            ranking_config={
                'vector_weight': 0.0,
                'keyword_weight': 1.0,
                'exact_match_boost': 3.0,
                'max_boost': 5.0
            },
            timeout_seconds=25,
            max_results_per_query=50,
            enable_performance_monitoring=True,
            enable_quality_metrics=True,
            enable_system_metrics=False
        )
        lexical_config.query_sets.set(query_sets.filter(category='legal_citations'))
        
        self.stdout.write(f'Created {BenchmarkConfiguration.objects.count()} configurations')

