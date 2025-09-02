#!/usr/bin/env python3
"""
Debug Suggestions
Check what data exists for suggestions and why they're not working
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.cases.models import Case, Term, TermOccurrence
from django.db.models import Count

def debug_suggestions():
    """Debug what data exists for suggestions"""
    print("🔍 DEBUGGING SUGGESTIONS")
    print("=" * 60)
    
    try:
        # Check Term model
        print("📊 Term Model:")
        try:
            total_terms = Term.objects.count()
            print(f"   Total terms: {total_terms}")
            
            if total_terms > 0:
                term_types = Term.objects.values('type').annotate(count=Count('id')).order_by('-count')
                print(f"   Term types:")
                for term_type in term_types:
                    print(f"      {term_type['type']}: {term_type['count']}")
                
                # Check a few sample terms
                sample_terms = Term.objects.all()[:3]
                print(f"\n   Sample terms:")
                for term in sample_terms:
                    print(f"      {term.canonical} (type: {term.type}, count: {term.occurrence_count})")
            else:
                print("   ❌ No terms found in Term model")
                
        except Exception as e:
            print(f"   ❌ Term model error: {e}")
        
        # Check TermOccurrence model
        print(f"\n📊 TermOccurrence Model:")
        try:
            total_occurrences = TermOccurrence.objects.count()
            print(f"   Total occurrences: {total_occurrences}")
            
            if total_occurrences > 0:
                occurrence_types = TermOccurrence.objects.values('term__type').annotate(count=Count('id')).order_by('-count')
                print(f"   Occurrence types:")
                for occ_type in occurrence_types:
                    print(f"      {occ_type['term__type']}: {occ_type['count']}")
            else:
                print("   ❌ No term occurrences found")
                
        except Exception as e:
            print(f"   ❌ TermOccurrence model error: {e}")
        
        # Check Case model for judge suggestions
        print(f"\n📊 Case Model (Judge Suggestions):")
        try:
            total_cases = Case.objects.count()
            print(f"   Total cases: {total_cases}")
            
            if total_cases > 0:
                # Check bench field
                cases_with_bench = Case.objects.exclude(bench__isnull=True).exclude(bench='').count()
                print(f"   Cases with bench: {cases_with_bench}")
                
                if cases_with_bench > 0:
                    sample_benches = Case.objects.exclude(bench__isnull=True).exclude(bench='').values('bench').annotate(count=Count('id')).order_by('-count')[:5]
                    print(f"   Sample benches:")
                    for bench in sample_benches:
                        print(f"      {bench['bench']}: {bench['count']} cases")
                else:
                    print("   ❌ No cases with bench information")
                    
        except Exception as e:
            print(f"   ❌ Case model error: {e}")
        
        # Test specific queries
        print(f"\n🔍 Testing Specific Queries:")
        
        # Test "PPC" for citations
        print(f"\n   Testing 'PPC' for citations:")
        try:
            ppc_citations = Term.objects.filter(
                type='citation',
                canonical__icontains='PPC'
            )[:3]
            print(f"      PPC citations found: {len(ppc_citations)}")
            for citation in ppc_citations:
                print(f"         {citation.canonical}")
        except Exception as e:
            print(f"      ❌ Error: {e}")
        
        # Test "302" for sections
        print(f"\n   Testing '302' for sections:")
        try:
            section_302 = Term.objects.filter(
                type='section',
                canonical__icontains='302'
            )[:3]
            print(f"      Section 302 found: {len(section_302)}")
            for section in section_302:
                print(f"         {section.canonical}")
        except Exception as e:
            print(f"      ❌ Error: {e}")
        
        # Test "Chief" for judges
        print(f"\n   Testing 'Chief' for judges:")
        try:
            chief_judges = Case.objects.filter(
                bench__icontains='Chief'
            ).values('bench').annotate(count=Count('id')).order_by('-count')[:3]
            print(f"      Chief judges found: {len(chief_judges)}")
            for judge in chief_judges:
                print(f"         {judge['bench']}: {judge['count']} cases")
        except Exception as e:
            print(f"      ❌ Error: {e}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_suggestions()
