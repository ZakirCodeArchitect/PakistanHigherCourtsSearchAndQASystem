#!/usr/bin/env python3
"""
Comprehensive Test Script for Search API
Shows full search results without limits and tests with diverse queries
"""

import requests
import json
import time
from urllib.parse import urlencode
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000/api/search"

# Diverse test queries covering different legal scenarios
COMPREHENSIVE_QUERIES = [
    # Legal Citations
    "PPC 302",
    "CrPC 497", 
    "CPC 9",
    "PLD 2020",
    "SCMR 2021",
    
    # Case Types
    "constitutional petition",
    "habeas corpus",
    "mandamus writ",
    "winding up petition",
    "criminal appeal",
    
    # Organizations/Entities
    "OGRA",
    "SNGPL",
    "FBR",
    "NAB",
    "ECP",
    
    # Legal Terms
    "bail",
    "stay order",
    "interim relief",
    "contempt of court",
    "judicial review",
    
    # Specific Case Numbers
    "Application 2/2025",
    "Petition 1/2024",
    "Appeal 3/2023",
    "Case 5/2022",
    "Reference 1/2021",
    
    # Judges/Courts
    "Chief Justice",
    "High Court",
    "Supreme Court",
    "Justice",
    "Bench",
    
    # Years
    "2025",
    "2024", 
    "2023",
    "2022",
    "2021"
]

