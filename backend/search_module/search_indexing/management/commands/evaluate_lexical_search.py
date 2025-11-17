"""
Django management command to evaluate lexical search performance
Extracts queries from database and runs them through lexical search to calculate metrics
"""

import time
import json
import math
from datetime import datetime
from typing import List, Dict, Any
import random

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

from django.core.management.base import BaseCommand
from django.db.models import Q
from apps.cases.models import Case, CaseSearchProfile, PartiesDetailData, CaseDetail
from search_indexing.models import SearchMetadata, DocumentChunk
from search_indexing.services.keyword_indexing import KeywordIndexingService


class Command(BaseCommand):
    help = 'Evaluate lexical search performance by extracting queries from database and running them'

    def add_arguments(self, parser):
        parser.add_argument(
            '--num-queries',
            type=int,
            default=50,
            help='Number of queries to extract and test (default: 50)'
        )
        parser.add_argument(
            '--output',
            type=str,
            default=None,
            help='Output file path for results (default: auto-generated Excel file)'
        )
        parser.add_argument(
            '--excel-only',
            action='store_true',
            help='Export only to Excel (skip JSON)'
        )
        parser.add_argument(
            '--complex-queries',
            action='store_true',
            help='Generate and test complex queries (natural language, synonyms, etc.)'
        )
        parser.add_argument(
            '--challenging-queries',
            action='store_true',
            help='Generate challenging queries (natural language, synonyms, negation, etc.) instead of exact matches'
        )
        parser.add_argument(
            '--natural-language-queries',
            action='store_true',
            help='Generate natural language queries (long descriptions, conceptual, synonym-based, multi-issue, etc.)'
        )
        parser.add_argument(
            '--no-bm25',
            action='store_true',
            help='Disable BM25 and use original icontains search (for testing)'
        )

    def handle(self, *args, **options):
        num_queries = options['num_queries']
        output_file = options['output']
        
        self.stdout.write(self.style.SUCCESS(f'Starting lexical search evaluation with {num_queries} queries...'))
        
        # Step 1: Extract queries from database with ground truth
        self.stdout.write('Extracting queries from database...')
        use_challenging = options.get('challenging_queries', False)
        use_natural = options.get('natural_language_queries', False)
        if use_natural:
            self.stdout.write(self.style.SUCCESS('Using natural language query generation mode...'))
            query_data = self.extract_natural_language_queries(num_queries)
        elif use_challenging:
            self.stdout.write(self.style.SUCCESS('Using challenging query generation mode...'))
            query_data = self.extract_queries_with_ground_truth(num_queries, use_challenging_queries=use_challenging)
        else:
            query_data = self.extract_queries_with_ground_truth(num_queries, use_challenging_queries=use_challenging)
        self.stdout.write(self.style.SUCCESS(f'Extracted {len(query_data)} queries'))
        
        # Step 2: Initialize keyword service
        # Allow disabling BM25 for testing original functionality
        use_bm25 = not options.get('no_bm25', False)
        keyword_service = KeywordIndexingService(use_bm25=use_bm25)
        
        # Step 3: Run queries and collect metrics
        self.stdout.write('Running queries through lexical search...')
        results = []
        total_time = 0
        
        for i, query_info in enumerate(query_data, 1):
            # Handle both tuple format (query, case_ids) and dict format (query, case_ids, category)
            if isinstance(query_info, dict):
                query = query_info.get('query', '')
                relevant_case_ids = query_info.get('relevant_case_ids', [])
                category = query_info.get('category', 'unknown')
            else:
                query, relevant_case_ids = query_info
                category = 'exact_match'  # Default for old format
            
            self.stdout.write(f'Processing query {i}/{len(query_data)}: "{query}"')
            
            start_time = time.time()
            search_results = keyword_service.search(query, top_k=20)
            execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            total_time += execution_time
            
            # Mark relevance for each result
            retrieved_case_ids = [r.get('case_id') for r in search_results]
            relevant_case_ids_set = set(relevant_case_ids) if relevant_case_ids else set()
            
            result = {
                'query': query,
                'category': category,
                'relevant_case_ids': relevant_case_ids,
                'num_results': len(search_results),
                'execution_time_ms': round(execution_time, 2),
                'results': [
                    {
                        'case_id': r.get('case_id', 'N/A'),
                        'case_number': r.get('case_number', 'N/A'),
                        'case_title': r.get('case_title', 'N/A')[:100] if r.get('case_title') else 'N/A',
                        'rank': r.get('rank', 0.0),
                        'is_relevant': r.get('case_id') in relevant_case_ids_set
                    }
                    for r in search_results[:20]  # Store top 20 for better metric calculation
                ]
            }
            results.append(result)
        
        # Step 4: Calculate metrics including IR metrics
        metrics = self.calculate_metrics(results, total_time)
        
        # Step 5: Display results
        self.display_results(metrics, results)
        
        # Step 6: Save to file
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f'lexical_search_evaluation_{timestamp}.xlsx'
        
        # Export to Excel
        if HAS_PANDAS:
            excel_path = output_file if output_file.endswith('.xlsx') else output_file.replace('.json', '.xlsx')
            self.export_to_excel(results, metrics, excel_path)
            self.stdout.write(self.style.SUCCESS(f'\nResults saved to Excel: {excel_path}'))
        else:
            self.stdout.write(self.style.WARNING('Pandas not available. Install with: pip install pandas openpyxl'))
        
        # Also save JSON if not excel-only
        if not options.get('excel_only', False):
            json_path = output_file.replace('.xlsx', '.json') if output_file.endswith('.xlsx') else output_file
            output_data = {
                'timestamp': datetime.now().isoformat(),
                'num_queries': len(query_data),
                'metrics': metrics,
                'query_results': results
            }
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            self.stdout.write(self.style.SUCCESS(f'Results also saved to JSON: {json_path}'))

    def extract_queries_with_ground_truth(self, num_queries: int, use_challenging_queries: bool = False) -> List[tuple]:
        """Extract queries with ground truth relevant case IDs"""
        if use_challenging_queries:
            return self.extract_challenging_queries(num_queries)
        return self.extract_queries(num_queries, return_ground_truth=True)
    
    def extract_queries(self, num_queries: int, return_ground_truth: bool = False) -> List:
        """Extract diverse queries from database"""
        queries = []
        
        # Get cases with search metadata
        indexed_case_ids = SearchMetadata.objects.filter(
            is_indexed=True
        ).values_list('case_id', flat=True)
        
        cases_with_metadata = Case.objects.filter(
            id__in=indexed_case_ids
        ).select_related('search_profile', 'court')[:500]  # Get a pool to sample from
        
        if not cases_with_metadata.exists():
            self.stdout.write(self.style.WARNING('No indexed cases found. Using all cases.'))
            cases_with_metadata = Case.objects.all()[:500]
        
        cases_list = list(cases_with_metadata)
        
        if len(cases_list) == 0:
            self.stdout.write(self.style.ERROR('No cases found in database!'))
            return []
        
        query_data = []  # List of (query, relevant_case_ids)
        seen_queries = set()
        
        # Strategy 1: Extract EXACT case numbers (high priority for lexical search)
        case_numbers = Case.objects.filter(
            id__in=indexed_case_ids
        ).exclude(case_number__isnull=True).exclude(case_number='').values_list('case_number', 'id')[:150]
        
        for case_num, case_id in case_numbers:
            case_num = case_num.strip()
            if len(case_num) > 3:
                query_lower = case_num.lower()
                if query_lower not in seen_queries:
                    seen_queries.add(query_lower)
                    query_data.append((case_num, [case_id]))
        
        # Strategy 2: Extract EXACT case titles (full titles - perfect for lexical)
        case_titles = Case.objects.filter(
            id__in=indexed_case_ids
        ).exclude(case_title__isnull=True).exclude(case_title='').values_list('case_title', 'id')[:150]
        
        for title, case_id in case_titles:
            title = title.strip()
            if len(title) > 10:
                query_lower = title.lower()
                if query_lower not in seen_queries:
                    seen_queries.add(query_lower)
                    query_data.append((title, [case_id]))
        
        # Strategy 3: Extract party names (exact matches)
        parties_data = PartiesDetailData.objects.filter(
            case_id__in=indexed_case_ids
        ).exclude(party_name__isnull=True).exclude(party_name='').values_list('party_name', 'case_id').distinct()[:100]
        
        for party_name, case_id in parties_data:
            party_name = party_name.strip()
            if len(party_name) > 5:
                query_lower = party_name.lower()
                if query_lower not in seen_queries:
                    seen_queries.add(query_lower)
                    # Find all cases with this exact party
                    relevant_cases = list(PartiesDetailData.objects.filter(
                        party_name__iexact=party_name
                    ).values_list('case_id', flat=True).distinct())
                    if relevant_cases:
                        query_data.append((party_name, relevant_cases))
        
        # Strategy 4: Extract partial case titles (first 3-7 words - common search pattern)
        for case in cases_list[:100]:
            if case.case_title:
                title = case.case_title.strip()
                words = title.split()
                # Generate 3-word, 5-word, and 7-word phrases
                for word_count in [3, 5, 7]:
                    if len(words) >= word_count:
                        phrase = ' '.join(words[:word_count])
                        phrase_lower = phrase.lower()
                        if phrase_lower not in seen_queries:
                            seen_queries.add(phrase_lower)
                            query_data.append((phrase, [case.id]))
        
        # Strategy 5: Extract case number patterns (e.g., "P.S.L.A.", "FERA", "Jail Appeal")
        case_num_patterns = {}
        for case in cases_list:
            if case.case_number:
                case_num = case.case_number
                # Extract patterns like "P.S.L.A.", "FERA", "Jail Appeal", etc.
                parts = case_num.split()
                if parts:
                    pattern = parts[0]  # First part often contains the pattern
                    if len(pattern) > 2 and pattern not in case_num_patterns:
                        case_num_patterns[pattern] = []
                    if pattern in case_num_patterns:
                        case_num_patterns[pattern].append(case.id)
        
        for pattern, case_ids in list(case_num_patterns.items())[:50]:
            query_lower = pattern.lower()
            if query_lower not in seen_queries and len(case_ids) > 0:
                seen_queries.add(query_lower)
                query_data.append((pattern, case_ids[:10]))  # Limit to 10 cases per pattern
        
        # Strategy 6: Extract from case details - FIR numbers, sections
        case_details = CaseDetail.objects.filter(
            case_id__in=indexed_case_ids
        ).exclude(fir_number__isnull=True).exclude(fir_number='')[:50]
        
        for detail in case_details:
            if detail.fir_number:
                fir = detail.fir_number.strip()
                if len(fir) > 5:
                    query_lower = fir.lower()
                    if query_lower not in seen_queries:
                        seen_queries.add(query_lower)
                        query_data.append((fir, [detail.case_id]))
        
        # Strategy 7: Extract under_section (legal sections)
        sections = CaseDetail.objects.filter(
            case_id__in=indexed_case_ids
        ).exclude(under_section__isnull=True).exclude(under_section='').values_list('under_section', 'case_id').distinct()[:50]
        
        for section, case_id in sections:
            section = section.strip()
            if len(section) > 3:
                query_lower = section.lower()
                if query_lower not in seen_queries:
                    seen_queries.add(query_lower)
                    relevant_cases = list(CaseDetail.objects.filter(
                        under_section__icontains=section
                    ).values_list('case_id', flat=True).distinct())
                    if relevant_cases:
                        query_data.append((section, relevant_cases[:10]))
        
        # Strategy 8: Extract court names
        courts = Case.objects.filter(
            id__in=indexed_case_ids
        ).exclude(court__isnull=True).select_related('court').values_list('court__name', 'id')[:50]
        
        for court_name, case_id in courts:
            if court_name:
                court_name = court_name.strip()
                query_lower = court_name.lower()
                if query_lower not in seen_queries and len(court_name) > 5:
                    seen_queries.add(query_lower)
                    relevant_cases = list(Case.objects.filter(
                        court__name__icontains=court_name
                    ).values_list('id', flat=True).distinct())
                    if relevant_cases:
                        query_data.append((court_name, relevant_cases[:20]))
        
        # Remove duplicates and ensure we have enough
        unique_query_data = []
        seen_queries_final = set()
        for query, case_ids in query_data:
            query_lower = query.lower().strip()
            if query_lower not in seen_queries_final and len(query_lower) > 2:
                seen_queries_final.add(query_lower)
                unique_query_data.append((query, case_ids))
        
        # If we need more, generate from case titles
        if len(unique_query_data) < num_queries:
            remaining = num_queries - len(unique_query_data)
            for case in cases_list[len(unique_query_data):len(unique_query_data)+remaining]:
                if case.case_title:
                    words = case.case_title.split()
                    if len(words) >= 2:
                        phrase_len = min(random.randint(2, 4), len(words))
                        phrase = ' '.join(words[:phrase_len])
                        phrase_lower = phrase.lower()
                        if phrase_lower not in seen_queries_final:
                            seen_queries_final.add(phrase_lower)
                            unique_query_data.append((phrase, [case.id]))
                            if len(unique_query_data) >= num_queries:
                                break
        
        # Randomly sample if we have more than needed
        if len(unique_query_data) > num_queries:
            query_data = random.sample(unique_query_data, num_queries)
        else:
            query_data = unique_query_data
        
        if return_ground_truth:
            return query_data[:num_queries]
        else:
            return [q[0] for q in query_data[:num_queries]]
    
    def extract_challenging_queries(self, num_queries: int) -> List[tuple]:
        """Extract reasonable challenging queries (5-6 words max) that test lexical search"""
        query_data = []
        seen_queries = set()
        
        # Get indexed cases
        indexed_case_ids = SearchMetadata.objects.filter(
            is_indexed=True
        ).values_list('case_id', flat=True)
        
        cases_list = list(Case.objects.filter(
            id__in=indexed_case_ids
        ).select_related('court', 'case_detail')[:500])
        
        if not cases_list:
            self.stdout.write(self.style.ERROR('No indexed cases found!'))
            return []
        
        # Category 1: Short natural-language queries (5-6 words from case titles/descriptions)
        self.stdout.write('  Generating natural language queries (5-6 words)...')
        natural_count = 0
        for case in cases_list[:100]:
            if case.case_title:
                title_words = case.case_title.split()
                # Extract 4-6 word phrases from titles
                for i in range(len(title_words) - 3):
                    phrase = ' '.join(title_words[i:i+random.randint(4, 6)])
                    if len(phrase) > 15 and len(phrase) < 80 and phrase.lower() not in seen_queries:
                        seen_queries.add(phrase.lower())
                        query_data.append({'query': phrase, 'relevant_case_ids': [case.id], 'category': 'natural_language'})
                        natural_count += 1
                        if natural_count >= 30:
                            break
                if natural_count >= 30:
                    break
            
            # From case detail - extract short meaningful phrases
            case_detail = getattr(case, 'case_detail', None)
            if case_detail and case_detail.case_description:
                desc_words = case_detail.case_description.split()
                if len(desc_words) >= 5:
                    # Extract 5-word phrases
                    for i in range(0, min(3, len(desc_words) - 4)):
                        phrase = ' '.join(desc_words[i:i+5])
                        if len(phrase) > 20 and len(phrase) < 100 and phrase.lower() not in seen_queries:
                            seen_queries.add(phrase.lower())
                            query_data.append({'query': phrase, 'relevant_case_ids': [case.id], 'category': 'natural_language'})
                            natural_count += 1
                            if natural_count >= 30:
                                break
                if natural_count >= 30:
                    break
        
        # Category 2: Short conceptual queries (5-6 words)
        self.stdout.write('  Generating conceptual queries (5-6 words)...')
        legal_concepts = [
            'bail application criminal procedure',
            'writ petition maintainability jurisdiction',
            'limitation period civil suits',
            'pre arrest bail principles',
            'contract breach compensation damages',
            'service matter termination reinstatement',
            'tax assessment appeal penalty',
            'property dispute ownership possession',
            'criminal appeal conviction sentence',
            'review petition grounds limitations'
        ]
        
        for concept in legal_concepts:
            if concept.lower() not in seen_queries and len(concept.split()) <= 6:
                seen_queries.add(concept.lower())
                # Find cases with relevant terms
                key_terms = [t for t in concept.split() if len(t) > 3]
                relevant_cases = []
                if key_terms:
                    relevant_cases = list(Case.objects.filter(
                        id__in=indexed_case_ids
                    ).filter(
                        Q(case_title__icontains=key_terms[0]) |
                        Q(case_title__icontains=key_terms[-1] if len(key_terms) > 1 else '')
                    ).values_list('id', flat=True)[:10])
                if relevant_cases:
                    query_data.append({'query': concept, 'relevant_case_ids': relevant_cases, 'category': 'conceptual'})
        
        # Category 3: Reasonable negation queries (5-6 words)
        self.stdout.write('  Generating negation queries (5-6 words)...')
        # Extract actual terms from cases first
        bail_cases = Case.objects.filter(id__in=indexed_case_ids, case_title__icontains='bail')[:5]
        appeal_cases = Case.objects.filter(id__in=indexed_case_ids, case_title__icontains='appeal')[:5]
        writ_cases = Case.objects.filter(id__in=indexed_case_ids, case_title__icontains='writ')[:5]
        
        negation_queries = []
        for case in bail_cases:
            if case.case_title:
                words = case.case_title.split()[:4]  # First 4 words
                query = ' '.join(words) + ' NOT granted'
                if len(query.split()) <= 6 and query.lower() not in seen_queries:
                    negation_queries.append((query, [case.id]))
        
        for case in appeal_cases:
            if case.case_title:
                words = case.case_title.split()[:3]
                query = ' '.join(words) + ' NOT allowed'
                if len(query.split()) <= 6 and query.lower() not in seen_queries:
                    negation_queries.append((query, [case.id]))
        
        for case in writ_cases:
            if case.case_title:
                words = case.case_title.split()[:3]
                query = ' '.join(words) + ' NOT maintainable'
                if len(query.split()) <= 6 and query.lower() not in seen_queries:
                    negation_queries.append((query, [case.id]))
        
        # Add some standard short negation queries
        short_negations = [
            'bail NOT granted',
            'appeal NOT allowed',
            'writ NOT maintainable',
            'review NOT dismissed',
            'limitation NOT condoned'
        ]
        for query in short_negations:
            if query.lower() not in seen_queries:
                seen_queries.add(query.lower())
                key_term = query.split()[0]
                relevant_cases = list(Case.objects.filter(
                    id__in=indexed_case_ids,
                    case_title__icontains=key_term
                ).values_list('id', flat=True)[:10])
                if relevant_cases:
                    query_data.append({'query': query, 'relevant_case_ids': relevant_cases, 'category': 'negation'})
        
        for query, case_ids in negation_queries[:15]:
            if query.lower() not in seen_queries:
                seen_queries.add(query.lower())
                query_data.append({'query': query, 'relevant_case_ids': case_ids, 'category': 'negation'})
        
        # Category 4: Related multi-issue queries (5-6 words)
        self.stdout.write('  Generating multi-issue queries (5-6 words)...')
        # Generate from actual case combinations
        multi_issue_queries = []
        for case in cases_list[:50]:
            if case.case_title:
                title_words = case.case_title.split()
                # Extract 2-3 key terms and combine with related terms
                if len(title_words) >= 2:
                    key_terms = title_words[:2]
                    # Add related legal terms
                    if 'bail' in ' '.join(title_words).lower():
                        query = ' '.join(key_terms) + ' medical evidence delay'
                    elif 'contract' in ' '.join(title_words).lower():
                        query = ' '.join(key_terms) + ' breach compensation'
                    elif 'service' in ' '.join(title_words).lower():
                        query = ' '.join(key_terms) + ' termination reinstatement'
                    elif 'tax' in ' '.join(title_words).lower():
                        query = ' '.join(key_terms) + ' assessment appeal'
                    else:
                        continue
                    
                    if len(query.split()) <= 6 and query.lower() not in seen_queries:
                        seen_queries.add(query.lower())
                        multi_issue_queries.append((query, [case.id]))
                        if len(multi_issue_queries) >= 20:
                            break
        
        for query, case_ids in multi_issue_queries:
            query_data.append({'query': query, 'relevant_case_ids': case_ids, 'category': 'multi_issue'})
        
        # Category 5: Short procedural queries (5-6 words)
        self.stdout.write('  Generating procedural queries (5-6 words)...')
        procedural_queries = [
            'pre arrest bail procedure',
            'writ petition maintainability test',
            'appeal against interim order',
            'revision against civil order',
            'review petition grounds',
            'bail application criminal cases',
            'limitation condonation delay',
            'jurisdiction high court writ',
            'service matter appeal procedure',
            'tax assessment appeal process'
        ]
        
        for query in procedural_queries:
            if query.lower() not in seen_queries and len(query.split()) <= 6:
                seen_queries.add(query.lower())
                key_terms = [q for q in query.split() if len(q) > 3]
                if key_terms:
                    relevant_cases = list(Case.objects.filter(
                        id__in=indexed_case_ids
                    ).filter(
                        Q(case_title__icontains=key_terms[0]) | Q(case_number__icontains=key_terms[0])
                    ).values_list('id', flat=True)[:10])
                    if relevant_cases:
                        query_data.append({'query': query, 'relevant_case_ids': relevant_cases, 'category': 'procedural'})
        
        # Category 6: Short statute queries (5-6 words)
        self.stdout.write('  Generating statute queries (5-6 words)...')
        case_details = CaseDetail.objects.filter(
            case_id__in=indexed_case_ids
        ).exclude(under_section__isnull=True).exclude(under_section='')[:30]
        
        for detail in case_details:
            section = detail.under_section.strip()
            if section:
                # Extract just section number (e.g., "302" from "Section 302 PPC")
                section_num = ''.join([c for c in section if c.isdigit()])[:3]
                if section_num:
                    # Generate short queries
                    queries = [
                        f"Section {section_num} PPC bail",
                        f"Section {section_num} PPC interpretation",
                        f"FIR {section_num} criminal case"
                    ]
                    for query in queries:
                        if query.lower() not in seen_queries and len(query.split()) <= 6:
                            seen_queries.add(query.lower())
                            relevant_cases = list(CaseDetail.objects.filter(
                                under_section__icontains=section_num
                            ).values_list('case_id', flat=True).distinct()[:10])
                            if relevant_cases:
                                query_data.append({'query': query, 'relevant_case_ids': relevant_cases, 'category': 'statute'})
        
        # Category 7: Short misspelling queries (5-6 words)
        self.stdout.write('  Generating misspelling queries (5-6 words)...')
        misspelling_map = {
            'bail': 'bal',
            'custody': 'custidy',
            'modification': 'modfication',
            'appeal': 'apel',
            'petition': 'petion',
            'jurisdiction': 'jurisdiciton'
        }
        
        misspelling_count = 0
        for case in cases_list[:30]:
            if case.case_title:
                title = case.case_title.lower()
                title_words = title.split()
                if len(title_words) <= 6:
                    for correct, misspelling in misspelling_map.items():
                        if correct in title:
                            query = title.replace(correct, misspelling)
                            if query != title and query.lower() not in seen_queries:
                                seen_queries.add(query.lower())
                                query_data.append({'query': query, 'relevant_case_ids': [case.id], 'category': 'misspelling'})
                                misspelling_count += 1
                                if misspelling_count >= 15:
                                    break
                    if misspelling_count >= 15:
                        break
        
        # Standalone short misspellings
        standalone_misspellings = [
            'pre arrest bal',
            'custidy modfication',
            'apel against order',
            'petion maintainability',
            'jurisdiciton high court'
        ]
        for query in standalone_misspellings:
            if query.lower() not in seen_queries and len(query.split()) <= 6:
                seen_queries.add(query.lower())
                # Find cases with correct spelling
                correct_query = query.replace('bal', 'bail').replace('custidy', 'custody').replace('modfication', 'modification')
                correct_query = correct_query.replace('apel', 'appeal').replace('petion', 'petition').replace('jurisdiciton', 'jurisdiction')
                relevant_cases = list(Case.objects.filter(
                    id__in=indexed_case_ids
                ).filter(
                    Q(case_title__icontains=correct_query.split()[0]) | Q(case_number__icontains=correct_query.split()[0])
                ).values_list('id', flat=True)[:10])
                if relevant_cases:
                    query_data.append({'query': query, 'relevant_case_ids': relevant_cases, 'category': 'misspelling'})
        
        # Remove duplicates and sample
        unique_queries = []
        seen_final = set()
        for query_info in query_data:
            query = query_info.get('query', '')
            query_lower = query.lower().strip()
            if query_lower not in seen_final and len(query_lower) > 5:
                seen_final.add(query_lower)
                unique_queries.append(query_info)
        
        # Sample to desired number
        if len(unique_queries) > num_queries:
            return random.sample(unique_queries, num_queries)
        else:
            return unique_queries[:num_queries]

    def extract_natural_language_queries(self, num_queries: int) -> List[Dict[str, Any]]:
        """
        Generate natural language queries from database based on the types shown in images:
        1. Long Natural-Language Queries
        2. Conceptual / Legal-Doctrine Queries
        3. Synonym-Based Queries
        4. Multi-Issue / Compound Queries
        5. Procedural / Technical Queries
        6. Statutory / Section-Based Queries
        7. Noisy / Misspelled Queries
        8. Short, Ambiguous Queries
        """
        query_data = []
        seen_queries = set()
        
        # Get indexed cases
        indexed_case_ids = SearchMetadata.objects.filter(
            is_indexed=True
        ).values_list('case_id', flat=True)
        
        cases_list = list(Case.objects.filter(
            id__in=indexed_case_ids
        ).select_related('court', 'case_detail')[:500])
        
        if not cases_list:
            self.stdout.write(self.style.ERROR('No indexed cases found!'))
            return []
        
        # Category 1: Long Natural-Language Queries (detailed scenarios from case descriptions)
        self.stdout.write('  Generating long natural-language queries...')
        natural_count = 0
        
        # Generate descriptive queries based on case types
        bail_cases = [c for c in cases_list if 'bail' in c.case_title.lower()][:10]
        appeal_cases = [c for c in cases_list if 'appeal' in c.case_title.lower()][:10]
        writ_cases = [c for c in cases_list if 'writ' in c.case_title.lower()][:10]
        service_cases = [c for c in cases_list if 'service' in c.case_title.lower() or 'termination' in c.case_title.lower()][:10]
        maintenance_cases = [c for c in cases_list if 'maintenance' in c.case_title.lower()][:5]
        
        # Bail-related queries - generate multiple queries
        bail_queries = [
            "Case where bail was refused due to contradictions in the statements of prosecution witnesses",
            "Judgment discussing delay in lodging FIR and its impact on credibility of prosecution",
            "Case where bail application was rejected due to non-cooperation with investigation",
            "Ruling on pre-arrest bail application in criminal case",
            "Court decision where bail was granted after considering medical evidence"
        ]
        for query in bail_queries:
            if query.lower() not in seen_queries:
                seen_queries.add(query.lower())
                # Find all bail cases as relevant
                relevant_cases = [c.id for c in bail_cases] if bail_cases else []
                if not relevant_cases:
                    relevant_cases = list(Case.objects.filter(
                        id__in=indexed_case_ids,
                        case_title__icontains='bail'
                    ).values_list('id', flat=True)[:10])
                if relevant_cases:
                    query_data.append({
                        'query': query,
                        'relevant_case_ids': relevant_cases,
                        'category': 'long_natural_language'
                    })
                    natural_count += 1
        
        # Appeal-related queries
        appeal_queries = [
            "Judgment discussing appeal against conviction and sentence",
            "Case where the High Court set aside departmental dismissal due to violation of due process",
            "Ruling on whether evidence collected after sunset search warrants is admissible in criminal trial",
            "Court decision where appeal was allowed after considering new evidence",
            "Judgment on appeal against interim order in civil matter"
        ]
        for query in appeal_queries:
            if query.lower() not in seen_queries:
                seen_queries.add(query.lower())
                relevant_cases = [c.id for c in appeal_cases] if appeal_cases else []
                if not relevant_cases:
                    relevant_cases = list(Case.objects.filter(
                        id__in=indexed_case_ids,
                        case_title__icontains='appeal'
                    ).values_list('id', flat=True)[:10])
                if relevant_cases:
                    query_data.append({
                        'query': query,
                        'relevant_case_ids': relevant_cases,
                        'category': 'long_natural_language'
                    })
                    natural_count += 1
        
        # Service-related queries
        service_queries = [
            "Case where the High Court set aside departmental dismissal due to violation of due process",
            "Court decision on service matter involving termination and reinstatement",
            "Judgment discussing legitimate expectation in service matters",
            "Ruling on service matter appeal regarding promotion and seniority"
        ]
        for query in service_queries:
            if query.lower() not in seen_queries:
                seen_queries.add(query.lower())
                relevant_cases = [c.id for c in service_cases] if service_cases else []
                if not relevant_cases:
                    relevant_cases = list(Case.objects.filter(
                        id__in=indexed_case_ids
                    ).filter(
                        Q(case_title__icontains='service') | Q(case_title__icontains='termination')
                    ).values_list('id', flat=True)[:10])
                if relevant_cases:
                    query_data.append({
                        'query': query,
                        'relevant_case_ids': relevant_cases,
                        'category': 'long_natural_language'
                    })
                    natural_count += 1
        
        # Maintenance-related queries
        maintenance_queries = [
            "Court decision where the party sought execution of maintenance decree after long delay",
            "Judgment on maintenance case involving determination of amount and arrears",
            "Ruling on maintenance application filed by wife against husband"
        ]
        for query in maintenance_queries:
            if query.lower() not in seen_queries:
                seen_queries.add(query.lower())
                relevant_cases = [c.id for c in maintenance_cases] if maintenance_cases else []
                if not relevant_cases:
                    relevant_cases = list(Case.objects.filter(
                        id__in=indexed_case_ids,
                        case_title__icontains='maintenance'
                    ).values_list('id', flat=True)[:10])
                if relevant_cases:
                    query_data.append({
                        'query': query,
                        'relevant_case_ids': relevant_cases,
                        'category': 'long_natural_language'
                    })
                    natural_count += 1
        
        # Category 2: Conceptual / Legal-Doctrine Queries
        self.stdout.write('  Generating conceptual/legal-doctrine queries...')
        legal_concepts = [
            ('bail', 'principles for granting pre-arrest bail under criminal procedure'),
            ('writ', 'scope of writ jurisdiction under article 199 high court'),
            ('limitation', 'limitation period for filing civil revision under section 115'),
            ('review', 'difference between review and revision under civil procedure'),
            ('maintenance', 'burden of proof in maintenance cases family court'),
            ('service', 'doctrine of legitimate expectation in service matters'),
            ('contract', 'principles of contract breach and compensation damages'),
            ('tax', 'scope of tax assessment appeal and penalty proceedings'),
            ('property', 'principles for recovery of possession and illegal dispossession'),
            ('criminal', 'scope of appellate court to reappraise evidence in criminal appeal')
        ]
        
        for keyword, concept_query in legal_concepts:
            if concept_query.lower() not in seen_queries:
                seen_queries.add(concept_query.lower())
                relevant_cases = list(Case.objects.filter(
                    id__in=indexed_case_ids,
                    case_title__icontains=keyword
                ).values_list('id', flat=True)[:10])
                if relevant_cases:
                    query_data.append({
                        'query': concept_query,
                        'relevant_case_ids': relevant_cases,
                        'category': 'conceptual_legal_doctrine'
                    })
        
        # Category 3: Synonym-Based Queries
        self.stdout.write('  Generating synonym-based queries...')
        synonym_pairs = [
            ('termination', 'dismissal', 'employment'),
            ('custody', 'guardianship', 'minor'),
            ('fraudulent transfer', 'benami transaction', 'property'),
            ('harassment', 'hostile work environment', 'workplace'),
            ('sentence reduction', 'mitigating circumstances', 'extenuating factors')
        ]
        
        for term1, term2, context in synonym_pairs:
            # Query uses term1, documents may use term2
            query = f"Case involving {term1} of {context}"
            if query.lower() not in seen_queries:
                seen_queries.add(query.lower())
                relevant_cases = list(Case.objects.filter(
                    id__in=indexed_case_ids
                ).filter(
                    Q(case_title__icontains=term1) | Q(case_title__icontains=term2)
                ).values_list('id', flat=True)[:10])
                if relevant_cases:
                    query_data.append({
                        'query': query,
                        'relevant_case_ids': relevant_cases,
                        'category': 'synonym_based'
                    })
        
        # Category 4: Multi-Issue / Compound Queries
        self.stdout.write('  Generating multi-issue/compound queries...')
        multi_issue_templates = [
            ('tenant', 'eviction case involving rent default and determination of fair market rent'),
            ('possession', 'case involving illegal dispossession recovery of possession and claim for damages'),
            ('bail', 'pre-arrest bail rejected due to abscondence and non-cooperation with investigation'),
            ('inheritance', 'inheritance dispute involving widows minors and allocation of shares'),
            ('winding up', 'company matter relating to winding up petition shareholder dispute and auditor appointment')
        ]
        
        for keyword, query_template in multi_issue_templates:
            if query_template.lower() not in seen_queries:
                seen_queries.add(query_template.lower())
                relevant_cases = list(Case.objects.filter(
                    id__in=indexed_case_ids,
                    case_title__icontains=keyword
                ).values_list('id', flat=True)[:10])
                if relevant_cases:
                    query_data.append({
                        'query': query_template,
                        'relevant_case_ids': relevant_cases,
                        'category': 'multi_issue_compound'
                    })
        
        # Category 5: Procedural / Technical Queries
        self.stdout.write('  Generating procedural/technical queries...')
        procedural_queries = [
            'maintainability of intra court appeal in service matters',
            'limitation period for filing civil revision under section 115 CPC',
            'conditions under which ex-parte decree can be set aside',
            'scope of appellate court to reappraise evidence in criminal appeal',
            'whether interim orders in family cases are challengeable before high court'
        ]
        
        for query in procedural_queries:
            if query.lower() not in seen_queries:
                seen_queries.add(query.lower())
                # Extract key terms
                key_terms = [t for t in query.split() if len(t) > 4]
                relevant_cases = []
                if key_terms:
                    q_filter = Q()
                    for term in key_terms[:2]:
                        q_filter |= Q(case_title__icontains=term)
                    relevant_cases = list(Case.objects.filter(
                        id__in=indexed_case_ids
                    ).filter(q_filter).values_list('id', flat=True)[:10])
                if relevant_cases:
                    query_data.append({
                        'query': query,
                        'relevant_case_ids': relevant_cases,
                        'category': 'procedural_technical'
                    })
        
        # Category 6: Statutory / Section-Based Queries
        self.stdout.write('  Generating statutory/section-based queries...')
        case_details = CaseDetail.objects.filter(
            case_id__in=indexed_case_ids
        ).exclude(under_section__isnull=True).exclude(under_section='')[:30]
        
        section_queries = []
        for detail in case_details:
            section = detail.under_section.strip()
            if section:
                # Extract section number
                section_num = ''.join([c for c in section if c.isdigit()])[:3]
                if section_num:
                    queries = [
                        f"interpretation of section {section_num} PPC regarding intention vs knowledge",
                        f"scope of section {section_num} regarding criminal procedure",
                        f"requirements of section {section_num} for registration of FIR",
                        f"mandatory conditions under section {section_num}",
                        f"application of section {section_num} in criminal cases"
                    ]
                    for query in queries[:2]:  # Limit to 2 per section
                        if query.lower() not in seen_queries:
                            seen_queries.add(query.lower())
                            relevant_cases = list(CaseDetail.objects.filter(
                                under_section__icontains=section_num
                            ).values_list('case_id', flat=True).distinct()[:10])
                            if relevant_cases:
                                section_queries.append({
                                    'query': query,
                                    'relevant_case_ids': relevant_cases,
                                    'category': 'statutory_section_based'
                                })
                                if len(section_queries) >= 15:
                                    break
                    if len(section_queries) >= 15:
                        break
        
        query_data.extend(section_queries)
        
        # Category 7: Noisy / Misspelled Queries
        self.stdout.write('  Generating noisy/misspelled queries...')
        misspelling_map = {
            'bail': 'bal',
            'custody': 'custidy',
            'modification': 'modfication',
            'appeal': 'apel',
            'petition': 'petion',
            'jurisdiction': 'jurisdiciton',
            'arrest': 'arest',
            'requirements': 'reqirmnts',
            'dispossession': 'dispsesion',
            'action': 'acton',
            'harassment': 'harasmant',
            'employee': 'emplyee',
            'review': 'revw',
            'setting': 'seting',
            'aside': 'asid',
            'ex-parte': 'exprte',
            'decree': 'decra'
        }
        
        misspelling_count = 0
        for case in cases_list[:50]:
            if case.case_title:
                title = case.case_title.lower()
                # Create misspelled version
                misspelled_title = title
                for correct, misspelling in misspelling_map.items():
                    if correct in misspelled_title:
                        misspelled_title = misspelled_title.replace(correct, misspelling)
                        break  # Only replace one word per query
                
                if misspelled_title != title and misspelled_title.lower() not in seen_queries:
                    seen_queries.add(misspelled_title.lower())
                    query_data.append({
                        'query': misspelled_title,
                        'relevant_case_ids': [case.id],
                        'category': 'noisy_misspelled'
                    })
                    misspelling_count += 1
                    if misspelling_count >= 10:
                        break
        
        # Standalone misspelled queries
        standalone_misspellings = [
            'pre arest bal reqirmnts',
            'custidy modfication minor welfar',
            'illgal dispsesion acton',
            'harasmant of female emplyee at work',
            'civil reviw seting asid exprte decra'
        ]
        for query in standalone_misspellings:
            if query.lower() not in seen_queries:
                seen_queries.add(query.lower())
                # Find cases with correct spelling
                correct_terms = ['bail', 'custody', 'modification', 'dispossession', 'harassment', 'employee', 'review']
                relevant_cases = []
                for term in correct_terms:
                    if any(t in query for t in [term[:3] for term in correct_terms]):
                        relevant_cases = list(Case.objects.filter(
                            id__in=indexed_case_ids,
                            case_title__icontains=term
                        ).values_list('id', flat=True)[:10])
                        break
                if relevant_cases:
                    query_data.append({
                        'query': query,
                        'relevant_case_ids': relevant_cases,
                        'category': 'noisy_misspelled'
                    })
        
        # Category 8: Short, Ambiguous Queries
        self.stdout.write('  Generating short ambiguous queries...')
        short_ambiguous = [
            'eviction',
            'harassment',
            'fraudulent transfer',
            'medical negligence',
            'service matter appeal',
            'bail',
            'custody',
            'maintenance',
            'writ petition',
            'limitation'
        ]
        
        for query in short_ambiguous:
            if query.lower() not in seen_queries:
                seen_queries.add(query.lower())
                relevant_cases = list(Case.objects.filter(
                    id__in=indexed_case_ids,
                    case_title__icontains=query.split()[0]
                ).values_list('id', flat=True)[:15])
                if relevant_cases:
                    query_data.append({
                        'query': query,
                        'relevant_case_ids': relevant_cases,
                        'category': 'short_ambiguous'
                    })
        
        # Remove duplicates and sample
        unique_queries = []
        seen_final = set()
        for query_info in query_data:
            query = query_info.get('query', '')
            query_lower = query.lower().strip()
            if query_lower not in seen_final and len(query_lower) > 3:
                seen_final.add(query_lower)
                unique_queries.append(query_info)
        
        # Generate well-formatted queries from case descriptions
        self.stdout.write('  Generating well-formatted queries from case descriptions...')
        cases_with_details = Case.objects.filter(
            id__in=indexed_case_ids
        ).select_related('case_detail').exclude(case_detail__case_description__isnull=True).exclude(case_detail__case_description='')[:200]
        
        desc_count = 0
        for case in cases_with_details:
            if desc_count >= 30:  # Limit to 30 well-formatted queries
                break
                
            case_detail = case.case_detail
            if case_detail and case_detail.case_description:
                desc = case_detail.case_description.strip()
                
                # Create well-formatted queries based on case type and content
                case_title_lower = case.case_title.lower() if case.case_title else ''
                
                # Template-based queries that match actual case content
                if 'bail' in case_title_lower or 'bail' in desc.lower():
                    templates = [
                        f"Case where bail was refused due to contradictions in the statements of prosecution witnesses",
                        f"Judgment discussing delay in lodging FIR and its impact on credibility of prosecution",
                        f"Case where bail application was rejected due to non-cooperation with investigation",
                        f"Ruling on pre-arrest bail application in criminal case",
                        f"Court decision where bail was granted after considering medical evidence"
                    ]
                    for template in templates[:1]:  # One per case
                        if template.lower() not in seen_final:
                            seen_final.add(template.lower())
                            unique_queries.append({
                                'query': template,
                                'relevant_case_ids': [case.id],
                                'category': 'long_natural_language'
                            })
                            desc_count += 1
                            break
                
                elif 'appeal' in case_title_lower or 'appeal' in desc.lower():
                    templates = [
                        f"Judgment discussing appeal against conviction and sentence",
                        f"Case where the High Court set aside departmental dismissal due to violation of due process",
                        f"Ruling on whether evidence collected after sunset search warrants is admissible in criminal trial",
                        f"Court decision where appeal was allowed after considering new evidence",
                        f"Judgment on appeal against interim order in civil matter"
                    ]
                    for template in templates[:1]:
                        if template.lower() not in seen_final:
                            seen_final.add(template.lower())
                            unique_queries.append({
                                'query': template,
                                'relevant_case_ids': [case.id],
                                'category': 'long_natural_language'
                            })
                            desc_count += 1
                            break
                
                elif 'writ' in case_title_lower or 'writ' in desc.lower():
                    templates = [
                        f"Ruling on writ petition maintainability and jurisdiction",
                        f"Case where writ petition was filed seeking direction from high court",
                        f"Judgment on writ petition regarding violation of fundamental rights",
                        f"Court decision on writ petition challenging administrative action"
                    ]
                    for template in templates[:1]:
                        if template.lower() not in seen_final:
                            seen_final.add(template.lower())
                            unique_queries.append({
                                'query': template,
                                'relevant_case_ids': [case.id],
                                'category': 'long_natural_language'
                            })
                            desc_count += 1
                            break
                
                elif 'service' in case_title_lower or 'termination' in case_title_lower or 'service' in desc.lower():
                    templates = [
                        f"Case where the High Court set aside departmental dismissal due to violation of due process",
                        f"Court decision on service matter involving termination and reinstatement",
                        f"Judgment discussing legitimate expectation in service matters",
                        f"Ruling on service matter appeal regarding promotion and seniority"
                    ]
                    for template in templates[:1]:
                        if template.lower() not in seen_final:
                            seen_final.add(template.lower())
                            unique_queries.append({
                                'query': template,
                                'relevant_case_ids': [case.id],
                                'category': 'long_natural_language'
                            })
                            desc_count += 1
                            break
                
                elif 'maintenance' in case_title_lower or 'maintenance' in desc.lower():
                    templates = [
                        f"Court decision where the party sought execution of maintenance decree after long delay",
                        f"Judgment on maintenance case involving determination of amount and arrears",
                        f"Ruling on maintenance application filed by wife against husband"
                    ]
                    for template in templates[:1]:
                        if template.lower() not in seen_final:
                            seen_final.add(template.lower())
                            unique_queries.append({
                                'query': template,
                                'relevant_case_ids': [case.id],
                                'category': 'long_natural_language'
                            })
                            desc_count += 1
                            break
                
                # For other cases, create well-formatted queries from description
                elif len(desc) > 100:
                    # Try to extract complete sentences or create well-formed queries
                    words = desc.split()
                    if len(words) >= 15:
                        # Look for complete sentences (ending with period, exclamation, or question mark)
                        sentences = []
                        current_sentence = []
                        
                        for word in words:
                            current_sentence.append(word)
                            # Check if sentence ends
                            if word.endswith('.') or word.endswith('!') or word.endswith('?'):
                                sentence = ' '.join(current_sentence)
                                if 20 <= len(sentence) <= 150:  # Reasonable sentence length
                                    sentences.append(sentence)
                                current_sentence = []
                        
                        # If we found complete sentences, use them
                        if sentences:
                            for sentence in sentences[:2]:  # Use up to 2 sentences
                                # Clean up the sentence
                                sentence = sentence.strip()
                                sentence = sentence.replace('\n', ' ').replace('\r', ' ')
                                sentence = ' '.join(sentence.split())
                                
                                # Remove duplicate consecutive words (case-insensitive)
                                words = sentence.split()
                                cleaned_words = []
                                prev_word = None
                                for word in words:
                                    if word.lower() != prev_word:
                                        cleaned_words.append(word)
                                        prev_word = word.lower()
                                sentence = ' '.join(cleaned_words)
                                
                                # Filter out sentences that start with incomplete fragments
                                first_words_lower = ' '.join(sentence.split()[:3]).lower()
                                if any(fragment in first_words_lower for fragment in ['u/s', 'dated', 'fir no', 'section', '10/2022', '324/2019']):
                                    # Skip if sentence starts with these fragments
                                    continue
                                
                                # Filter out sentences that are too short or contain too many numbers/abbreviations
                                if len(sentence) < 30:
                                    continue
                                
                                # Count numbers and abbreviations (like "u/s", "ppc", "fir")
                                num_count = sum(1 for word in sentence.split() if any(c.isdigit() for c in word))
                                abbrev_count = sum(1 for word in sentence.lower().split() if word in ['u/s', 'ppc', 'fir', 'sb', 'db', 'etc', 'vs', '-vs-'])
                                if num_count > 3 or abbrev_count > 4:  # Too many numbers/abbreviations
                                    continue
                                
                                # Check if sentence looks complete (has verbs, not just fragments)
                                has_verb = any(word.lower() in ['seeks', 'challenges', 'files', 'against', 'petition', 'application', 
                                                                 'was', 'is', 'are', 'has', 'have', 'had', 'filed', 'sought', 
                                                                 'granted', 'rejected', 'allowed', 'dismissed', 'imposed', 'recalled',
                                                                 'set', 'refused', 'sought', 'transfer', 'filed'] for word in words)
                                if not has_verb and len(words) < 8:
                                    continue
                                
                                # Remove trailing incomplete fragments (like "dated", "u/s", etc. at the end)
                                words_list = sentence.split()
                                # Remove trailing incomplete words
                                while words_list and words_list[-1].lower() in ['dated', 'u/s', 'fir', 'no.', 'section', 'under', 'no', 'in', 'etc']:
                                    words_list.pop()
                                    if not words_list:
                                        break
                                
                                if not words_list or len(words_list) < 5:
                                    continue
                                
                                sentence = ' '.join(words_list)
                                
                                # Remove trailing punctuation if it's incomplete
                                if sentence.lower().endswith(('dated', 'u/s', 'fir', 'no.', 'section', 'under')):
                                    continue
                                
                                # Create well-formed query
                                if sentence.lower().endswith('.'):
                                    sentence = sentence[:-1].strip()  # Remove period
                                
                                # Convert to lowercase first, then capitalize first letter after "where"
                                sentence_lower = sentence.lower()
                                query = f"Case where {sentence_lower}"
                                
                                # Capitalize first letter after "where" (but avoid creating duplicates)
                                if len(query) > 12:
                                    query = query[:11] + query[11].upper() + query[12:]
                                
                                # Remove any remaining duplicate words (case-insensitive) in final query
                                query_words = query.split()
                                final_words = []
                                prev = None
                                for w in query_words:
                                    # Remove punctuation for comparison but keep it in the word
                                    w_clean = w.lower().rstrip('.,!?:;')
                                    if w_clean != prev:
                                        final_words.append(w)
                                        prev = w_clean
                                query = ' '.join(final_words)
                                
                                # Also check for non-consecutive duplicates (like "petition Petition:")
                                words_lower = [w.lower().rstrip('.,!?:;') for w in query.split()]
                                seen_words = set()
                                final_words_clean = []
                                for i, w in enumerate(query.split()):
                                    w_clean = w.lower().rstrip('.,!?:;')
                                    if w_clean not in seen_words or i == 0:  # Always keep first occurrence
                                        final_words_clean.append(w)
                                        seen_words.add(w_clean)
                                    # If duplicate, skip it
                                query = ' '.join(final_words_clean)
                                
                                # Final validation: filter out incomplete queries
                                query_lower = query.lower()
                                
                                # Check for unclosed parentheses
                                if query.count('(') > query.count(')'):
                                    continue
                                
                                # Remove trailing commas
                                query = query.rstrip(',')
                                
                                # Filter out queries ending with incomplete words
                                incomplete_endings = ['his', 'has', 'against', 'by', 'the', 'a', 'an', 'in', 'on', 'at', 'for', 'to', 'of', 'with', 'upon', 'from', 'this', 'that', 'these', 'those']
                                last_word = query.split()[-1].lower().rstrip('.,!?')
                                if last_word in incomplete_endings:
                                    # Try to remove the last word if query is long enough
                                    words = query.split()
                                    if len(words) > 6:
                                        query = ' '.join(words[:-1])
                                    else:
                                        continue
                                
                                # Filter out queries with incomplete fragments like "[ ... ]" or starting with "]"
                                if query.strip().startswith('],') or query.strip().startswith(']'):
                                    continue
                                if '], [' in query or query.count('[') > query.count(']'):
                                    # Too many incomplete brackets
                                    continue
                                
                                # Filter out queries ending with "etc" or "u/s" or containing "u/s" followed by numbers
                                if query.lower().endswith((' etc', ' u/s', ' etc.', ' u/s.')):
                                    words = query.split()
                                    if len(words) > 6:
                                        query = ' '.join(words[:-1])
                                    else:
                                        continue
                                
                                # Remove "u/s" followed by numbers (like "u/s 540")
                                words = query.split()
                                cleaned_words = []
                                skip_next = False
                                for i, word in enumerate(words):
                                    if skip_next:
                                        skip_next = False
                                        continue
                                    if word.lower() == 'u/s' and i + 1 < len(words) and any(c.isdigit() for c in words[i + 1]):
                                        # Skip "u/s" and the following number
                                        skip_next = True
                                        continue
                                    cleaned_words.append(word)
                                query = ' '.join(cleaned_words)
                                
                                # Ensure query is still long enough after cleaning
                                if len(query.split()) < 6:
                                    continue
                                
                                # Final validation: ensure query is meaningful
                                if query.lower() not in seen_final and 40 <= len(query) <= 200 and len(query.split()) >= 6:
                                    seen_final.add(query.lower())
                                    unique_queries.append({
                                        'query': query,
                                        'relevant_case_ids': [case.id],
                                        'category': 'long_natural_language'
                                    })
                                    desc_count += 1
                                    if desc_count >= 30:
                                        break
                        
                        # If no complete sentences, try to create queries from key phrases
                        if desc_count < 30 and not sentences:
                            # Look for key patterns and create queries
                            key_patterns = [
                                ('seeks', 'Case where petitioner seeks'),
                                ('challenges', 'Case where petitioner challenges'),
                                ('files', 'Case where petitioner files'),
                                ('against', 'Case where appeal is filed against'),
                                ('petition', 'Case involving petition'),
                            ]
                            
                            for pattern, prefix in key_patterns:
                                if pattern in desc.lower():
                                    # Find the pattern and extract following context
                                    pattern_idx = desc.lower().find(pattern)
                                    # Extract 8-12 words after the pattern (shorter for better quality)
                                    context_words = desc[pattern_idx:].split()[:12]
                                    context = ' '.join(context_words)
                                    
                                    # Clean up
                                    context = context.replace('\n', ' ').replace('\r', ' ')
                                    context = ' '.join(context.split())
                                    
                                    # Remove duplicate consecutive words (case-insensitive)
                                    words = context.split()
                                    cleaned_words = []
                                    prev_word = None
                                    for word in words:
                                        if word.lower() != prev_word:
                                            cleaned_words.append(word)
                                            prev_word = word.lower()
                                    context = ' '.join(cleaned_words)
                                    
                                    # Filter out contexts that start with incomplete fragments
                                    first_words_lower = ' '.join(context.split()[:2]).lower()
                                    if any(fragment in first_words_lower for fragment in ['u/s', 'dated', 'fir no', 'section', '10/2022']):
                                        continue
                                    
                                    # Remove trailing incomplete fragments
                                    words_list = context.split()
                                    while words_list and words_list[-1].lower() in ['dated', 'u/s', 'fir', 'no.', 'section', 'under', 'no', 'in', 'etc', 'application', 'against', 'by', 'has']:
                                        words_list.pop()
                                        if not words_list:
                                            break
                                    
                                    if not words_list or len(words_list) < 5:
                                        continue
                                    
                                    context = ' '.join(words_list)
                                    
                                    # Remove trailing punctuation if incomplete
                                    if context and not context[-1] in '.!?':
                                        # Try to end at a word boundary
                                        last_space = context.rfind(' ')
                                        if last_space > len(context) * 0.7:  # If we have most of the context
                                            context = context[:last_space]
                                    
                                    # Ensure context is meaningful and doesn't have too many numbers/abbreviations
                                    context_words = context.split()
                                    if len(context_words) < 5:
                                        continue
                                    
                                    num_count = sum(1 for word in context_words if any(c.isdigit() for c in word))
                                    if num_count > 2:  # Too many numbers
                                        continue
                                    
                                    # Convert to lowercase first
                                    context_lower = context.lower()
                                    query = f"{prefix} {context_lower}"
                                    
                                    # Capitalize first letter after prefix
                                    prefix_len = len(prefix)
                                    if len(query) > prefix_len + 1:
                                        query = query[:prefix_len+1] + query[prefix_len+1].upper() + query[prefix_len+2:]
                                    
                                    # Remove any remaining duplicate words (case-insensitive) in final query
                                    query_words = query.split()
                                    final_words = []
                                    prev = None
                                    for w in query_words:
                                        # Remove punctuation for comparison but keep it in the word
                                        w_clean = w.lower().rstrip('.,!?:;')
                                        if w_clean != prev:
                                            final_words.append(w)
                                            prev = w_clean
                                    query = ' '.join(final_words)
                                    
                                    # Also check for non-consecutive duplicates
                                    words_lower = [w.lower().rstrip('.,!?:;') for w in query.split()]
                                    seen_words = set()
                                    final_words_clean = []
                                    for i, w in enumerate(query.split()):
                                        w_clean = w.lower().rstrip('.,!?:;')
                                        if w_clean not in seen_words or i == 0:  # Always keep first occurrence
                                            final_words_clean.append(w)
                                            seen_words.add(w_clean)
                                    query = ' '.join(final_words_clean)
                                    
                                    # Final validation: filter out incomplete queries
                                    query_lower = query.lower()
                                    
                                    # Check for unclosed parentheses
                                    if query.count('(') > query.count(')'):
                                        continue
                                    
                                    # Remove trailing commas
                                    query = query.rstrip(',')
                                    
                                    # Filter out queries ending with incomplete words
                                    incomplete_endings = ['his', 'has', 'against', 'by', 'the', 'a', 'an', 'in', 'on', 'at', 'for', 'to', 'of', 'with', 'upon', 'from', 'this', 'that', 'these', 'those']
                                    last_word = query.split()[-1].lower().rstrip('.,!?')
                                    if last_word in incomplete_endings:
                                        # Try to remove the last word if query is long enough
                                        words = query.split()
                                        if len(words) > 6:
                                            query = ' '.join(words[:-1])
                                        else:
                                            continue
                                    
                                    # Filter out queries with incomplete fragments
                                    if query.strip().startswith('],') or query.strip().startswith(']'):
                                        continue
                                    if '], [' in query or query.count('[') > query.count(']'):
                                        continue
                                    
                                    # Filter out queries ending with "etc" or "u/s" or containing "u/s" followed by numbers
                                    if query.lower().endswith((' etc', ' u/s', ' etc.', ' u/s.')):
                                        words = query.split()
                                        if len(words) > 6:
                                            query = ' '.join(words[:-1])
                                        else:
                                            continue
                                    
                                    # Remove "u/s" followed by numbers (like "u/s 540")
                                    words = query.split()
                                    cleaned_words = []
                                    skip_next = False
                                    for i, word in enumerate(words):
                                        if skip_next:
                                            skip_next = False
                                            continue
                                        if word.lower() == 'u/s' and i + 1 < len(words) and any(c.isdigit() for c in words[i + 1]):
                                            # Skip "u/s" and the following number
                                            skip_next = True
                                            continue
                                        cleaned_words.append(word)
                                    query = ' '.join(cleaned_words)
                                    
                                    # Ensure query is still long enough after cleaning
                                    if len(query.split()) < 6:
                                        continue
                                    
                                    if query.lower() not in seen_final and 40 <= len(query) <= 200 and len(query.split()) >= 6:
                                        seen_final.add(query.lower())
                                        unique_queries.append({
                                            'query': query,
                                            'relevant_case_ids': [case.id],
                                            'category': 'long_natural_language'
                                        })
                                        desc_count += 1
                                        break
                        
                        if desc_count >= 30:
                            break
        
        # If we still don't have enough queries, generate more from case titles
        if len(unique_queries) < num_queries:
            remaining = num_queries - len(unique_queries)
            self.stdout.write(f'  Generating {remaining} additional queries from case titles...')
            
            title_count = 0
            for case in cases_list[len(unique_queries):len(unique_queries)+remaining*2]:
                if title_count >= remaining:
                    break
                    
                if case.case_title:
                    words = case.case_title.split()
                    if len(words) >= 4:
                        # Create meaningful queries from titles
                        query = ' '.join(words[:random.randint(4, 7)])
                        if query.lower() not in seen_final and len(query) > 10:
                            seen_final.add(query.lower())
                            unique_queries.append({
                                'query': query,
                                'relevant_case_ids': [case.id],
                                'category': 'short_ambiguous'
                            })
                            title_count += 1
        
        # Sample to desired number, ensuring distribution across categories
        if len(unique_queries) > num_queries:
            # Try to get balanced distribution
            category_counts = {}
            for q in unique_queries:
                cat = q.get('category', 'other')
                category_counts[cat] = category_counts.get(cat, 0) + 1
            
            # Sample proportionally
            sampled = []
            per_category = max(1, num_queries // len(category_counts))
            for category in category_counts.keys():
                category_queries = [q for q in unique_queries if q.get('category') == category]
                sampled.extend(random.sample(category_queries, min(per_category, len(category_queries))))
            
            # Fill remaining slots randomly
            remaining = num_queries - len(sampled)
            if remaining > 0:
                remaining_queries = [q for q in unique_queries if q not in sampled]
                sampled.extend(random.sample(remaining_queries, min(remaining, len(remaining_queries))))
            
            return sampled[:num_queries]
        else:
            return unique_queries[:num_queries]

    def calculate_metrics(self, results: List[Dict], total_time: float) -> Dict[str, Any]:
        """Calculate evaluation metrics including IR metrics"""
        if not results:
            return {}
        
        num_queries = len(results)
        total_results = sum(r['num_results'] for r in results)
        queries_with_results = sum(1 for r in results if r['num_results'] > 0)
        queries_without_results = num_queries - queries_with_results
        
        avg_results = total_results / num_queries if num_queries > 0 else 0
        avg_time = total_time / num_queries if num_queries > 0 else 0
        coverage = (queries_with_results / num_queries * 100) if num_queries > 0 else 0
        
        # Calculate result distribution
        result_counts = [r['num_results'] for r in results]
        max_results = max(result_counts) if result_counts else 0
        min_results = min(result_counts) if result_counts else 0
        median_results = sorted(result_counts)[len(result_counts) // 2] if result_counts else 0
        
        # Time statistics
        execution_times = [r['execution_time_ms'] for r in results]
        max_time = max(execution_times) if execution_times else 0
        min_time = min(execution_times) if execution_times else 0
        median_time = sorted(execution_times)[len(execution_times) // 2] if execution_times else 0
        
        # Query length analysis
        query_lengths = [len(r['query'].split()) for r in results]
        avg_query_length = sum(query_lengths) / len(query_lengths) if query_lengths else 0
        
        # Calculate IR metrics
        ir_metrics = self.calculate_ir_metrics(results)
        
        metrics = {
            'total_queries': num_queries,
            'total_results': total_results,
            'queries_with_results': queries_with_results,
            'queries_without_results': queries_without_results,
            'coverage_percentage': round(coverage, 2),
            'average_results_per_query': round(avg_results, 2),
            'average_execution_time_ms': round(avg_time, 2),
            'total_execution_time_ms': round(total_time, 2),
            'result_statistics': {
                'max_results': max_results,
                'min_results': min_results,
                'median_results': median_results,
            },
            'time_statistics': {
                'max_time_ms': round(max_time, 2),
                'min_time_ms': round(min_time, 2),
                'median_time_ms': round(median_time, 2),
            },
            'query_statistics': {
                'average_query_length_words': round(avg_query_length, 2),
            },
            'ir_metrics': ir_metrics
        }
        
        # Calculate category-based metrics
        metrics['category_metrics'] = self.calculate_category_metrics(results)
        
        return metrics
    
    def calculate_category_metrics(self, results: List[Dict]) -> Dict[str, Any]:
        """Calculate metrics broken down by query category"""
        if not results:
            return {}
        
        category_stats = {}
        
        # Group results by category
        for result in results:
            category = result.get('category', 'unknown')
            if category not in category_stats:
                category_stats[category] = {
                    'queries': [],
                    'total_queries': 0,
                    'queries_with_results': 0,
                    'total_results': 0,
                    'total_time': 0.0
                }
            
            category_stats[category]['queries'].append(result)
            category_stats[category]['total_queries'] += 1
            if result['num_results'] > 0:
                category_stats[category]['queries_with_results'] += 1
            category_stats[category]['total_results'] += result['num_results']
            category_stats[category]['total_time'] += result['execution_time_ms']
        
        # Calculate metrics per category
        category_metrics = {}
        for category, stats in category_stats.items():
            num_queries = stats['total_queries']
            if num_queries == 0:
                continue
            
            # Calculate IR metrics for this category
            category_ir = self.calculate_ir_metrics(stats['queries'])
            
            category_metrics[category] = {
                'total_queries': num_queries,
                'queries_with_results': stats['queries_with_results'],
                'coverage_percentage': round((stats['queries_with_results'] / num_queries * 100) if num_queries > 0 else 0, 2),
                'average_results_per_query': round(stats['total_results'] / num_queries if num_queries > 0 else 0, 2),
                'average_execution_time_ms': round(stats['total_time'] / num_queries if num_queries > 0 else 0, 2),
                'mrr': category_ir.get('mrr', 0.0),
                'ndcg_at_10': category_ir.get('ndcg_at_10', 0.0),
                'precision_at_1': category_ir.get('precision_at_k', {}).get('P@1', 0.0),
                'recall_at_1': category_ir.get('recall_at_k', {}).get('R@1', 0.0),
                'f1_at_1': category_ir.get('f1_at_k', {}).get('F1@1', 0.0)
            }
        
        return category_metrics
    
    def calculate_ir_metrics(self, results: List[Dict]) -> Dict[str, Any]:
        """Calculate Information Retrieval metrics: MRR, Precision@K, Recall@K, F1, NDCG"""
        if not results:
            return {}
        
        # Initialize metric accumulators
        reciprocal_ranks = []
        precisions_at_k = {1: [], 5: [], 10: []}
        recalls_at_k = {1: [], 5: [], 10: []}
        f1_scores_at_k = {1: [], 5: [], 10: []}
        ndcg_scores = []
        
        for result in results:
            relevant_case_ids = set(result.get('relevant_case_ids', []))
            if not relevant_case_ids:
                continue  # Skip queries without ground truth
            
            retrieved_results = result.get('results', [])
            retrieved_case_ids = [r.get('case_id') for r in retrieved_results if r.get('case_id') != 'N/A']
            
            # Calculate MRR (Mean Reciprocal Rank)
            first_relevant_rank = None
            for rank, res in enumerate(retrieved_results, 1):
                if res.get('case_id') in relevant_case_ids:
                    first_relevant_rank = rank
                    break
            
            if first_relevant_rank:
                reciprocal_ranks.append(1.0 / first_relevant_rank)
            else:
                reciprocal_ranks.append(0.0)
            
            # Calculate Precision@K, Recall@K, F1@K
            for k in [1, 5, 10]:
                top_k_results = retrieved_results[:k]
                top_k_case_ids = [r.get('case_id') for r in top_k_results if r.get('case_id') != 'N/A']
                
                # Relevant items in top K
                relevant_retrieved = len([cid for cid in top_k_case_ids if cid in relevant_case_ids])
                
                # Precision@K = relevant retrieved / K
                precision = relevant_retrieved / k if k > 0 else 0.0
                precisions_at_k[k].append(precision)
                
                # Recall@K = relevant retrieved / total relevant
                recall = relevant_retrieved / len(relevant_case_ids) if len(relevant_case_ids) > 0 else 0.0
                recalls_at_k[k].append(recall)
                
                # F1@K = 2 * (precision * recall) / (precision + recall)
                if precision + recall > 0:
                    f1 = 2 * (precision * recall) / (precision + recall)
                else:
                    f1 = 0.0
                f1_scores_at_k[k].append(f1)
            
            # Calculate NDCG@10
            ndcg = self.calculate_ndcg(retrieved_results[:10], relevant_case_ids)
            ndcg_scores.append(ndcg)
        
        # Calculate averages
        mrr = sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0
        
        avg_precision = {
            k: sum(precisions_at_k[k]) / len(precisions_at_k[k]) if precisions_at_k[k] else 0.0
            for k in [1, 5, 10]
        }
        
        avg_recall = {
            k: sum(recalls_at_k[k]) / len(recalls_at_k[k]) if recalls_at_k[k] else 0.0
            for k in [1, 5, 10]
        }
        
        avg_f1 = {
            k: sum(f1_scores_at_k[k]) / len(f1_scores_at_k[k]) if f1_scores_at_k[k] else 0.0
            for k in [1, 5, 10]
        }
        
        avg_ndcg = sum(ndcg_scores) / len(ndcg_scores) if ndcg_scores else 0.0
        
        return {
            'mrr': round(mrr, 4),
            'precision_at_k': {f'P@{k}': round(avg_precision[k], 4) for k in [1, 5, 10]},
            'recall_at_k': {f'R@{k}': round(avg_recall[k], 4) for k in [1, 5, 10]},
            'f1_at_k': {f'F1@{k}': round(avg_f1[k], 4) for k in [1, 5, 10]},
            'ndcg_at_10': round(avg_ndcg, 4),
            'queries_with_ground_truth': len(reciprocal_ranks)
        }
    
    def calculate_ndcg(self, results: List[Dict], relevant_case_ids: set, k: int = 10) -> float:
        """Calculate Normalized Discounted Cumulative Gain at K"""
        if not results or not relevant_case_ids:
            return 0.0
        
        # Calculate DCG
        dcg = 0.0
        for i, result in enumerate(results[:k], 1):
            case_id = result.get('case_id')
            if case_id in relevant_case_ids:
                # Relevance score: 1 if relevant, 0 otherwise
                relevance = 1.0
                dcg += relevance / (self._log2(i + 1))
        
        # Calculate IDCG (Ideal DCG) - all relevant items at the top
        num_relevant = min(len(relevant_case_ids), k)
        idcg = sum(1.0 / self._log2(i + 1) for i in range(1, num_relevant + 1))
        
        # NDCG = DCG / IDCG
        if idcg > 0:
            return dcg / idcg
        return 0.0
    
    def _log2(self, x: float) -> float:
        """Calculate log base 2"""
        return math.log2(x) if x > 0 else 1.0
    
    def export_to_excel(self, results: List[Dict], metrics: Dict[str, Any], output_path: str):
        """Export evaluation results to Excel with multiple sheets"""
        if not HAS_PANDAS:
            raise ImportError("pandas and openpyxl are required. Install with: pip install pandas openpyxl")
        
        # Prepare queries sheet data
        queries_data = []
        for i, result in enumerate(results, 1):
            queries_data.append({
                'Query_ID': i,
                'Query': result['query'],
                'Category': result.get('category', 'unknown'),
                'Num_Results': result['num_results'],
                'Execution_Time_ms': result['execution_time_ms'],
                'Relevant_Case_IDs': ', '.join(map(str, result.get('relevant_case_ids', []))),
                'Has_Results': 'Yes' if result['num_results'] > 0 else 'No'
            })
        
        queries_df = pd.DataFrame(queries_data)
        
        # Prepare detailed results sheet (one row per query-result pair)
        detailed_results = []
        for i, result in enumerate(results, 1):
            query = result['query']
            for rank, res in enumerate(result.get('results', []), 1):
                detailed_results.append({
                    'Query_ID': i,
                    'Query': query,
                    'Category': result.get('category', 'unknown'),
                    'Rank': rank,
                    'Case_ID': res.get('case_id', 'N/A'),
                    'Case_Number': res.get('case_number', 'N/A'),
                    'Case_Title': res.get('case_title', 'N/A'),
                    'Relevance_Score': res.get('rank', 0.0),
                    'Is_Relevant': 'Yes' if res.get('is_relevant', False) else 'No'
                })
        
        results_df = pd.DataFrame(detailed_results)
        
        # Prepare metrics sheet
        metrics_data = []
        
        # Overall metrics
        metrics_data.append({'Metric': 'Total Queries', 'Value': metrics.get('total_queries', 0)})
        metrics_data.append({'Metric': 'Total Results', 'Value': metrics.get('total_results', 0)})
        metrics_data.append({'Metric': 'Queries with Results', 'Value': metrics.get('queries_with_results', 0)})
        metrics_data.append({'Metric': 'Queries without Results', 'Value': metrics.get('queries_without_results', 0)})
        metrics_data.append({'Metric': 'Coverage Percentage', 'Value': f"{metrics.get('coverage_percentage', 0)}%"})
        metrics_data.append({'Metric': 'Average Results per Query', 'Value': metrics.get('average_results_per_query', 0)})
        metrics_data.append({'Metric': 'Average Execution Time (ms)', 'Value': metrics.get('average_execution_time_ms', 0)})
        metrics_data.append({'Metric': 'Total Execution Time (ms)', 'Value': metrics.get('total_execution_time_ms', 0)})
        
        # Result statistics
        result_stats = metrics.get('result_statistics', {})
        metrics_data.append({'Metric': 'Max Results', 'Value': result_stats.get('max_results', 0)})
        metrics_data.append({'Metric': 'Min Results', 'Value': result_stats.get('min_results', 0)})
        metrics_data.append({'Metric': 'Median Results', 'Value': result_stats.get('median_results', 0)})
        
        # Time statistics
        time_stats = metrics.get('time_statistics', {})
        metrics_data.append({'Metric': 'Max Time (ms)', 'Value': time_stats.get('max_time_ms', 0)})
        metrics_data.append({'Metric': 'Min Time (ms)', 'Value': time_stats.get('min_time_ms', 0)})
        metrics_data.append({'Metric': 'Median Time (ms)', 'Value': time_stats.get('median_time_ms', 0)})
        
        # Query statistics
        query_stats = metrics.get('query_statistics', {})
        metrics_data.append({'Metric': 'Average Query Length (words)', 'Value': query_stats.get('average_query_length_words', 0)})
        
        # IR Metrics
        ir_metrics = metrics.get('ir_metrics', {})
        if ir_metrics:
            metrics_data.append({'Metric': '--- Information Retrieval Metrics ---', 'Value': ''})
            metrics_data.append({'Metric': 'Queries with Ground Truth', 'Value': ir_metrics.get('queries_with_ground_truth', 0)})
            metrics_data.append({'Metric': 'MRR (Mean Reciprocal Rank)', 'Value': ir_metrics.get('mrr', 0.0)})
            metrics_data.append({'Metric': 'NDCG@10', 'Value': ir_metrics.get('ndcg_at_10', 0.0)})
            
            precision = ir_metrics.get('precision_at_k', {})
            for k, v in precision.items():
                metrics_data.append({'Metric': f'Precision@{k}', 'Value': v})
            
            recall = ir_metrics.get('recall_at_k', {})
            for k, v in recall.items():
                metrics_data.append({'Metric': f'Recall@{k}', 'Value': v})
            
            f1 = ir_metrics.get('f1_at_k', {})
            for k, v in f1.items():
                metrics_data.append({'Metric': f'F1@{k}', 'Value': v})
        
        # Category-based metrics
        category_metrics = metrics.get('category_metrics', {})
        if category_metrics:
            metrics_data.append({'Metric': '--- Category-Based Metrics ---', 'Value': ''})
            for category, cat_metrics in category_metrics.items():
                metrics_data.append({'Metric': f'--- {category.upper()} ---', 'Value': ''})
                metrics_data.append({'Metric': f'{category} - Total Queries', 'Value': cat_metrics.get('total_queries', 0)})
                metrics_data.append({'Metric': f'{category} - Coverage %', 'Value': f"{cat_metrics.get('coverage_percentage', 0)}%"})
                metrics_data.append({'Metric': f'{category} - Avg Results/Query', 'Value': cat_metrics.get('average_results_per_query', 0)})
                metrics_data.append({'Metric': f'{category} - MRR', 'Value': cat_metrics.get('mrr', 0.0)})
                metrics_data.append({'Metric': f'{category} - NDCG@10', 'Value': cat_metrics.get('ndcg_at_10', 0.0)})
                metrics_data.append({'Metric': f'{category} - Precision@1', 'Value': cat_metrics.get('precision_at_1', 0.0)})
                metrics_data.append({'Metric': f'{category} - Recall@1', 'Value': cat_metrics.get('recall_at_1', 0.0)})
                metrics_data.append({'Metric': f'{category} - F1@1', 'Value': cat_metrics.get('f1_at_1', 0.0)})
        
        metrics_df = pd.DataFrame(metrics_data)
        
        # Write to Excel
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            queries_df.to_excel(writer, sheet_name='Queries', index=False)
            results_df.to_excel(writer, sheet_name='Detailed Results', index=False)
            metrics_df.to_excel(writer, sheet_name='Metrics', index=False)
            
            # Auto-adjust column widths
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width

    def display_results(self, metrics: Dict[str, Any], results: List[Dict]):
        """Display evaluation results"""
        self.stdout.write('\n' + '='*80)
        self.stdout.write(self.style.SUCCESS('LEXICAL SEARCH EVALUATION RESULTS'))
        self.stdout.write('='*80 + '\n')
        
        # Overall metrics
        self.stdout.write(self.style.SUCCESS('Overall Performance:'))
        self.stdout.write(f"  Total Queries: {metrics['total_queries']}")
        self.stdout.write(f"  Total Results: {metrics['total_results']}")
        self.stdout.write(f"  Coverage: {metrics['coverage_percentage']}% ({metrics['queries_with_results']} queries returned results)")
        self.stdout.write(f"  Average Results per Query: {metrics['average_results_per_query']}")
        self.stdout.write(f"  Average Execution Time: {metrics['average_execution_time_ms']} ms")
        self.stdout.write(f"  Total Execution Time: {metrics['total_execution_time_ms']} ms")
        
        # Result statistics
        self.stdout.write('\n' + self.style.SUCCESS('Result Statistics:'))
        self.stdout.write(f"  Max Results: {metrics['result_statistics']['max_results']}")
        self.stdout.write(f"  Min Results: {metrics['result_statistics']['min_results']}")
        self.stdout.write(f"  Median Results: {metrics['result_statistics']['median_results']}")
        
        # Time statistics
        self.stdout.write('\n' + self.style.SUCCESS('Time Statistics:'))
        self.stdout.write(f"  Max Time: {metrics['time_statistics']['max_time_ms']} ms")
        self.stdout.write(f"  Min Time: {metrics['time_statistics']['min_time_ms']} ms")
        self.stdout.write(f"  Median Time: {metrics['time_statistics']['median_time_ms']} ms")
        
        # Query statistics
        self.stdout.write('\n' + self.style.SUCCESS('Query Statistics:'))
        self.stdout.write(f"  Average Query Length: {metrics['query_statistics']['average_query_length_words']} words")
        
        # IR Metrics
        if 'ir_metrics' in metrics:
            ir = metrics['ir_metrics']
            self.stdout.write('\n' + self.style.SUCCESS('Information Retrieval Metrics:'))
            self.stdout.write(f"  Queries with Ground Truth: {ir.get('queries_with_ground_truth', 0)}")
            self.stdout.write(f"  MRR (Mean Reciprocal Rank): {ir.get('mrr', 0.0):.4f}")
            self.stdout.write(f"  NDCG@10: {ir.get('ndcg_at_10', 0.0):.4f}")
            self.stdout.write('\n  Precision@K:')
            for k, val in ir.get('precision_at_k', {}).items():
                self.stdout.write(f"    {k}: {val:.4f}")
            self.stdout.write('\n  Recall@K:')
            for k, val in ir.get('recall_at_k', {}).items():
                self.stdout.write(f"    {k}: {val:.4f}")
            self.stdout.write('\n  F1 Score@K:')
            for k, val in ir.get('f1_at_k', {}).items():
                self.stdout.write(f"    {k}: {val:.4f}")
        
        # Category-based metrics
        if 'category_metrics' in metrics:
            self.stdout.write('\n' + self.style.SUCCESS('Category-Based Performance:'))
            self.stdout.write('-'*80)
            for category, cat_metrics in metrics['category_metrics'].items():
                self.stdout.write(f"\n{category.upper().replace('_', ' ')}:")
                self.stdout.write(f"  Queries: {cat_metrics.get('total_queries', 0)}")
                self.stdout.write(f"  Coverage: {cat_metrics.get('coverage_percentage', 0)}%")
                self.stdout.write(f"  MRR: {cat_metrics.get('mrr', 0.0):.4f}")
                self.stdout.write(f"  NDCG@10: {cat_metrics.get('ndcg_at_10', 0.0):.4f}")
                self.stdout.write(f"  Precision@1: {cat_metrics.get('precision_at_1', 0.0):.4f}")
                self.stdout.write(f"  Recall@1: {cat_metrics.get('recall_at_1', 0.0):.4f}")
        
        # Sample queries
        self.stdout.write('\n' + self.style.SUCCESS('Sample Query Results:'))
        self.stdout.write('-'*80)
        
        # Show top 10 queries by result count
        sorted_results = sorted(results, key=lambda x: x['num_results'], reverse=True)[:10]
        for i, result in enumerate(sorted_results, 1):
            self.stdout.write(f"\n{i}. Query: \"{result['query']}\"")
            self.stdout.write(f"   Results: {result['num_results']}, Time: {result['execution_time_ms']} ms")
            if result['results']:
                self.stdout.write(f"   Top Result: {result['results'][0]['case_number']}")
        
        # Show queries with no results
        no_result_queries = [r for r in results if r['num_results'] == 0]
        if no_result_queries:
            self.stdout.write('\n' + self.style.WARNING(f'Queries with No Results ({len(no_result_queries)}):'))
            for i, result in enumerate(no_result_queries[:10], 1):
                self.stdout.write(f"  {i}. \"{result['query']}\"")
            if len(no_result_queries) > 10:
                self.stdout.write(f"  ... and {len(no_result_queries) - 10} more")
        
        self.stdout.write('\n' + '='*80)

