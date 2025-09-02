#!/usr/bin/env python3
"""
Debug Search Metadata
Check what's in the SearchMetadata and why keyword search is failing
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from search_indexing.models import SearchMetadata
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank

def debug_search_metadata():
    """Debug SearchMetadata content and search issues"""
    print("🔍 DEBUGGING SEARCH METADATA")
    print("=" * 60)
    
    try:
        # Check total count
        total_count = SearchMetadata.objects.count()
        print(f"📊 Total SearchMetadata records: {total_count}")
        
        indexed_count = SearchMetadata.objects.filter(is_indexed=True).count()
        print(f"📊 Indexed records: {indexed_count}")
        
        # Check a few sample records
        print(f"\n🔍 Sample records:")
        sample_records = SearchMetadata.objects.all()[:3]
        
        for i, record in enumerate(sample_records):
            print(f"\n   Record {i+1}:")
            print(f"      Case ID: {record.case_id}")
            print(f"      Case Number: {record.case_number_normalized}")
            print(f"      Case Title: {record.case_title_normalized}")
            print(f"      Court: {record.court_normalized}")
            print(f"      Status: {record.status_normalized}")
            print(f"      Is Indexed: {record.is_indexed}")
        
        # Test the search query "PPC 302"
        test_query = "PPC 302"
        print(f"\n🔍 Testing search query: '{test_query}'")
        
        # Build search vector
        search_vector = (
            SearchVector('case_number_normalized', weight='A') +
            SearchVector('case_title_normalized', weight='B') +
            SearchVector('parties_normalized', weight='C') +
            SearchVector('court_normalized', weight='D')
        )
        
        search_query = SearchQuery(test_query, config='english')
        
        # Try to find any results
        results = SearchMetadata.objects.filter(is_indexed=True).annotate(
            rank=SearchRank(search_vector, search_query)
        ).order_by('-rank')[:5]
        
        print(f"\n📊 Search results: {len(results)}")
        
        if results:
            print("\n🔍 Top results:")
            for i, result in enumerate(results):
                print(f"\n   Result {i+1}:")
                print(f"      Case ID: {result.case_id}")
                print(f"      Case Number: {result.case_number_normalized}")
                print(f"      Case Title: {result.case_title_normalized}")
                print(f"      Rank: {result.rank}")
                print(f"      Raw Rank: {getattr(result, 'rank', 'N/A')}")
        else:
            print("❌ No search results found")
        
        # Check if there are any records with "PPC" in them
        print(f"\n🔍 Checking for records containing 'PPC':")
        ppc_records = SearchMetadata.objects.filter(
            case_number_normalized__icontains='PPC'
        )[:3]
        
        print(f"📊 Records with 'PPC': {ppc_records.count()}")
        
        if ppc_records:
            for i, record in enumerate(ppc_records):
                print(f"\n   PPC Record {i+1}:")
                print(f"      Case ID: {record.case_id}")
                print(f"      Case Number: {record.case_number_normalized}")
                print(f"      Case Title: {record.case_title_normalized}")
        
        # Check if there are any records with "302" in them
        print(f"\n🔍 Checking for records containing '302':")
        section_records = SearchMetadata.objects.filter(
            case_number_normalized__icontains='302'
        )[:3]
        
        print(f"📊 Records with '302': {section_records.count()}")
        
        if section_records:
            for i, record in enumerate(section_records):
                print(f"\n   Section Record {i+1}:")
                print(f"      Case ID: {record.case_id}")
                print(f"      Case Number: {record.case_number_normalized}")
                print(f"      Case Title: {record.case_title_normalized}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_search_metadata()