def test_comprehensive_search():
    """Test search endpoint with comprehensive queries and show full results"""
    print("🔍 COMPREHENSIVE SEARCH TESTING")
    print("=" * 80)
    
    for i, query in enumerate(COMPREHENSIVE_QUERIES, 1):
        print(f"\n{'='*60}")
        print(f"📝 TEST {i:2d}/30: '{query}'")
        print(f"{'='*60}")
        
        # Test all search modes
        for mode in ['lexical', 'semantic', 'hybrid']:
            print(f"\n🔍 {mode.upper()} SEARCH MODE:")
            print("-" * 40)
            
            params = {
                'q': query,
                'mode': mode,
                'limit': 50,  # High limit to get more results
                'return_facets': 'true',
                'highlight': 'true',
                'debug': 'true'  # Get debug information
            }
            
            url = f"{BASE_URL}/search/?{urlencode(params)}"
            
            try:
                start_time = time.time()
                response = requests.get(url, timeout=60)  # Increased timeout
                request_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Basic info
                    total_results = data.get('search_metadata', {}).get('total_results', 0)
                    latency = data.get('search_metadata', {}).get('latency_ms', 0)
                    
                    print(f"✅ Status: 200 OK")
                    print(f"📊 Total Results: {total_results}")
                    print(f"⚡ API Latency: {latency:.2f}ms")
                    print(f"🌐 Request Time: {request_time:.2f}s")
                    
                    # Query information
                    query_info = data.get('query_info', {})
                    print(f"🔍 Query Info:")
                    print(f"   Original: '{query_info.get('original_query', 'N/A')}'")
                    print(f"   Normalized: '{query_info.get('normalized_query', 'N/A')}'")
                    print(f"   Citations Found: {query_info.get('citations_found', 0)}")
                    print(f"   Exact Matches: {query_info.get('exact_matches_found', 0)}")
                    
                    # Show ALL results in detail
                    results = data.get('results', [])
                    if results:
                        print(f"\n📋 ALL RESULTS ({len(results)} found):")
                        print("-" * 50)
                        
                        for j, result in enumerate(results, 1):
                            print(f"\n🎯 RESULT #{j}:")
                            print(f"   Case ID: {result.get('case_id', 'N/A')}")
                            print(f"   Rank: {result.get('rank', 'N/A')}")
                            print(f"   Final Score: {result.get('final_score', 'N/A'):.4f}")
                            
                            # Scoring breakdown
                            print(f"   📊 Scoring:")
                            print(f"      Vector Score: {result.get('vector_score', 0):.4f}")
                            print(f"      Keyword Score: {result.get('keyword_score', 0):.4f}")
                            print(f"      Base Score: {result.get('base_score', 0):.4f}")
                            print(f"      Recency Score: {result.get('recency_score', 0):.4f}")
                            print(f"      Total Boost: {result.get('total_boost', 0):.4f}")
                            
                            # Result data
                            result_data = result.get('result_data', {})
                            print(f"   📄 Case Details:")
                            print(f"      Case Number: {result_data.get('case_number', 'N/A')}")
                            print(f"      Case Title: {result_data.get('case_title', 'N/A')}")
                            print(f"      Court: {result_data.get('court', 'N/A')}")
                            print(f"      Status: {result_data.get('status', 'N/A')}")
                            print(f"      Parties: {result_data.get('parties', 'N/A')}")
                            print(f"      Institution Date: {result_data.get('institution_date', 'N/A')}")
                            print(f"      Disposal Date: {result_data.get('disposal_date', 'N/A')}")
                            
                            # Boost factors
                            boost_factors = result.get('boost_factors', [])
                            if boost_factors:
                                print(f"   🚀 Boost Factors: {boost_factors}")
                            
                            # Explanation (if available)
                            explanation = result.get('explanation', {})
                            if explanation:
                                print(f"   🔍 Explanation:")
                                for key, value in explanation.items():
                                    if isinstance(value, float):
                                        print(f"      {key}: {value:.4f}")
                                    else:
                                        print(f"      {key}: {value}")
                            
                            # Snippets (if available)
                            snippets = result.get('snippets', [])
                            if snippets:
                                print(f"   📝 Snippets ({len(snippets)}):")
                                for k, snippet in enumerate(snippets[:3], 1):  # Show first 3 snippets
                                    print(f"      {k}. {snippet.get('text', 'N/A')[:200]}...")
                                    print(f"         Relevance: {snippet.get('relevance', 0):.4f}")
                                    print(f"         Source: {snippet.get('source', 'N/A')}")
                    
                    # Show facets
                    facets = data.get('facets', {})
                    if facets:
                        print(f"\n🔍 FACETS:")
                        print("-" * 30)
                        for facet_type, facet_values in facets.items():
                            if facet_values and len(facet_values) > 0:
                                print(f"   {facet_type.upper()}:")
                                for facet in facet_values[:5]:  # Show top 5 facet values
                                    print(f"      {facet.get('value', 'N/A')} ({facet.get('count', 0)} cases)")
                    
                    # Show pagination info
                    pagination = data.get('pagination', {})
                    if pagination:
                        print(f"\n📄 PAGINATION:")
                        print(f"   Total: {pagination.get('total', 0)}")
                        print(f"   Offset: {pagination.get('offset', 0)}")
                        print(f"   Limit: {pagination.get('limit', 0)}")
                        print(f"   Has Next: {pagination.get('has_next', False)}")
                        print(f"   Has Previous: {pagination.get('has_previous', False)}")
                    
                    # Show debug info if available
                    debug_signals = data.get('debug_signals', {})
                    if debug_signals:
                        print(f"\n🐛 DEBUG SIGNALS:")
                        print(f"   Query Normalization: {debug_signals.get('query_normalization', {})}")
                        print(f"   Ranking Config: {debug_signals.get('ranking_config', {})}")
                        print(f"   Boost Signals: {debug_signals.get('boost_signals', {})}")
                        print(f"   Search Performance: {debug_signals.get('search_performance', {})}")
                    
                else:
                    print(f"❌ Error: {response.status_code}")
                    print(f"Response: {response.text}")
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ Request failed: {e}")
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
            
            print(f"\n{'='*60}")
            time.sleep(2)  # Be nice to the server

