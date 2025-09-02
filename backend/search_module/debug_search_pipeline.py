#!/usr/bin/env python3
"""
Debug Search Pipeline
Trace through the entire search pipeline to see where it's failing
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from search_indexing.views import SearchAPIView
from search_indexing.services.hybrid_indexing import HybridIndexingService
from search_indexing.services.keyword_indexing import KeywordIndexingService
from search_indexing.services.vector_indexing import VectorIndexingService
from django.test import RequestFactory

def debug_search_pipeline():
    """Debug the entire search pipeline"""
    print("🔍 DEBUGGING SEARCH PIPELINE")
    print("=" * 60)
    
    test_query = "Chief"
    print(f"📝 Testing query: '{test_query}'")
    
    try:
        # Test 1: Direct service calls
        print(f"\n🔍 TEST 1: Direct Service Calls")
        print("-" * 40)
        
        # Test keyword service
        print(f"\n   Keyword Service:")
        try:
            keyword_service = KeywordIndexingService()
            keyword_results = keyword_service.search(test_query, top_k=5)
            print(f"      Results: {len(keyword_results)}")
            if keyword_results:
                print(f"      First result: {keyword_results[0]}")
            else:
                print(f"      ❌ No keyword results")
        except Exception as e:
            print(f"      ❌ Keyword service error: {e}")
        
        # Test vector service
        print(f"\n   Vector Service:")
        try:
            vector_service = VectorIndexingService()
            vector_results = vector_service.search(test_query, top_k=5)
            print(f"      Results: {len(vector_results)}")
            if vector_results:
                print(f"      First result: {vector_results[0]}")
            else:
                print(f"      ❌ No vector results")
        except Exception as e:
            print(f"      ❌ Vector service error: {e}")
        
        # Test hybrid service
        print(f"\n   Hybrid Service:")
        try:
            hybrid_service = HybridIndexingService(use_pinecone=True)
            hybrid_results = hybrid_service.hybrid_search(test_query, top_k=5)
            print(f"      Results: {len(hybrid_results)}")
            if hybrid_results:
                print(f"      First result: {hybrid_results[0]}")
            else:
                print(f"      ❌ No hybrid results")
        except Exception as e:
            print(f"      ❌ Hybrid service error: {e}")
        
        # Test 2: View pipeline
        print(f"\n🔍 TEST 2: View Pipeline")
        print("-" * 40)
        
        try:
            # Create a mock request
            factory = RequestFactory()
            request = factory.get(f'/api/search/search/?q={test_query}&mode=hybrid&limit=5')
            
            # Create the view instance
            view = SearchAPIView()
            
            # Parse parameters
            params = view._parse_search_params(request)
            print(f"   Parsed parameters: {params}")
            
            # Normalize query
            query_info = view.query_normalizer.normalize_query(params['query'])
            print(f"   Query info: {query_info}")
            
            # Perform hybrid search
            print(f"\n   Performing hybrid search...")
            search_results = view._perform_hybrid_search(params, query_info)
            print(f"   Search results structure:")
            print(f"      Vector results: {len(search_results.get('vector_results', []))}")
            print(f"      Keyword results: {len(search_results.get('keyword_results', []))}")
            
            if search_results.get('vector_results'):
                print(f"      First vector result: {search_results['vector_results'][0]}")
            if search_results.get('keyword_results'):
                print(f"      First keyword result: {search_results['keyword_results'][0]}")
            
            # Apply ranking
            print(f"\n   Applying ranking...")
            ranked_results = view.ranking_service.rank_results(
                search_results.get('vector_results', []),
                search_results.get('keyword_results', []),
                params['query'],
                None,
                params.get('filters')
            )
            print(f"   Ranked results: {len(ranked_results)}")
            
            if ranked_results:
                print(f"      First ranked result: {ranked_results[0]}")
            else:
                print(f"      ❌ No ranked results")
                
        except Exception as e:
            print(f"   ❌ View pipeline error: {e}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_search_pipeline()
