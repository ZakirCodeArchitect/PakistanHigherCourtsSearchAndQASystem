"""
Test script to verify basic search functionality (without BM25)
This tests the original icontains-based search that was used before BM25
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from search_indexing.services.keyword_indexing import KeywordIndexingService

def test_basic_search():
    """Test basic search functionality without BM25"""
    print("=" * 80)
    print("ORIGINAL SEARCH FUNCTIONALITY TEST (Without BM25)")
    print("=" * 80)
    
    # Initialize service without BM25
    print("\n1. Initializing KeywordIndexingService (use_bm25=False)...")
    try:
        service = KeywordIndexingService(use_bm25=False)
        print("   [OK] Service initialized successfully")
    except Exception as e:
        print(f"   [ERROR] Failed to initialize service: {e}")
        return False
    
    # Test queries (simple queries that should work with icontains)
    test_queries = [
        "service matter",
        "PPC 302",
        "writ petition",
        "tax appeal",
        "criminal case"
    ]
    
    print("\n2. Testing basic search queries...")
    all_passed = True
    
    for i, query in enumerate(test_queries, 1):
        try:
            results = service.search(query, top_k=5)
            if results:
                print(f"   [OK] Query {i}: '{query}' - Found {len(results)} results")
                print(f"     Top result: {results[0].get('case_number', 'N/A')} - {results[0].get('title', 'N/A')[:50]}")
            else:
                print(f"   [WARN] Query {i}: '{query}' - No results found")
        except Exception as e:
            print(f"   [ERROR] Query {i}: '{query}' - Error: {e}")
            all_passed = False
    
    # Test exact case number search
    print("\n3. Testing exact case number search...")
    try:
        results = service.search("W.P. 1/2016", top_k=3)
        if results:
            print(f"   [OK] Exact case number search - Found {len(results)} results")
            print(f"     Top result: {results[0].get('case_number', 'N/A')}")
        else:
            print(f"   [WARN] Exact case number search - No results found")
    except Exception as e:
        print(f"   [ERROR] Exact case number search - Error: {e}")
        all_passed = False
    
    # Test party name search
    print("\n4. Testing party name search...")
    try:
        results = service.search("The State", top_k=3)
        if results:
            print(f"   [OK] Party name search - Found {len(results)} results")
            print(f"     Top result: {results[0].get('case_number', 'N/A')}")
        else:
            print(f"   [WARN] Party name search - No results found")
    except Exception as e:
        print(f"   [ERROR] Party name search - Error: {e}")
        all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("[SUCCESS] ALL TESTS PASSED - Original search functionality is working")
    else:
        print("[WARNING] SOME TESTS FAILED - Check errors above")
    print("=" * 80)
    
    return all_passed

if __name__ == '__main__':
    success = test_basic_search()
    sys.exit(0 if success else 1)

