#!/usr/bin/env python3
"""
Test script to check if snippet service is working properly
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

from search_indexing.services.snippet_service import SnippetService
from apps.cases.models import Case

def test_snippet_service():
    """Test the snippet service"""
    print("🧪 TESTING SNIPPET SERVICE")
    print("=" * 50)
    
    # Get a case that should have content
    case = Case.objects.first()
    if not case:
        print("❌ No cases found in database")
        return
    
    print(f"📋 Testing with case: {case.case_title}")
    print(f"   Case ID: {case.id}")
    print(f"   Court: {case.court.name if case.court else 'None'}")
    
    # Initialize snippet service
    snippet_service = SnippetService()
    
    # Test query
    query = "murder case"
    query_info = {
        'normalized_query': 'murder case',
        'citations': [],
        'exact_identifiers': []
    }
    
    print(f"\n🔍 Generating snippets for query: '{query}'")
    
    try:
        snippets = snippet_service.generate_snippets(
            case_id=case.id,
            query=query,
            query_info=query_info,
            max_snippets=3
        )
        
        print(f"📄 Generated {len(snippets)} snippets:")
        
        for i, snippet in enumerate(snippets, 1):
            print(f"\n   Snippet {i}:")
            print(f"     Type: {snippet.get('type', 'unknown')}")
            print(f"     Relevance Score: {snippet.get('relevance_score', 0):.3f}")
            print(f"     Text: {snippet.get('text', 'No text')[:100]}...")
            print(f"     Page: {snippet.get('page_number', 'N/A')}")
        
        if not snippets:
            print("❌ No snippets generated - this might be the issue!")
            
            # Check if case has document text
            from apps.cases.models import DocumentText
            doc_texts = DocumentText.objects.filter(document__case_id=case.id)
            print(f"\n🔍 DocumentText records for case: {doc_texts.count()}")
            
            if doc_texts.exists():
                doc_text = doc_texts.first()
                print(f"   First DocumentText:")
                print(f"     Clean text: {doc_text.clean_text[:100] if doc_text.clean_text else 'None'}...")
                print(f"     Raw text: {doc_text.raw_text[:100] if doc_text.raw_text else 'None'}...")
            
            # Check if case has document chunks
            from search_indexing.models import DocumentChunk
            chunks = DocumentChunk.objects.filter(case_id=case.id)
            print(f"\n🔍 DocumentChunk records for case: {chunks.count()}")
            
            if chunks.exists():
                chunk = chunks.first()
                print(f"   First DocumentChunk:")
                print(f"     Text: {chunk.chunk_text[:100] if chunk.chunk_text else 'None'}...")
                print(f"     Is embedded: {chunk.is_embedded}")
        
    except Exception as e:
        print(f"❌ Error generating snippets: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_snippet_service()
