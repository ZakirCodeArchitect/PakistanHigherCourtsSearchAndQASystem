#!/usr/bin/env python3
"""
Script to check database content and identify data issues
"""

import os
import sys
import django

# Add the backend/search_module directory to Python path
backend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend', 'search_module')
sys.path.append(backend_path)

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'search_module.settings')
django.setup()

from apps.cases.models import Case, Court
from search_indexing.models import DocumentChunk, SearchMetadata

def check_database():
    """Check database content and identify issues"""
    print("🔍 DATABASE CONTENT ANALYSIS")
    print("=" * 60)
    
    # Check cases
    total_cases = Case.objects.count()
    print(f"📊 Total Cases: {total_cases}")
    
    if total_cases > 0:
        # Check first few cases
        cases = Case.objects.all()[:5]
        print(f"\n📋 Sample Cases:")
        for i, case in enumerate(cases, 1):
            print(f"  {i}. Case ID: {case.id}")
            print(f"     Title: '{case.case_title}'")
            print(f"     Number: '{case.case_number}'")
            print(f"     Court: '{case.court.name if case.court else 'None'}'")
            print(f"     Status: '{case.status}'")
            print()
        
        # Check for missing data
        cases_with_titles = Case.objects.exclude(case_title__isnull=True).exclude(case_title='').count()
        cases_with_courts = Case.objects.exclude(court__isnull=True).count()
        cases_with_numbers = Case.objects.exclude(case_number__isnull=True).exclude(case_number='').count()
        
        print(f"📈 Data Quality:")
        print(f"   Cases with titles: {cases_with_titles}/{total_cases} ({cases_with_titles/total_cases*100:.1f}%)")
        print(f"   Cases with courts: {cases_with_courts}/{total_cases} ({cases_with_courts/total_cases*100:.1f}%)")
        print(f"   Cases with numbers: {cases_with_numbers}/{total_cases} ({cases_with_numbers/total_cases*100:.1f}%)")
        
        # Check for "N/A" values
        na_titles = Case.objects.filter(case_title__icontains='N/A').count()
        empty_titles = Case.objects.filter(case_title__isnull=True).count()
        
        print(f"\n⚠️  Data Issues:")
        print(f"   Cases with 'N/A' titles: {na_titles}")
        print(f"   Cases with NULL titles: {empty_titles}")
        
    else:
        print("❌ No cases found in database!")
    
    # Check courts
    total_courts = Court.objects.count()
    print(f"\n🏛️  Total Courts: {total_courts}")
    
    if total_courts > 0:
        courts = Court.objects.all()[:3]
        print(f"   Sample Courts:")
        for court in courts:
            print(f"     - {court.name} ({court.code})")
    
    # Check document chunks
    total_chunks = DocumentChunk.objects.count()
    embedded_chunks = DocumentChunk.objects.filter(is_embedded=True).count()
    print(f"\n📄 Document Chunks:")
    print(f"   Total chunks: {total_chunks}")
    print(f"   Embedded chunks: {embedded_chunks}")
    
    if total_chunks > 0:
        chunk = DocumentChunk.objects.first()
        print(f"   Sample chunk text: '{chunk.chunk_text[:100]}...'")
    
    # Check search metadata
    total_metadata = SearchMetadata.objects.count()
    indexed_metadata = SearchMetadata.objects.filter(is_indexed=True).count()
    print(f"\n🔍 Search Metadata:")
    print(f"   Total metadata records: {total_metadata}")
    print(f"   Indexed records: {indexed_metadata}")
    
    if total_metadata > 0:
        metadata = SearchMetadata.objects.first()
        print(f"   Sample metadata:")
        print(f"     Case ID: {metadata.case_id}")
        print(f"     Case Title: '{metadata.case_title_normalized}'")
        print(f"     Court: '{metadata.court_normalized}'")
        print(f"     Is Indexed: {metadata.is_indexed}")

if __name__ == "__main__":
    check_database()
