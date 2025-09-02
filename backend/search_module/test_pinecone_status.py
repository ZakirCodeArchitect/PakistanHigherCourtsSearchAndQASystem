#!/usr/bin/env python3
"""
Test Pinecone Status
Check if Pinecone can be initialized and what the current configuration is
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from search_indexing.services.pinecone_indexing import PineconeIndexingService
from search_indexing.services.hybrid_indexing import HybridIndexingService

def test_pinecone_status():
    """Test Pinecone initialization and status"""
    print("🔍 Testing Pinecone Status")
    print("=" * 50)
    
    # Check environment variables
    api_key = os.getenv('PINECONE_API_KEY')
    print(f"📋 Environment Variables:")
    print(f"   PINECONE_API_KEY: {'✅ Set' if api_key else '❌ Not Set'}")
    if api_key:
        print(f"   API Key Length: {len(api_key)} characters")
    
    # Try to initialize Pinecone service
    print(f"\n🔧 Testing Pinecone Service Initialization:")
    try:
        service = PineconeIndexingService()
        print("   ✅ PineconeIndexingService created successfully")
        
        # Try to initialize Pinecone
        if service.initialize_pinecone():
            print("   ✅ Pinecone initialized successfully")
            
            # Try to get index stats
            stats = service.get_index_stats()
            if stats:
                print("   ✅ Index stats retrieved successfully")
                print(f"   📊 Index Name: {stats.get('index_name', 'N/A')}")
                print(f"   📊 Dimension: {stats.get('dimension', 'N/A')}")
                print(f"   📊 Vector Count: {stats.get('total_vector_count', 'N/A')}")
            else:
                print("   ⚠️  Could not get index stats")
        else:
            print("   ❌ Failed to initialize Pinecone")
            
    except Exception as e:
        print(f"   ❌ Error initializing Pinecone service: {str(e)}")
    
    # Test hybrid service with Pinecone
    print(f"\n🔧 Testing Hybrid Service with Pinecone:")
    try:
        hybrid_service = HybridIndexingService(use_pinecone=True)
        print("   ✅ HybridIndexingService with Pinecone created successfully")
        
        # Check what vector service is being used
        if hasattr(hybrid_service, 'vector_service'):
            service_type = type(hybrid_service.vector_service).__name__
            print(f"   📊 Vector Service Type: {service_type}")
            
            if 'Pinecone' in service_type:
                print("   ✅ Using Pinecone vector service")
            else:
                print("   ⚠️  Using FAISS vector service (Pinecone not available)")
        else:
            print("   ❌ No vector service found")
            
    except Exception as e:
        print(f"   ❌ Error creating hybrid service: {str(e)}")

def test_faiss_fallback():
    """Test FAISS fallback performance"""
    print(f"\n🔧 Testing FAISS Fallback Performance:")
    try:
        from search_indexing.services.vector_indexing import VectorIndexingService
        
        service = VectorIndexingService()
        print("   ✅ FAISS service created successfully")
        
        # Test if index is loaded
        if service._load_cached_index():
            print("   ✅ FAISS index loaded successfully")
        else:
            print("   ❌ Failed to load FAISS index")
            
    except Exception as e:
        print(f"   ❌ Error with FAISS service: {str(e)}")

if __name__ == "__main__":
    test_pinecone_status()
    test_faiss_fallback()
    
    print(f"\n{'='*50}")
    print("📋 RECOMMENDATIONS:")
    if not os.getenv('PINECONE_API_KEY'):
        print("1. Set PINECONE_API_KEY environment variable for better performance")
        print("2. Sign up at pinecone.io to get a free API key")
        print("3. Current system will use optimized FAISS as fallback")
    else:
        print("1. Pinecone is configured and ready to use")
        print("2. Performance should be significantly better than FAISS")
