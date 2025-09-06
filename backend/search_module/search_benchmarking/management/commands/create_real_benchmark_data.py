"""
Django management command to create benchmark data based on real case data
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
import random
import logging

from search_benchmarking.models import (
    BenchmarkQuerySet, BenchmarkQuery, BenchmarkExecution, 
    BenchmarkResult, BenchmarkComparison
)
from apps.cases.models import Case, Court, JudgementData
from search_indexing.models import SearchMetadata

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create benchmark data based on real case data from the system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing benchmark data before creating new data',
        )
        parser.add_argument(
            '--query-count',
            type=int,
            default=20,
            help='Number of queries to create per query set (default: 20)',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Creating benchmark data based on real case data...')
        )

        self.options = options  # Store options for use in methods

        if options['clear_existing']:
            self.clear_existing_data()

        # Create real benchmark query sets
        self.create_legal_citation_queries()
        self.create_case_title_queries()
        self.create_semantic_queries()
        self.create_complex_queries()
        self.create_edge_case_queries()

        self.stdout.write(
            self.style.SUCCESS('Successfully created real benchmark data!')
        )

    def clear_existing_data(self):
        """Clear existing benchmark data"""
        self.stdout.write('Clearing existing benchmark data...')
        
        BenchmarkResult.objects.all().delete()
        BenchmarkExecution.objects.all().delete()
        BenchmarkQuery.objects.all().delete()
        BenchmarkQuerySet.objects.all().delete()
        BenchmarkComparison.objects.all().delete()
        
        self.stdout.write(
            self.style.WARNING('Cleared all existing benchmark data')
        )

    def create_legal_citation_queries(self):
        """Create queries based on actual case numbers and citations"""
        self.stdout.write('Creating legal citation queries...')
        
        query_set, created = BenchmarkQuerySet.objects.get_or_create(
            name="Real Legal Citations",
            description="Benchmark queries based on actual case numbers and legal citations from Islamabad High Court",
            category="legal_citations",
            defaults={
                'is_active': True,
                'created_by': None,  # No user specified
            }
        )
        
        if not created:
            # Clear existing queries for this set
            query_set.queries.all().delete()
        
        # Get actual case numbers for citation queries
        cases = Case.objects.filter(
            case_number__isnull=False,
            case_number__gt=''
        ).exclude(case_number='.').order_by('?')[:self.options['query_count']]
        
        for case in cases:
            # Create citation-based queries
            queries = [
                case.case_number,  # Full case number
                case.case_number.split()[0] if case.case_number else None,  # First part
                f"{case.case_number} {case.case_title[:50]}" if case.case_title else case.case_number,  # Case number + title
            ]
            
            for i, query_text in enumerate(queries):
                if query_text and len(query_text.strip()) > 3:
                    BenchmarkQuery.objects.create(
                        query_set=query_set,
                        query_text=query_text.strip(),
                        query_type="exact_match",
                        expected_results=[{"case_id": case.id, "relevance_score": 4}],
                        difficulty_level=2,
                        legal_domain="general",
                        expected_latency_ms=500,
                        min_relevance_score=0.8
                    )

    def create_case_title_queries(self):
        """Create queries based on actual case titles"""
        self.stdout.write('Creating case title queries...')
        
        query_set, created = BenchmarkQuerySet.objects.get_or_create(
            name="Real Case Titles",
            description="Benchmark queries based on actual case titles and parties from Islamabad High Court",
            category="semantic_queries",
            defaults={
                'is_active': True,
                'created_by': None,
            }
        )
        
        if not created:
            query_set.queries.all().delete()
        
        # Get cases with meaningful titles
        cases = Case.objects.filter(
            case_title__isnull=False,
            case_title__gt=''
        ).exclude(case_title='.').exclude(case_title='VS').order_by('?')[:self.options['query_count']]
        
        for case in cases:
            if case.case_title and len(case.case_title.strip()) > 5:
                # Extract meaningful parts of the title
                title_parts = case.case_title.split(' VS ')
                if len(title_parts) >= 2:
                    # Create queries for each party
                    for i, party in enumerate(title_parts[:2]):
                        party_clean = party.strip()
                        if len(party_clean) > 3:
                            BenchmarkQuery.objects.create(
                                query_set=query_set,
                                query_text=party_clean,
                                query_type="semantic",
                                expected_results=[{"case_id": case.id, "relevance_score": 4}],
                                difficulty_level=3,
                                legal_domain="general",
                                expected_latency_ms=800,
                                min_relevance_score=0.7
                            )
                
                # Create full title query
                BenchmarkQuery.objects.create(
                    query_set=query_set,
                    query_text=case.case_title,
                    query_type="semantic",
                    expected_results=[{"case_id": case.id, "relevance_score": 5}],
                    difficulty_level=2,
                    legal_domain="general",
                    expected_latency_ms=600,
                    min_relevance_score=0.9
                )

    def create_semantic_queries(self):
        """Create semantic queries based on case content and context"""
        self.stdout.write('Creating semantic queries...')
        
        query_set, created = BenchmarkQuerySet.objects.get_or_create(
            name="Real Semantic Queries",
            description="Semantic queries based on legal concepts and case context from real data",
            category="semantic_queries",
            defaults={
                'is_active': True,
                'created_by': None,
            }
        )
        
        if not created:
            query_set.queries.all().delete()
        
        # Create semantic queries based on case patterns
        semantic_queries = [
            ("criminal case", "Criminal", [4]),
            ("civil matter", "Civil", [3]),
            ("writ petition", "Writ", [4]),
            ("constitutional petition", "Constitutional", [4]),
            ("bail application", "Bail", [3]),
            ("appeal case", "Appeal", [3]),
            ("review petition", "Review", [3]),
            ("contempt of court", "Contempt", [4]),
            ("land dispute", "Land", [3]),
            ("property case", "Property", [3]),
            ("family matter", "Family", [3]),
            ("commercial dispute", "Commercial", [3]),
            ("tax case", "Tax", [3]),
            ("service matter", "Service", [3]),
            ("contract dispute", "Contract", [3]),
        ]
        
        for query_text, category, scores in semantic_queries:
            # Find cases that might match this semantic query
            matching_cases = Case.objects.filter(
                case_title__icontains=query_text.split()[0]
            ).values_list('id', flat=True)[:3]
            
            expected_results = []
            if matching_cases:
                for case_id in matching_cases:
                    expected_results.append({"case_id": case_id, "relevance_score": scores[0]})
            
            BenchmarkQuery.objects.create(
                query_set=query_set,
                query_text=query_text,
                query_type="semantic",
                expected_results=expected_results,
                difficulty_level=3,
                legal_domain=category.lower(),
                expected_latency_ms=1000,
                min_relevance_score=0.6
            )

    def create_complex_queries(self):
        """Create complex multi-faceted queries"""
        self.stdout.write('Creating complex queries...')
        
        query_set, created = BenchmarkQuerySet.objects.get_or_create(
            name="Real Complex Queries",
            description="Complex multi-faceted queries combining multiple search criteria",
            category="complex_queries",
            defaults={
                'is_active': True,
                'created_by': None,
            }
        )
        
        if not created:
            query_set.queries.all().delete()
        
        # Get cases with multiple data points
        cases_with_details = Case.objects.filter(
            case_title__isnull=False,
            status__isnull=False
        ).exclude(case_title='.').exclude(status='')[:self.options['query_count']]
        
        for case in cases_with_details:
            if case.case_title and case.status:
                # Create complex queries combining title and status
                complex_queries = [
                    f"{case.case_title[:50]} {case.status}",
                    f"{case.status} case {case.case_title[:30]}",
                ]
                
                for i, query_text in enumerate(complex_queries):
                    BenchmarkQuery.objects.create(
                        query_set=query_set,
                        query_text=query_text,
                        query_type="complex",
                        expected_results=[{"case_id": case.id, "relevance_score": 4}],
                        difficulty_level=4,
                        legal_domain="general",
                        expected_latency_ms=1200,
                        min_relevance_score=0.8
                    )

    def create_edge_case_queries(self):
        """Create edge case queries for testing robustness"""
        self.stdout.write('Creating edge case queries...')
        
        query_set, created = BenchmarkQuerySet.objects.get_or_create(
            name="Real Edge Cases",
            description="Edge case queries to test search system robustness with real data patterns",
            category="edge_cases",
            defaults={
                'is_active': True,
                'created_by': None,
            }
        )
        
        if not created:
            query_set.queries.all().delete()
        
        # Create edge case queries
        edge_queries = [
            ("2025", "Year only", [2]),
            ("Islamabad", "Court name only", [2]),
            ("VS", "Separator only", [1]),
            ("Application", "Common word", [2]),
            ("Case", "Very common word", [1]),
            ("No. 1", "Partial case number", [3]),
            ("Criminal", "Case type", [3]),
            ("Writ", "Petition type", [3]),
            ("", "Empty query", [0]),
            ("a", "Single character", [0]),
            ("123456789", "Numbers only", [1]),
            ("!@#$%^&*()", "Special characters", [0]),
        ]
        
        for query_text, description, scores in edge_queries:
            if query_text:  # Skip empty queries
                expected_results = []
                if scores and scores[0] > 0:
                    # For edge cases with potential matches, create minimal expected results
                    expected_results = [{"case_id": 1, "relevance_score": scores[0]}]  # Placeholder
                
                BenchmarkQuery.objects.create(
                    query_set=query_set,
                    query_text=query_text,
                    query_type="complex",
                    expected_results=expected_results,
                    difficulty_level=5,
                    legal_domain="general",
                    expected_latency_ms=2000,
                    min_relevance_score=0.3
                )

    def create_sample_executions(self):
        """Create sample benchmark executions with real data"""
        self.stdout.write('Creating sample executions...')
        
        # Create a sample execution for each query set
        for query_set in BenchmarkQuerySet.objects.filter(is_active=True):
            execution = BenchmarkExecution.objects.create(
                name=f"Real Data Test - {query_set.name}",
                description=f"Benchmark execution using real {query_set.name.lower()}",
                query_set=query_set,
                search_mode="hybrid",
                ranking_algorithm="advanced",
                configuration={
                    'use_real_data': True,
                    'data_source': 'islamabad_high_court',
                    'test_type': 'real_data_benchmark'
                },
                status="completed",
                started_at=timezone.now(),
                completed_at=timezone.now(),
                total_queries=query_set.queries.count(),
                successful_queries=query_set.queries.count(),
                failed_queries=0
            )
            
            self.stdout.write(
                f'  Created execution: {execution.name} with {execution.total_queries} queries'
            )
