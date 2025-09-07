#!/usr/bin/env python
"""
Check Search Metadata - Look for the Libya case in search metadata
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def check_search_metadata():
    """Check search metadata for the Libya case"""
    print("🔍 CHECKING SEARCH METADATA FOR LIBYA CASE")
    print("=" * 60)
    
    from apps.cases.models import Case
    from search_indexing.models import SearchMetadata
    
    # Get the Libya case
    libya_case = Case.objects.filter(case_title__icontains='libya').first()
    if not libya_case:
        print("❌ Libya case not found in database")
        return
    
    print(f"✅ Found Libya case: {libya_case.case_number}")
    print(f"   Title: {libya_case.case_title}")
    print(f"   Case ID: {libya_case.id}")
    
    # Check if it has search metadata
    print(f"\n🔍 Checking search metadata for case ID {libya_case.id}...")
    search_metadata = SearchMetadata.objects.filter(case_id=libya_case.id).first()
    
    if search_metadata:
        print("✅ Search metadata found!")
        print(f"   Case ID: {search_metadata.case_id}")
        print(f"   Case Number: {search_metadata.case_number_normalized}")
        print(f"   Case Title: {search_metadata.case_title_normalized}")
        print(f"   Court: {search_metadata.court_normalized}")
        print(f"   Is Indexed: {search_metadata.is_indexed}")
        print(f"   Enhanced Metadata Extracted: {search_metadata.enhanced_metadata_extracted}")
        print(f"   Total Terms: {search_metadata.total_terms}")
        print(f"   Total Chunks: {search_metadata.total_chunks}")
        
        # Check searchable keywords
        if search_metadata.searchable_keywords:
            print(f"   Searchable Keywords: {search_metadata.searchable_keywords[:10]}...")  # First 10
        
        # Check legal entities
        if search_metadata.legal_entities:
            print(f"   Legal Entities: {search_metadata.legal_entities}")
        
        # Check semantic tags
        if search_metadata.semantic_tags:
            print(f"   Semantic Tags: {search_metadata.semantic_tags[:5]}...")  # First 5
        
    else:
        print("❌ No search metadata found for Libya case!")
        print("🔧 This explains why it's not appearing in search results")
        print("💡 Solution: Need to index this case")
    
    # Check if there are any search metadata entries with 'libya'
    print(f"\n🔍 Checking all search metadata for 'libya'...")
    libya_metadata = SearchMetadata.objects.filter(
        case_title_normalized__icontains='libya'
    )
    print(f"Found {libya_metadata.count()} search metadata entries with 'libya'")
    
    for metadata in libya_metadata:
        print(f"   Case ID: {metadata.case_id}")
        print(f"   Title: {metadata.case_title_normalized}")
        print(f"   Indexed: {metadata.is_indexed}")
        print()
    
    # Check if there are any search metadata entries with 'civil judge'
    print(f"\n🔍 Checking all search metadata for 'civil judge'...")
    civil_judge_metadata = SearchMetadata.objects.filter(
        case_title_normalized__icontains='civil judge'
    )
    print(f"Found {civil_judge_metadata.count()} search metadata entries with 'civil judge'")
    
    for metadata in civil_judge_metadata:
        print(f"   Case ID: {metadata.case_id}")
        print(f"   Title: {metadata.case_title_normalized}")
        print(f"   Indexed: {metadata.is_indexed}")
        print()
    
    print("\n" + "=" * 60)
    print("🔍 ROOT CAUSE ANALYSIS:")
    if not search_metadata:
        print("❌ ROOT CAUSE: Libya case is not indexed in search metadata")
        print("💡 SOLUTION: Need to run indexing for this case")
    elif not search_metadata.is_indexed:
        print("❌ ROOT CAUSE: Libya case metadata exists but not marked as indexed")
        print("💡 SOLUTION: Need to mark as indexed or re-index")
    else:
        print("✅ Libya case is properly indexed")
        print("❌ ROOT CAUSE: Search ranking/query processing issue")
        print("💡 SOLUTION: Need to improve search algorithm")

if __name__ == "__main__":
    check_search_metadata()
