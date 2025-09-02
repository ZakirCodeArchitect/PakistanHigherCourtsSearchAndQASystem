#!/usr/bin/env python3
"""
Test Script for Search API
Tests the main search endpoints to ensure they're working correctly
"""

import requests
import json
import time
from urllib.parse import urlencode

# Configuration
BASE_URL = "http://localhost:8000/api/search"
TEST_QUERIES = [
    "PPC 302",
    "CrPC 497",
    "Application 2/2025",
    "constitutional petition",
    "habeas corpus",
    "mandamus writ"
]

def test_search_endpoint():
    """Test the main search endpoint"""
    print("🔍 Testing Search Endpoint...")
    
    for query in TEST_QUERIES:
        print(f"\n📝 Testing query: '{query}'")
        
        # Test hybrid search
        params = {
            'q': query,
            'mode': 'hybrid',
            'limit': 5,
            'return_facets': 'true',
            'highlight': 'true'
        }
        
        url = f"{BASE_URL}/search/?{urlencode(params)}"
        
        try:
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                total_results = data.get('search_metadata', {}).get('total_results', 0)
                print(f"✅ Success! Found {total_results} results")
                print(f"   Latency: {data.get('search_metadata', {}).get('latency_ms', 0)}ms")
                
                # Show first result
                if data.get('results'):
                    first_result = data['results'][0]
                    result_data = first_result.get('result_data', {})
                    case_number = result_data.get('case_number', 'N/A')
                    case_title = result_data.get('case_title', 'N/A')
                    print(f"   Top result: {case_number} - {case_title[:50]}...")
                
                # Show facets if available
                if data.get('facets'):
                    facet_keys = list(data['facets'].keys())
                    non_empty_facets = [key for key, value in data['facets'].items() if value and len(value) > 0]
                    print(f"   Facets: {facet_keys} (Non-empty: {non_empty_facets})")
                
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
        
        time.sleep(1)  # Be nice to the server

def test_suggest_endpoint():
    """Test the suggestions endpoint"""
    print("\n💡 Testing Suggestions Endpoint...")
    
    test_suggestions = ["PPC", "CrPC", "Application", "Petition"]
    
    for term in test_suggestions:
        print(f"\n🔤 Testing suggestions for: '{term}'")
        
        params = {
            'q': term,
            'type': 'auto'
        }
        
        url = f"{BASE_URL}/suggest/?{urlencode(params)}"
        
        try:
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                suggestions = data.get('suggestions', [])
                print(f"✅ Success! Found {len(suggestions)} suggestions")
                
                for i, suggestion in enumerate(suggestions[:3]):  # Show top 3
                    print(f"   {i+1}. {suggestion.get('value', 'N/A')} ({suggestion.get('type', 'N/A')})")
                    
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
        
        time.sleep(1)

def test_status_endpoint():
    """Test the status endpoint"""
    print("\n📊 Testing Status Endpoint...")
    
    url = f"{BASE_URL}/status/"
    
    try:
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! System status: {data.get('status', 'unknown')}")
            
            # Show index information
            indexes = data.get('indexes', {})
            if indexes:
                print("   Index Status:")
                for index_type, status in indexes.items():
                    if isinstance(status, dict):
                        if index_type == 'facet_indexes':
                            total = status.get('total', 0)
                            built = status.get('built', 0)
                            print(f"     {index_type}: {'✅ Built' if built > 0 else '❌ Not Built'} ({built}/{total})")
                        elif index_type == 'search_metadata':
                            total = status.get('total_records', 0)
                            indexed = status.get('indexed_records', 0)
                            is_built = status.get('is_built', False)
                            print(f"     {index_type}: {'✅ Built' if is_built else '❌ Not Built'} ({indexed}/{total})")
                        else:
                            print(f"     {index_type}: {'✅ Built' if status.get('is_built') else '❌ Not Built'}")
                    else:
                        print(f"     {index_type}: {status}")
            
            # Show health metrics
            health = data.get('health', {})
            if health:
                print("   Health Metrics:")
                print(f"     Database: {'✅ Healthy' if health.get('database', {}).get('healthy') else '❌ Unhealthy'}")
                print(f"     Index Coverage: {health.get('indexing', {}).get('coverage_percentage', 0)}%")
                
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")

def test_case_context_endpoint():
    """Test the case context endpoint"""
    print("\n📄 Testing Case Context Endpoint...")
    
    # First, we need to get a case ID from search
    params = {
        'q': 'PPC 302',
        'mode': 'hybrid',
        'limit': 1
    }
    
    url = f"{BASE_URL}/search/?{urlencode(params)}"
    
    try:
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            
            if results:
                case_id = results[0].get('case_id')
                print(f"✅ Found case ID: {case_id}")
                
                # Now test the context endpoint
                context_url = f"{BASE_URL}/case/{case_id}/contexts/"
                context_response = requests.get(context_url, timeout=30)
                
                if context_response.status_code == 200:
                    context_data = context_response.json()
                    print(f"✅ Context retrieved successfully!")
                    print(f"   Chunks: {len(context_data.get('chunks', []))}")
                    print(f"   Terms: {len(context_data.get('terms', []))}")
                    
                else:
                    print(f"❌ Context error: {context_response.status_code} - {context_response.text}")
            else:
                print("❌ No search results to test context with")
                
        else:
            print(f"❌ Search error: {response.status_code} - {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")

def main():
    """Run all tests"""
    print("🚀 Starting Search API Tests...")
    print("=" * 50)
    
    try:
        # Test each endpoint
        test_search_endpoint()
        test_suggest_endpoint()
        test_status_endpoint()
        test_case_context_endpoint()
        
        print("\n" + "=" * 50)
        print("✅ All tests completed!")
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test suite failed: {e}")

if __name__ == "__main__":
    main()
