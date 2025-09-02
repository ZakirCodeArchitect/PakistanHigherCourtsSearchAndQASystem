#!/usr/bin/env python3
"""
Debug Status Endpoint
Check why the status endpoint is not working properly
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from search_indexing.views import SearchStatusAPIView
from search_indexing.services.hybrid_indexing import HybridIndexingService
from django.test import RequestFactory

def debug_status():
    """Debug the status endpoint"""
    print("🔍 DEBUGGING STATUS ENDPOINT")
    print("=" * 60)
    
    try:
        # Create a mock request
        factory = RequestFactory()
        request = factory.get('/api/search/status/')
        
        # Create the view instance
        view = SearchStatusAPIView()
        
        # Test the hybrid service directly
        print("📊 Testing Hybrid Service:")
        try:
            hybrid_service = HybridIndexingService()
            index_status = hybrid_service.get_index_status()
            print(f"   Index status: {index_status}")
        except Exception as e:
            print(f"   ❌ Hybrid service error: {e}")
        
        # Test the health metrics
        print(f"\n📊 Testing Health Metrics:")
        try:
            health_metrics = view._get_health_metrics()
            print(f"   Health metrics: {health_metrics}")
        except Exception as e:
            print(f"   ❌ Health metrics error: {e}")
        
        # Test the full status endpoint
        print(f"\n📊 Testing Full Status Endpoint:")
        try:
            response = view.get(request)
            print(f"   Response status: {response.status_code}")
            print(f"   Response data: {response.data}")
        except Exception as e:
            print(f"   ❌ Status endpoint error: {e}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_status()
