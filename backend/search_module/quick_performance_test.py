#!/usr/bin/env python3
"""
Quick Performance Test for Search API
Tests a few queries with detailed timing and performance analysis
"""

import requests
import json
import time
from urllib.parse import urlencode
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000/api/search"

# Simple test queries
SIMPLE_QUERIES = [
    "PPC 302",
    "OGRA",
    "2025",
    "Application"
]

def test_single_query(query, mode='hybrid', limit=10):
    """Test a single query with detailed timing"""
    print(f"\n🔍 Testing: '{query}' (Mode: {mode}, Limit: {limit})")
    print("-" * 60)
    
    params = {
        'q': query,
        'mode': mode,
        'limit': limit,
        'return_facets': 'false',  # Disable facets for faster response
        'highlight': 'false'       # Disable highlighting for faster response
    }
    
    url = f"{BASE_URL}/search/?{urlencode(params)}"
    
    try:
        print(f"🌐 Request URL: {url}")
        print(f"⏱️  Starting request...")
        
        start_time = time.time()
        response = requests.get(url, timeout=30)  # 30 second timeout
        request_time = time.time() - start_time
        
        print(f"⏱️  Request completed in {request_time:.2f} seconds")
        
        if response.status_code == 200:
            data = response.json()
            
            # Basic info
            total_results = data.get('search_metadata', {}).get('total_results', 0)
            latency = data.get('search_metadata', {}).get('latency_ms', 0)
            
            print(f"✅ Status: 200 OK")
            print(f"📊 Total Results: {total_results}")
            print(f"⚡ API Latency: {latency:.2f}ms")
            print(f"🌐 Total Request Time: {request_time:.2f}s")
            
            # Show results
            results = data.get('results', [])
            if results:
                print(f"\n📋 RESULTS ({len(results)} found):")
                for i, result in enumerate(results, 1):
                    result_data = result.get('result_data', {})
                    case_number = result_data.get('case_number', 'N/A')
                    case_title = result_data.get('case_title', 'N/A')
                    final_score = result.get('final_score', 0)
                    
                    print(f"   {i:2d}. {case_number} - {case_title[:50]}... (Score: {final_score:.4f})")
            else:
                print("   No results found")
                
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            
    except requests.exceptions.Timeout:
        print(f"❌ TIMEOUT: Request took longer than 30 seconds")
    except requests.exceptions.ConnectionError:
        print(f"❌ CONNECTION ERROR: Could not connect to server")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def test_status_quick():
    """Quick status check"""
    print(f"\n📊 QUICK STATUS CHECK")
    print("-" * 40)
    
    url = f"{BASE_URL}/status/"
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            status = data.get('status', 'unknown')
            print(f"✅ System Status: {status}")
            
            # Check indexes
            indexes = data.get('indexes', {})
            if indexes:
                print("📊 Index Status:")
                for index_type, status in indexes.items():
                    if isinstance(status, dict):
                        is_built = status.get('is_built', False)
                        print(f"   {index_type}: {'✅ Built' if is_built else '❌ Not Built'}")
                    else:
                        print(f"   {index_type}: {status}")
        else:
            print(f"❌ Status Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Status check failed: {e}")

def test_simple_search():
    """Test simple search functionality"""
    print("🚀 QUICK PERFORMANCE TEST")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # First check status
    test_status_quick()
    
    # Test each query
    for query in SIMPLE_QUERIES:
        test_single_query(query, mode='hybrid', limit=5)
        time.sleep(1)  # Be nice to the server
    
    print(f"\n{'='*60}")
    print("✅ Quick performance test completed!")
    print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    test_simple_search()
