#!/usr/bin/env python3
"""
Debug Pinecone Configuration
Check exactly what's happening with API key loading and connection
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.conf import settings
from search_indexing.services.pinecone_indexing import PineconeIndexingService

def debug_pinecone_config():
    """Debug Pinecone configuration and API key loading"""
    print("🔍 DEBUGGING PINECONE CONFIGURATION")
    print("=" * 60)
    
    # Check environment variables
    print("\n📋 ENVIRONMENT VARIABLES:")
    env_api_key = os.getenv('PINECONE_API_KEY')
    print(f"   os.getenv('PINECONE_API_KEY'): {'✅ Set' if env_api_key else '❌ Not Set'}")
    if env_api_key:
        print(f"   API Key Length: {len(env_api_key)} characters")
        print(f"   API Key Preview: {env_api_key[:10]}...{env_api_key[-10:] if len(env_api_key) > 20 else ''}")
    
    # Check Django settings
    print("\n⚙️  DJANGO SETTINGS:")
    django_api_key = getattr(settings, 'PINECONE_API_KEY', None)
    print(f"   settings.PINECONE_API_KEY: {'✅ Set' if django_api_key else '❌ Not Set'}")
    if django_api_key:
        print(f"   API Key Length: {len(django_api_key)} characters")
        print(f"   API Key Preview: {django_api_key[:10]}...{django_api_key[-10:] if len(django_api_key) > 20 else ''}")
    
    # Check if there are any other environment variables that might contain the key
    print("\n🔍 OTHER POTENTIAL ENVIRONMENT VARIABLES:")
    pinecone_vars = [k for k in os.environ.keys() if 'pinecone' in k.lower()]
    if pinecone_vars:
        for var in pinecone_vars:
            value = os.environ[var]
            print(f"   {var}: {'✅ Set' if value else '❌ Not Set'}")
            if value and len(value) > 20:
                print(f"      Preview: {value[:10]}...{value[-10:]}")
    else:
        print("   No other Pinecone-related environment variables found")
    
    # Try to initialize Pinecone service
    print("\n🔧 TESTING PINECONE SERVICE INITIALIZATION:")
    try:
        service = PineconeIndexingService()
        print("   ✅ PineconeIndexingService created successfully")
        
        # Try to initialize Pinecone
        print("   🔄 Attempting to initialize Pinecone...")
        if service.initialize_pinecone():
            print("   ✅ Pinecone initialized successfully")
            
            # Try to get index stats
            print("   🔄 Attempting to get index stats...")
            try:
                stats = service.get_index_stats()
                if stats:
                    print("   ✅ Index stats retrieved successfully")
                    print(f"      Index Name: {stats.get('index_name', 'N/A')}")
                    print(f"      Dimension: {stats.get('dimension', 'N/A')}")
                    print(f"      Vector Count: {stats.get('total_vector_count', 'N/A')}")
                else:
                    print("   ⚠️  Could not get index stats")
            except Exception as e:
                print(f"   ❌ Error getting index stats: {str(e)}")
        else:
            print("   ❌ Failed to initialize Pinecone")
            
    except Exception as e:
        print(f"   ❌ Error creating Pinecone service: {str(e)}")
    
    # Check if there are any cached connections or existing indexes
    print("\n🔍 CHECKING FOR EXISTING CONNECTIONS:")
    try:
        import pinecone
        print("   ✅ Pinecone library imported successfully")
        
        # Check if there are any existing indexes
        try:
            # This might work if there's a cached connection
            from pinecone import Pinecone
            print("   🔄 Attempting to list indexes without explicit initialization...")
            
            # Try to get any existing connection
            try:
                # Check if there's a default client
                if hasattr(pinecone, 'list_indexes'):
                    indexes = pinecone.list_indexes()
                    print(f"   ✅ Found {len(indexes)} indexes using default connection")
                    for idx in indexes:
                        print(f"      - {idx}")
                else:
                    print("   ⚠️  No default connection found")
            except Exception as e:
                print(f"   ❌ Error listing indexes: {str(e)}")
                
        except Exception as e:
            print(f"   ❌ Error with Pinecone operations: {str(e)}")
            
    except ImportError as e:
        print(f"   ❌ Pinecone library not available: {str(e)}")

if __name__ == "__main__":
    debug_pinecone_config()
