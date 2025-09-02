#!/usr/bin/env python3
"""
Test Content Search
Check what's actually in DocumentChunks for specific terms
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from search_indexing.models import DocumentChunk
from apps.cases.models import Case

def test_content_search():
    """Test content search in DocumentChunks"""
    print("🔍 TESTING CONTENT SEARCH IN DOCUMENT CHUNKS")
    print("=" * 60)
    
    test_terms = ["CPC", "CrPC", "2025", "PPC", "302"]
    
    for term in test_terms:
        print(f"\n📝 Testing term: '{term}'")
        print("-" * 40)
        
        # Search in DocumentChunks
        chunks = DocumentChunk.objects.filter(
            chunk_text__icontains=term,
            is_embedded=True
        )[:5]  # Limit to 5 results
        
        print(f"   Found {chunks.count()} chunks containing '{term}'")
        
        if chunks.exists():
            for i, chunk in enumerate(chunks):
                case = Case.objects.get(id=chunk.case_id)
                print(f"   Chunk {i+1}:")
                print(f"      Case: {case.case_number} - {case.case_title}")
                print(f"      Text preview: {chunk.chunk_text[:100]}...")
                print(f"      Chunk index: {chunk.chunk_index}")
        else:
            print(f"   ❌ No chunks found containing '{term}'")
            
            # Try case-insensitive search
            chunks_ci = DocumentChunk.objects.filter(
                chunk_text__icontains=term.lower(),
                is_embedded=True
            )[:3]
            
            if chunks_ci.exists():
                print(f"   🔍 Found {chunks_ci.count()} chunks with case-insensitive search")
                for i, chunk in enumerate(chunks_ci):
                    case = Case.objects.get(id=chunk.case_id)
                    print(f"      Case {i+1}: {case.case_number}")
            else:
                print(f"   ❌ No chunks found even with case-insensitive search")

if __name__ == "__main__":
    test_content_search()
