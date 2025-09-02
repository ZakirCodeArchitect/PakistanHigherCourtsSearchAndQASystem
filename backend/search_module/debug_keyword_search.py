#!/usr/bin/env python3
"""
Debug Keyword Search
Trace through the keyword search logic to see why content search isn't working
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from search_indexing.services.keyword_indexing import KeywordIndexingService
from search_indexing.models import SearchMetadata, DocumentChunk
from django.db.models import Q

def debug_keyword_search():
    """Debug the keyword search step by step"""
    print("🔍 DEBUGGING KEYWORD SEARCH")
    print("=" * 60)
    
    test_queries = ["CPC", "CrPC", "2025"]
    
    for query in test_queries:
        print(f"\n📝 Testing query: '{query}'")
        print("-" * 40)
        
        try:
            # Initialize service
            keyword_service = KeywordIndexingService()
            
            # Normalize query
            normalized_query = keyword_service.normalize_text(query)
            print(f"   Normalized query: '{normalized_query}'")
            
            # Build search query
            from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
            search_vector = (
                SearchVector('case_number_normalized', weight='A') +
                SearchVector('case_title_normalized', weight='B') +
                SearchVector('parties_normalized', weight='C') +
                SearchVector('court_normalized', weight='D')
            )
            
            search_query = SearchQuery(normalized_query, config='english')
            
            # Get base queryset
            queryset = SearchMetadata.objects.filter(is_indexed=True)
            print(f"   Base queryset count: {queryset.count()}")
            
            # Test PostgreSQL search
            results = queryset.annotate(
                rank=SearchRank(search_vector, search_query)
            ).order_by('-rank')[:10]
            
            print(f"   PostgreSQL search results: {len(results)}")
            if results:
                print(f"   First result rank: {results[0].rank}")
                print(f"   Last result rank: {results[results.count()-1].rank if results.count() > 0 else 'N/A'}")
            
            # Check if we need partial matching
            if not results or all(r.rank < 0.001 for r in results):
                print(f"   ✅ Need partial matching (ranks too low)")
                
                # Split query into terms
                query_terms = normalized_query.split()
                print(f"   Query terms: {query_terms}")
                
                partial_results = []
                
                for term in query_terms:
                    if len(term) >= 2:
                        print(f"\n   🔍 Processing term: '{term}'")
                        
                        # Try metadata matching
                        term_results = queryset.filter(
                            Q(case_number_normalized__icontains=term) |
                            Q(case_title_normalized__icontains=term) |
                            Q(parties_normalized__icontains=term)
                        )[:5]
                        
                        print(f"      Metadata matches: {term_results.count()}")
                        
                        for result in term_results:
                            score = 0
                            if term.lower() in result.case_number_normalized.lower():
                                score += 10
                            if term.lower() in result.case_title_normalized.lower():
                                score += 5
                            if term.lower() in result.parties_normalized.lower():
                                score += 3
                            
                            if score > 0:
                                partial_results.append({
                                    'result': result,
                                    'score': score,
                                    'matched_term': term
                                })
                                print(f"      Added metadata result: case {result.case_id}, score {score}")
                        
                        # Try content search
                        content_matches = DocumentChunk.objects.filter(
                            chunk_text__icontains=term,
                            is_embedded=True
                        ).values('case_id').distinct()[:5]
                        
                        print(f"      Content matches: {content_matches.count()}")
                        
                        for match in content_matches:
                            case_id = match['case_id']
                            case_metadata = queryset.filter(case_id=case_id).first()
                            
                            if case_metadata:
                                content_score = 2
                                
                                # Check if already exists
                                existing_result = next((item for item in partial_results if item['result'].case_id == case_id), None)
                                if existing_result:
                                    existing_result['score'] += content_score
                                    print(f"      Boosted existing result: case {case_id}, new score {existing_result['score']}")
                                else:
                                    partial_results.append({
                                        'result': case_metadata,
                                        'score': content_score,
                                        'matched_term': term
                                    })
                                    print(f"      Added content result: case {case_id}, score {content_score}")
                
                print(f"\n   📊 Partial results summary:")
                print(f"      Total partial results: {len(partial_results)}")
                
                # Sort by score
                partial_results.sort(key=lambda x: x['score'], reverse=True)
                
                for i, item in enumerate(partial_results[:5]):
                    print(f"      {i+1}. Case {item['result'].case_id}: score {item['score']} (matched: {item['matched_term']})")
                
                # Take top results
                final_results = [item['result'] for item in partial_results[:5]]
                print(f"      Final results count: {len(final_results)}")
                
                # Add rank field
                for result in final_results:
                    result.rank = 0.1
                
            else:
                print(f"   ❌ PostgreSQL search worked, no partial matching needed")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug_keyword_search()
