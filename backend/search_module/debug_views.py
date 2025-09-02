#!/usr/bin/env python3
"""
Debug Views
See exactly what data the views are receiving and processing
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from search_indexing.views import SearchAPIView
from django.test import RequestFactory

def debug_views():
    """Debug what the views are receiving and processing"""
    print("🔍 DEBUGGING VIEWS")
    print("=" * 60)
    
    try:
        # Create a mock request
        factory = RequestFactory()
        request = factory.get('/api/search/search/?q=PPC%20302&mode=hybrid&limit=5')
        
        # Create the view instance
        view = SearchAPIView()
        
        # Parse parameters
        params = view._parse_search_params(request)
        print(f"📝 Parsed parameters: {params}")
        
        # Normalize query
        query_info = view.query_normalizer.normalize_query(params['query'])
        print(f"📝 Query info: {query_info}")
        
        # Perform hybrid search
        print(f"\n🔄 Performing hybrid search...")
        search_results = view._perform_hybrid_search(params, query_info)
        
        print(f"\n📊 Search results structure:")
        print(f"   Vector results: {len(search_results.get('vector_results', []))}")
        print(f"   Keyword results: {len(search_results.get('keyword_results', []))}")
        
        if search_results.get('vector_results'):
            print(f"\n🔍 First vector result:")
            first_vector = search_results['vector_results'][0]
            for key, value in first_vector.items():
                print(f"      {key}: {value}")
        
        if search_results.get('keyword_results'):
            print(f"\n🔍 First keyword result:")
            first_keyword = search_results['keyword_results'][0]
            for key, value in first_keyword.items():
                print(f"      {key}: {value}")
        
        # Apply ranking
        print(f"\n🔄 Applying ranking...")
        ranked_results = view.ranking_service.rank_results(
            search_results.get('vector_results', []),
            search_results.get('keyword_results', []),
            query_info,
            params.get('filters'),
            params['limit']
        )
        
        print(f"\n📊 Ranked results: {len(ranked_results)}")
        
        if ranked_results:
            print(f"\n🔍 First ranked result:")
            first_ranked = ranked_results[0]
            for key, value in first_ranked.items():
                print(f"      {key}: {value}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_views()
