#!/usr/bin/env python3
"""
Debug Hybrid Search
See exactly what data is being returned and why scores are 0
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from search_indexing.services.hybrid_indexing import HybridIndexingService

def debug_hybrid_search():
    """Debug what hybrid search is actually returning"""
    print("🔍 DEBUGGING HYBRID SEARCH")
    print("=" * 60)
    
    try:
        # Initialize hybrid service
        hybrid_service = HybridIndexingService(use_pinecone=True)
        print("✅ Hybrid service initialized")
        
        # Test query
        test_query = "PPC 302"
        print(f"\n📝 Testing query: '{test_query}'")
        
        # Perform hybrid search
        print("\n🔄 Performing hybrid search...")
        hybrid_results = hybrid_service.hybrid_search(test_query, top_k=5)
        
        print(f"\n📊 Hybrid search returned {len(hybrid_results)} results")
        
        if hybrid_results:
            print("\n🔍 First result structure:")
            first_result = hybrid_results[0]
            for key, value in first_result.items():
                print(f"   {key}: {value} (type: {type(value)})")
            
            print("\n🔍 All results summary:")
            for i, result in enumerate(hybrid_results):
                print(f"\n   Result {i+1}:")
                print(f"      Case ID: {result.get('case_id', 'N/A')}")
                print(f"      Case Number: {result.get('case_number', 'N/A')}")
                print(f"      Vector Score: {result.get('vector_score', 'N/A')}")
                print(f"      Keyword Score: {result.get('keyword_score', 'N/A')}")
                print(f"      Combined Score: {result.get('combined_score', 'N/A')}")
                print(f"      Final Score: {result.get('final_score', 'N/A')}")
                print(f"      Search Type: {result.get('search_type', 'N/A')}")
        else:
            print("❌ No results returned")
        
        # Check what the individual services return
        print(f"\n🔍 Checking individual services...")
        
        # Vector service
        print("\n   Vector Service:")
        try:
            vector_results = hybrid_service.vector_service.search(test_query, top_k=3)
            print(f"      Vector results: {len(vector_results)}")
            if vector_results:
                print(f"      First vector result: {vector_results[0]}")
        except Exception as e:
            print(f"      Vector service error: {e}")
        
        # Keyword service
        print("\n   Keyword Service:")
        try:
            keyword_results = hybrid_service.keyword_service.search(test_query, top_k=3)
            print(f"      Keyword results: {len(keyword_results)}")
            if keyword_results:
                print(f"      First keyword result: {keyword_results[0]}")
        except Exception as e:
            print(f"      Keyword service error: {e}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_hybrid_search()
