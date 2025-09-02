#!/usr/bin/env python3
"""
Performance Profiler for Search API
Identify bottlenecks in the search process
"""

import requests
import json
import time
from urllib.parse import urlencode
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000/api/search"

def profile_search_performance():
    """Profile search performance step by step"""
    print("🔍 PERFORMANCE PROFILING")
    print("=" * 60)
    
    # Test with a simple query first
    test_query = "PPC 302"
    
    print(f"\n📝 Testing Query: '{test_query}'")
    print("-" * 40)
    
    # Test 1: Simple search without facets or highlights
    print("\n🔍 TEST 1: Simple Search (No Facets/Highlights)")
    print("-" * 40)
    
    params = {
        'q': test_query,
        'mode': 'hybrid',
        'limit': 10,
        'return_facets': 'false',
        'highlight': 'false',
        'debug': 'false'
    }
    
    url = f"{BASE_URL}/search/?{urlencode(params)}"
    
    try:
        start_time = time.time()
        response = requests.get(url, timeout=60)  # 60 second timeout
        request_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            latency = data.get('search_metadata', {}).get('latency_ms', 0)
            total_results = data.get('search_metadata', {}).get('total_results', 0)
            
            print(f"✅ Status: 200 OK")
            print(f"📊 Total Results: {total_results}")
            print(f"⚡ API Latency: {latency:.2f}ms")
            print(f"🌐 Total Request Time: {request_time:.2f}s")
            print(f"🔍 Results Found: {len(data.get('results', []))}")
            
            # Show first result details
            results = data.get('results', [])
            if results:
                first_result = results[0]
                print(f"\n📋 First Result Details:")
                print(f"   Case ID: {first_result.get('case_id', 'N/A')}")
                print(f"   Final Score: {first_result.get('final_score', 'N/A')}")
                print(f"   Vector Score: {first_result.get('vector_score', 'N/A')}")
                print(f"   Keyword Score: {first_result.get('keyword_score', 'N/A')}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print(f"❌ TIMEOUT: Request took longer than 60 seconds")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Semantic-only search
    print(f"\n\n🔍 TEST 2: Semantic-Only Search")
    print("-" * 40)
    
    params = {
        'q': test_query,
        'mode': 'semantic',
        'limit': 10,
        'return_facets': 'false',
        'highlight': 'false',
        'debug': 'false'
    }
    
    url = f"{BASE_URL}/search/?{urlencode(params)}"
    
    try:
        start_time = time.time()
        response = requests.get(url, timeout=60)
        request_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            latency = data.get('search_metadata', {}).get('latency_ms', 0)
            total_results = data.get('search_metadata', {}).get('total_results', 0)
            
            print(f"✅ Status: 200 OK")
            print(f"📊 Total Results: {total_results}")
            print(f"⚡ API Latency: {latency:.2f}ms")
            print(f"🌐 Total Request Time: {request_time:.2f}s")
            print(f"🔍 Results Found: {len(data.get('results', []))}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print(f"❌ TIMEOUT: Request took longer than 60 seconds")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Lexical-only search
    print(f"\n\n🔍 TEST 3: Lexical-Only Search")
    print("-" * 40)
    
    params = {
        'q': test_query,
        'mode': 'lexical',
        'limit': 10,
        'return_facets': 'false',
        'highlight': 'false',
        'debug': 'false'
    }
    
    url = f"{BASE_URL}/search/?{urlencode(params)}"
    
    try:
        start_time = time.time()
        response = requests.get(url, timeout=60)
        request_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            latency = data.get('search_metadata', {}).get('latency_ms', 0)
            total_results = data.get('search_metadata', {}).get('total_results', 0)
            
            print(f"✅ Status: 200 OK")
            print(f"📊 Total Results: {total_results}")
            print(f"⚡ API Latency: {latency:.2f}ms")
            print(f"🌐 Total Request Time: {request_time:.2f}s")
            print(f"🔍 Results Found: {len(data.get('results', []))}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print(f"❌ TIMEOUT: Request took longer than 60 seconds")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 4: Check server status
    print(f"\n\n🔍 TEST 4: Server Status Check")
    print("-" * 40)
    
    url = f"{BASE_URL}/status/"
    
    try:
        start_time = time.time()
        response = requests.get(url, timeout=15)
        request_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: 200 OK")
            print(f"🌐 Request Time: {request_time:.2f}s")
            print(f"📊 System Status: {data.get('status', 'unknown')}")
            
            # Check index status
            indexes = data.get('indexes', {})
            if indexes:
                print(f"\n📊 Index Status:")
                for index_type, status in indexes.items():
                    if isinstance(status, dict):
                        if index_type == 'facet_indexes':
                            # Facet indexes have a different structure
                            built_count = status.get('built', 0)
                            total_count = status.get('total', 0)
                            is_built = built_count > 0
                            print(f"   {index_type}: {'✅ Built' if is_built else '❌ Not Built'} ({built_count}/{total_count})")
                        else:
                            # Other indexes have is_built field
                            is_built = status.get('is_built', False)
                            total = status.get('total_vectors', status.get('total_documents', 0))
                            print(f"   {index_type}: {'✅ Built' if is_built else '❌ Not Built'} ({total})")
                    else:
                        print(f"   {index_type}: {status}")
        else:
            print(f"❌ Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def profile_simple_queries():
    """Profile performance with very simple queries"""
    print(f"\n\n🔍 SIMPLE QUERIES PERFORMANCE TEST")
    print("=" * 60)
    
    simple_queries = [
        "2025",
        "Application",
        "Court",
        "Case"
    ]
    
    for query in simple_queries:
        print(f"\n📝 Testing: '{query}'")
        print("-" * 30)
        
        params = {
            'q': query,
            'mode': 'hybrid',
            'limit': 5,
            'return_facets': 'false',
            'highlight': 'false',
            'debug': 'false'
        }
        
        url = f"{BASE_URL}/search/?{urlencode(params)}"
        
        try:
            start_time = time.time()
            response = requests.get(url, timeout=30)
            request_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                latency = data.get('search_metadata', {}).get('latency_ms', 0)
                total_results = data.get('search_metadata', {}).get('total_results', 0)
                
                print(f"✅ Status: 200 OK")
                print(f"📊 Total Results: {total_results}")
                print(f"⚡ API Latency: {latency:.2f}ms")
                print(f"🌐 Request Time: {request_time:.2f}s")
            else:
                print(f"❌ Error: {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"❌ TIMEOUT: Request took longer than 30 seconds")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        time.sleep(1)  # Be nice to the server

if __name__ == "__main__":
    print("🚀 SEARCH PERFORMANCE PROFILING")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        profile_search_performance()
        profile_simple_queries()
        
        print(f"\n\n{'='*60}")
        print("✅ PERFORMANCE PROFILING COMPLETED!")
        print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
    except KeyboardInterrupt:
        print(f"\n\n⏹️  Profiling interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Performance profiling failed: {e}")
