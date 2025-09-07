#!/usr/bin/env python
"""
Check Database Directly - Look for the Libya case in the database
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def check_database():
    """Check the database directly for the Libya case"""
    print("🔍 CHECKING DATABASE DIRECTLY FOR LIBYA CASE")
    print("=" * 60)
    
    from apps.cases.models import Case
    
    # Search for Libya case in database
    print("\n1️⃣ Searching for 'libya' in case titles...")
    libya_cases = Case.objects.filter(case_title__icontains='libya')
    print(f"Found {libya_cases.count()} cases with 'libya' in title")
    
    for case in libya_cases:
        print(f"   Case: {case.case_number}")
        print(f"   Title: {case.case_title}")
        print(f"   Court: {case.court}")
        print(f"   Status: {case.status}")
        print()
    
    # Search for 'civil judge' cases
    print("\n2️⃣ Searching for 'civil judge' in case titles...")
    civil_judge_cases = Case.objects.filter(case_title__icontains='civil judge')
    print(f"Found {civil_judge_cases.count()} cases with 'civil judge' in title")
    
    for case in civil_judge_cases[:5]:  # Show first 5
        print(f"   Case: {case.case_number}")
        print(f"   Title: {case.case_title}")
        print()
    
    # Search for 'west islamabad' cases
    print("\n3️⃣ Searching for 'west islamabad' in case titles...")
    west_islamabad_cases = Case.objects.filter(case_title__icontains='west islamabad')
    print(f"Found {west_islamabad_cases.count()} cases with 'west islamabad' in title")
    
    for case in west_islamabad_cases:
        print(f"   Case: {case.case_number}")
        print(f"   Title: {case.case_title}")
        print()
    
    # Check if the exact case exists
    print("\n4️⃣ Searching for exact case title...")
    exact_case = Case.objects.filter(
        case_title__icontains='state of libya'
    ).filter(
        case_title__icontains='civil judge'
    ).filter(
        case_title__icontains='west islamabad'
    )
    
    print(f"Found {exact_case.count()} cases matching all terms")
    for case in exact_case:
        print(f"   Case: {case.case_number}")
        print(f"   Title: {case.case_title}")
        print(f"   Court: {case.court}")
        print(f"   Status: {case.status}")
        print()
    
    # Check search metadata
    print("\n5️⃣ Checking search metadata...")
    from search_indexing.models import SearchMetadata
    
    # Look for Libya in search metadata
    libya_metadata = SearchMetadata.objects.filter(
        case_title__icontains='libya'
    )
    print(f"Found {libya_metadata.count()} search metadata entries with 'libya'")
    
    for metadata in libya_metadata:
        print(f"   Case ID: {metadata.case_id}")
        print(f"   Title: {metadata.case_title}")
        print(f"   Enhanced: {metadata.enhanced_metadata_extracted}")
        print()
    
    print("\n" + "=" * 60)
    print("🔍 ANALYSIS:")
    if libya_cases.exists():
        print("✅ Libya case exists in database")
        print("❌ But not appearing in search results")
        print("🔧 Issue: Search indexing or ranking problem")
    else:
        print("❌ Libya case not found in database")
        print("🔧 Issue: Case might not be properly scraped/indexed")

if __name__ == "__main__":
    check_database()
