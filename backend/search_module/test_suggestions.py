#!/usr/bin/env python3
"""
Test Suggestions API
Check if the suggestions are working after the fixes
"""

import requests
import json
from urllib.parse import urlencode

# Configuration
BASE_URL = "http://localhost:8000/api/search"

def test_suggestions():
    """Test the suggestions API"""
    print("🔍 TESTING SUGGESTIONS API")
    print("=" * 60)
    
    # Test queries
    test_queries = [
        "PPC",      # Should find section suggestions
        "302",      # Should find section suggestions  
        "Chief",    # Should find judge suggestions
        "CPC",      # Should find section suggestions
        "CrPC",     # Should find section suggestions
    ]
    
    for query in test_queries:
        print(f"\n📝 Testing query: '{query}'")
        print("-" * 40)
        
        # Test auto suggestions
        try:
            params = {
                'q': query,
                'type': 'auto'
            }
            
            response = requests.get(
                f"{BASE_URL}/suggest/",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                suggestions = data.get('suggestions', [])
                print(f"✅ Auto suggestions: {len(suggestions)} found")
                
                for i, suggestion in enumerate(suggestions[:3]):
                    print(f"   {i+1}. {suggestion.get('value', 'N/A')} ({suggestion.get('type', 'N/A')})")
                    print(f"      Info: {suggestion.get('additional_info', 'N/A')}")
            else:
                print(f"❌ Auto suggestions failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Auto suggestions error: {e}")
        
        # Test specific type suggestions
        for suggestion_type in ['citation', 'section', 'judge']:
            try:
                params = {
                    'q': query,
                    'type': suggestion_type
                }
                
                response = requests.get(
                    f"{BASE_URL}/suggest/",
                    params=params,
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    suggestions = data.get('suggestions', [])
                    print(f"✅ {suggestion_type.title()} suggestions: {len(suggestions)} found")
                    
                    for i, suggestion in enumerate(suggestions[:2]):
                        print(f"   {i+1}. {suggestion.get('value', 'N/A')}")
                        print(f"      Info: {suggestion.get('additional_info', 'N/A')}")
                else:
                    print(f"❌ {suggestion_type.title()} suggestions failed: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ {suggestion_type.title()} suggestions error: {e}")

if __name__ == "__main__":
    test_suggestions()
