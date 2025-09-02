#!/usr/bin/env python3
"""
Test Simple Search
Check why the search is returning 0 results
"""

import requests
import json
from urllib.parse import urlencode

# Configuration
BASE_URL = "http://localhost:8000/api/search"

def test_simple_search():
    """Test simple search to see why it's returning 0 results"""
    print("🔍 TESTING SIMPLE SEARCH")
    print("=" * 60)
    
    # Test queries that should definitely return results
    test_queries = [
        "Chief",           # Should find judge-related cases
        "CPC",            # Should find CPC-related cases
        "CrPC",           # Should find CrPC-related cases
        "2025",           # Should find recent cases
        "Appeal",         # Should find appeal cases
    ]
    
    for query in test_queries:
        print(f"\n📝 Testing query: '{query}'")
        print("-" * 40)
        
        # Test hybrid search
        try:
            params = {
                'q': query,
                'mode': 'hybrid',
                'limit': 5,
                'return_facets': 'false',
                'highlight': 'false'
            }
            
            response = requests.get(
                f"{BASE_URL}/search/",
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                total_results = data.get('search_metadata', {}).get('total_results', 0)
                results = data.get('results', [])
                latency = data.get('search_metadata', {}).get('latency_ms', 0)
                
                print(f"✅ Status: {response.status_code}")
                print(f"📊 Total Results: {total_results}")
                print(f"📄 Results Returned: {len(results)}")
                print(f"⚡ Latency: {latency}ms")
                
                if results:
                    print(f"\n🔍 First Result:")
                    first_result = results[0]
                    for key, value in first_result.items():
                        if key in ['case_id', 'case_number', 'case_title', 'vector_score', 'keyword_score', 'final_score']:
                            print(f"   {key}: {value}")
                else:
                    print("❌ No results returned")
                    
            else:
                print(f"❌ Search failed: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Response: {response.text[:200]}")
                
        except Exception as e:
            print(f"❌ Search error: {e}")
        
        # Test status endpoint to see system health
        try:
            status_response = requests.get(f"{BASE_URL}/status/", timeout=10)
            if status_response.status_code == 200:
                status_data = status_response.json()
                indexes = status_data.get('indexes', {})
                print(f"\n📊 System Status:")
                vector_info = indexes.get('vector_index', {})
                keyword_info = indexes.get('keyword_index', {})
                facet_info = indexes.get('facet_indexes', {})
                metadata_info = indexes.get('search_metadata', {})
                
                print(f"   Vector Index: {'✅ Built' if vector_info.get('is_built') else '❌ Not Built'} ({vector_info.get('total_vectors', 0)} vectors)")
                print(f"   Keyword Index: {'✅ Built' if keyword_info.get('is_built') else '❌ Not Built'} ({keyword_info.get('total_documents', 0)} documents)")
                print(f"   Facet Indexes: {'✅ Built' if facet_info.get('built', 0) > 0 else '❌ Not Built'} ({facet_info.get('built', 0)}/{facet_info.get('total', 0)})")
                print(f"   Search Metadata: {'✅ Built' if metadata_info.get('is_built') else '❌ Not Built'} ({metadata_info.get('indexed_records', 0)} records)")
        except Exception as e:
            print(f"❌ Status check error: {e}")

if __name__ == "__main__":
    test_simple_search()
