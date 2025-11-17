"""
Check if BM25 can be imported correctly
"""

import sys
import os

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

print("=" * 80)
print("BM25 IMPORT CHECK")
print("=" * 80)

# Check 1: Direct import
print("\n1. Checking direct rank_bm25 import...")
try:
    from rank_bm25 import BM25Okapi
    print("   [OK] rank_bm25.BM25Okapi imported successfully")
except ImportError as e:
    print(f"   [ERROR] Failed to import rank_bm25: {e}")
    sys.exit(1)

# Setup Django first
print("\n2. Setting up Django...")
try:
    import django
    django.setup()
    print("   [OK] Django setup complete")
except Exception as e:
    print(f"   [ERROR] Django setup failed: {e}")
    sys.exit(1)

# Check 3: Import through bm25_indexing module
print("\n3. Checking bm25_indexing module import...")
try:
    from search_indexing.services.bm25_indexing import BM25IndexingService, BM25_AVAILABLE
    print(f"   [OK] BM25IndexingService imported successfully")
    print(f"   [OK] BM25_AVAILABLE = {BM25_AVAILABLE}")
except ImportError as e:
    print(f"   [ERROR] Failed to import BM25IndexingService: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Check 4: Import through keyword_indexing module
print("\n4. Checking keyword_indexing module import...")
try:
    from search_indexing.services.keyword_indexing import KeywordIndexingService
    print("   [OK] KeywordIndexingService imported successfully")
    
    # Try to initialize
    service = KeywordIndexingService()
    print(f"   [OK] KeywordIndexingService initialized")
    print(f"   [OK] service.use_bm25 = {service.use_bm25}")
    print(f"   [OK] service.bm25_service is not None = {service.bm25_service is not None}")
except Exception as e:
    print(f"   [ERROR] Failed to initialize KeywordIndexingService: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("[SUCCESS] All BM25 imports are working correctly")
print("=" * 80)