def test_suggestions_comprehensive():
    """Test suggestions with comprehensive queries"""
    print(f"\n\n💡 COMPREHENSIVE SUGGESTIONS TESTING")
    print("=" * 80)
    
    suggestion_queries = [
        "PPC", "CrPC", "CPC", "PLD", "SCMR",
        "Application", "Petition", "Appeal", "Case", "Reference",
        "OGRA", "SNGPL", "FBR", "NAB", "ECP",
        "bail", "stay", "contempt", "review", "relief",
        "Chief", "Justice", "Court", "Bench", "Judge"
    ]
    
    for query in suggestion_queries:
        print(f"\n🔤 Testing suggestions for: '{query}'")
        print("-" * 50)
        
        for suggestion_type in ['auto', 'case', 'citation', 'section', 'judge']:
            params = {
                'q': query,
                'type': suggestion_type
            }
            
            url = f"{BASE_URL}/suggest/?{urlencode(params)}"
            
            try:
                response = requests.get(url, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    suggestions = data.get('suggestions', [])
                    
                    if suggestions:
                        print(f"✅ {suggestion_type.upper()}: {len(suggestions)} suggestions")
                        for i, suggestion in enumerate(suggestions, 1):
                            print(f"   {i:2d}. {suggestion.get('value', 'N/A')}")
                            print(f"       Type: {suggestion.get('type', 'N/A')}")
                            print(f"       Info: {suggestion.get('additional_info', 'N/A')}")
                    else:
                        print(f"⚠️  {suggestion_type.upper()}: No suggestions")
                        
                else:
                    print(f"❌ {suggestion_type.upper()}: Error {response.status_code}")
                    
            except Exception as e:
                print(f"❌ {suggestion_type.upper()}: Request failed - {e}")
        
        time.sleep(1)

def test_status_detailed():
    """Test status endpoint with detailed information"""
    print(f"\n\n📊 DETAILED STATUS TESTING")
    print("=" * 80)
    
    url = f"{BASE_URL}/status/"
    
    try:
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"✅ System Status: {data.get('status', 'unknown')}")
            print(f"🕒 Timestamp: {datetime.fromtimestamp(data.get('timestamp', 0))}")
            
            # Detailed index information
            indexes = data.get('indexes', {})
            if indexes:
                print(f"\n📊 INDEX DETAILS:")
                print("-" * 40)
                
                for index_type, status in indexes.items():
                    print(f"\n🔍 {index_type.upper()}:")
                    if isinstance(status, dict):
                        for key, value in status.items():
                            if key == 'last_updated' and value:
                                try:
                                    from datetime import datetime
                                    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                                    print(f"   {key}: {dt.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                                except:
                                    print(f"   {key}: {value}")
                            else:
                                print(f"   {key}: {value}")
                    else:
                        print(f"   {status}")
            
            # Health metrics
            health = data.get('health', {})
            if health:
                print(f"\n🏥 HEALTH METRICS:")
                print("-" * 40)
                
                is_healthy = health.get('is_healthy', False)
                print(f"   Overall Health: {'✅ HEALTHY' if is_healthy else '❌ UNHEALTHY'}")
                
                database = health.get('database', {})
                if database:
                    print(f"   Database: {'✅ Healthy' if database.get('healthy') else '❌ Unhealthy'}")
                    print(f"   Total Cases: {database.get('total_cases', 0)}")
                
                indexing = health.get('indexing', {})
                if indexing:
                    print(f"   Index Coverage: {indexing.get('coverage_percentage', 0)}%")
                    print(f"   Indexed Cases: {indexing.get('indexed_cases', 0)}")
                    print(f"   Total Cases: {indexing.get('total_cases', 0)}")
            
            # System info
            system_info = data.get('system_info', {})
            if system_info:
                print(f"\n⚙️  SYSTEM INFO:")
                print("-" * 40)
                for key, value in system_info.items():
                    print(f"   {key}: {value}")
                    
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

def main():
    """Run comprehensive tests"""
    print("🚀 COMPREHENSIVE SEARCH API TESTING")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    try:
        # Run comprehensive tests
        test_comprehensive_search()
        test_suggestions_comprehensive()
        test_status_detailed()
        
        print(f"\n\n{'='*80}")
        print("✅ COMPREHENSIVE TESTING COMPLETED!")
        print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")
        
    except KeyboardInterrupt:
        print(f"\n\n⏹️  Testing interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Comprehensive test suite failed: {e}")

if __name__ == "__main__":
    main()
