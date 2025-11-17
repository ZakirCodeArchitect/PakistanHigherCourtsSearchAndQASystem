"""
Quick verification that BM25 is the default
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from search_indexing.services.keyword_indexing import KeywordIndexingService
import inspect

print("=" * 80)
print("BM25 DEFAULT CONFIGURATION VERIFICATION")
print("=" * 80)

# Check the default parameter
sig = inspect.signature(KeywordIndexingService.__init__)
default_value = sig.parameters['use_bm25'].default
print(f"\n1. Default parameter value: use_bm25 = {default_value}")

# Initialize service without parameters (should use default)
print("\n2. Initializing KeywordIndexingService() without parameters...")
service = KeywordIndexingService()
print(f"   Service.use_bm25 = {service.use_bm25}")
print(f"   BM25 service initialized = {service.bm25_service is not None}")

# Test a search to confirm BM25 is being used
print("\n3. Testing search to verify BM25 is used...")
try:
    results = service.search("service matter", top_k=3)
    if results:
        print(f"   [OK] Search returned {len(results)} results")
        if results[0].get('bm25_score') is not None:
            print(f"   [OK] Results include BM25 scores (BM25 is active)")
        else:
            print(f"   [WARN] Results don't include BM25 scores (may be using fallback)")
except Exception as e:
    print(f"   [ERROR] Search failed: {e}")

print("\n" + "=" * 80)
print("CONCLUSION:")
if default_value and service.use_bm25:
    print("[SUCCESS] BM25 is the DEFAULT search method")
else:
    print("[INFO] BM25 is not the default")
print("=" * 80)

