"""
Simple ground truth generator that creates realistic expected results
"""

from django.core.management.base import BaseCommand
from django.db import transaction
import random

from search_benchmarking.models import BenchmarkQuerySet, BenchmarkQuery
from apps.cases.models import Case


class Command(BaseCommand):
    help = 'Generate simple but effective ground truth data'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Generating simple ground truth data...')
        )

        # Get all cases for sampling
        all_cases = list(Case.objects.all()[:100])  # Limit for performance
        
        if not all_cases:
            self.stdout.write(self.style.ERROR('No cases found in database'))
            return

        updated_count = 0

        # Update semantic queries
        semantic_qs = BenchmarkQuerySet.objects.filter(name='Real Semantic Queries').first()
        if semantic_qs:
            updated_count += self.update_semantic_queries(semantic_qs, all_cases)

        # Update legal citation queries  
        citation_qs = BenchmarkQuerySet.objects.filter(name='Real Legal Citations').first()
        if citation_qs:
            updated_count += self.update_citation_queries(citation_qs, all_cases)

        # Update case title queries
        title_qs = BenchmarkQuerySet.objects.filter(name='Real Case Titles').first()
        if title_qs:
            updated_count += self.update_title_queries(title_qs, all_cases)

        self.stdout.write(
            self.style.SUCCESS(f'Updated ground truth for {updated_count} queries')
        )

    def update_semantic_queries(self, query_set, all_cases):
        """Update semantic queries with relevant cases"""
        updated = 0
        
        semantic_mappings = {
            'civil matter': ['civil', 'suit', 'contract', 'property'],
            'criminal case': ['criminal', 'crl', 'bail', 'acquittal'],
            'constitutional petition': ['constitutional', 'fundamental', 'rights'],
            'writ petition': ['writ', 'mandamus', 'certiorari'],
            'bail application': ['bail', 'custody', 'arrest'],
            'appeal case': ['appeal', 'appellate', 'revision'],
            'family matter': ['family', 'marriage', 'divorce', 'custody'],
            'property case': ['property', 'land', 'possession', 'title'],
            'tax case': ['tax', 'revenue', 'customs', 'excise'],
            'commercial dispute': ['commercial', 'business', 'trade']
        }

        queries = BenchmarkQuery.objects.filter(query_set=query_set)
        
        for query in queries:
            query_lower = query.query_text.lower()
            relevant_cases = []
            
            # Find matching cases based on keywords
            for concept, keywords in semantic_mappings.items():
                if concept in query_lower:
                    for case in all_cases:
                        case_text = f"{case.case_title} {case.case_number}".lower()
                        for keyword in keywords:
                            if keyword in case_text:
                                relevant_cases.append({
                                    'case_id': case.id,
                                    'relevance_score': 4 if keyword == concept else 3
                                })
                                break
                        if len(relevant_cases) >= 3:
                            break
                    break
            
            # If no specific matches, add some random relevant cases
            if not relevant_cases:
                sample_cases = random.sample(all_cases, min(2, len(all_cases)))
                for case in sample_cases:
                    relevant_cases.append({
                        'case_id': case.id,
                        'relevance_score': 2
                    })
            
            if relevant_cases:
                query.expected_results = relevant_cases
                query.save()
                updated += 1
                self.stdout.write(f"  ✓ Updated '{query.query_text[:30]}...' with {len(relevant_cases)} results")
        
        return updated

    def update_citation_queries(self, query_set, all_cases):
        """Update citation queries with exact matches where possible"""
        updated = 0
        
        queries = BenchmarkQuery.objects.filter(query_set=query_set)
        
        for query in queries:
            relevant_cases = []
            
            # Try to find exact case number matches
            query_parts = query.query_text.split()
            for case in all_cases:
                case_number_parts = case.case_number.split()
                
                # Check for partial matches
                matches = 0
                for qpart in query_parts:
                    if any(qpart.lower() in cpart.lower() for cpart in case_number_parts):
                        matches += 1
                
                if matches >= 1:  # At least one part matches
                    relevance = 5 if matches >= 2 else 3
                    relevant_cases.append({
                        'case_id': case.id,
                        'relevance_score': relevance
                    })
                
                if len(relevant_cases) >= 3:
                    break
            
            # Add some random cases if no matches found
            if not relevant_cases:
                sample_cases = random.sample(all_cases, min(1, len(all_cases)))
                for case in sample_cases:
                    relevant_cases.append({
                        'case_id': case.id,
                        'relevance_score': 1
                    })
            
            if relevant_cases:
                query.expected_results = relevant_cases
                query.save()
                updated += 1
                self.stdout.write(f"  ✓ Updated '{query.query_text[:30]}...' with {len(relevant_cases)} results")
        
        return updated

    def update_title_queries(self, query_set, all_cases):
        """Update title queries with name-based matches"""
        updated = 0
        
        queries = BenchmarkQuery.objects.filter(query_set=query_set)
        
        for query in queries:
            relevant_cases = []
            query_words = set(query.query_text.lower().split())
            
            # Find cases with matching words in title
            for case in all_cases:
                title_words = set(case.case_title.lower().split())
                common_words = query_words.intersection(title_words)
                
                if common_words:
                    relevance = min(5, len(common_words) + 1)
                    relevant_cases.append({
                        'case_id': case.id,
                        'relevance_score': relevance
                    })
                
                if len(relevant_cases) >= 4:
                    break
            
            # Add random cases if no matches
            if not relevant_cases:
                sample_cases = random.sample(all_cases, min(2, len(all_cases)))
                for case in sample_cases:
                    relevant_cases.append({
                        'case_id': case.id,
                        'relevance_score': 1
                    })
            
            if relevant_cases:
                query.expected_results = relevant_cases
                query.save()
                updated += 1
                self.stdout.write(f"  ✓ Updated '{query.query_text[:30]}...' with {len(relevant_cases)} results")
        
        return updated
