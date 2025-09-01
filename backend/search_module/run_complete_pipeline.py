#!/usr/bin/env python
"""
Complete Data Processing Pipeline
Runs all steps automatically after scraping new data
"""

import os
import sys
import django
import time
import subprocess
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def run_command(command, description):
    """Run a Django management command and return success status"""
    print(f"\n{'='*60}")
    print(f"🚀 STEP: {description}")
    print(f"📋 Command: {command}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            command.split(),
            capture_output=True,
            text=True,
            check=True
        )
        
        execution_time = time.time() - start_time
        print(f"✅ SUCCESS: {description}")
        print(f"⏱️ Execution Time: {execution_time:.2f} seconds")
        
        if result.stdout:
            print(f"📤 Output: {result.stdout[-500:]}...")  # Last 500 chars
        
        return True, execution_time
        
    except subprocess.CalledProcessError as e:
        execution_time = time.time() - start_time
        print(f"❌ ERROR: {description}")
        print(f"⏱️ Execution Time: {execution_time:.2f} seconds")
        print(f"🔍 Error Code: {e.returncode}")
        print(f"📤 Output: {e.stdout}")
        print(f"📥 Error: {e.stderr}")
        return False, execution_time

def check_system_status():
    """Check current system status before running pipeline"""
    print(f"\n🔍 SYSTEM STATUS CHECK")
    print(f"{'='*60}")
    
    from apps.cases.models import Case, UnifiedCaseView
    from search_indexing.models import FacetTerm, FacetMapping, DocumentChunk, SearchMetadata, VectorIndex, KeywordIndex
    
    # Check data counts
    total_cases = Case.objects.count()
    unified_views = UnifiedCaseView.objects.count()
    facet_terms = FacetTerm.objects.count()
    facet_mappings = FacetMapping.objects.count()
    document_chunks = DocumentChunk.objects.count()
    search_metadata = SearchMetadata.objects.count()
    
    # Check index status
    vector_indexes = VectorIndex.objects.filter(is_active=True, is_built=True).count()
    keyword_indexes = KeywordIndex.objects.filter(is_active=True, is_built=True).count()
    
    print(f"📊 Current System Status:")
    print(f"   Total Cases: {total_cases}")
    print(f"   Unified Views: {unified_views}")
    print(f"   Facet Terms: {facet_terms}")
    print(f"   Facet Mappings: {facet_mappings}")
    print(f"   Document Chunks: {document_chunks}")
    print(f"   Search Metadata: {search_metadata}")
    print(f"   Vector Indexes: {vector_indexes}")
    print(f"   Keyword Indexes: {keyword_indexes}")
    
    return {
        'total_cases': total_cases,
        'unified_views': unified_views,
        'facet_terms': facet_terms,
        'facet_mappings': facet_mappings,
        'document_chunks': document_chunks,
        'search_metadata': search_metadata,
        'vector_indexes': vector_indexes,
        'keyword_indexes': keyword_indexes
    }

def main():
    """Run the complete data processing pipeline"""
    print(f"🎯 COMPLETE DATA PROCESSING PIPELINE")
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")
    
    # Check initial system status
    initial_status = check_system_status()
    
    # Pipeline steps
    pipeline_steps = [
        {
            'command': 'python manage.py run_complete_pipeline --force',
            'description': 'PDF Processing Pipeline',
            'expected_output': 'Unified case views created'
        },
        {
            'command': 'python manage.py extract_legal_vocabulary --force',
            'description': 'Enhanced Vocabulary Extraction',
            'expected_output': 'Legal vocabulary extracted'
        },
        {
            'command': 'python manage.py build_normalized_facets --force',
            'description': 'Normalized Facet System',
            'expected_output': 'Normalized facets built'
        },
        {
            'command': 'python manage.py build_indexes --vector-only --force',
            'description': 'Vector Index Building',
            'expected_output': 'Vector index built'
        },
        {
            'command': 'python manage.py build_indexes --keyword-only --force',
            'description': 'Keyword Index Building',
            'expected_output': 'Keyword index built'
        },
        {
            'command': 'python manage.py build_indexes --force',
            'description': 'Hybrid Search System',
            'expected_output': 'Hybrid search system ready'
        }
    ]
    
    # Run pipeline steps
    total_time = 0
    successful_steps = 0
    failed_steps = []
    
    for i, step in enumerate(pipeline_steps, 1):
        print(f"\n📋 STEP {i}/{len(pipeline_steps)}: {step['description']}")
        
        success, execution_time = run_command(step['command'], step['description'])
        total_time += execution_time
        
        if success:
            successful_steps += 1
        else:
            failed_steps.append(step['description'])
    
    # Check final system status
    print(f"\n🔍 FINAL SYSTEM STATUS CHECK")
    print(f"{'='*60}")
    final_status = check_system_status()
    
    # Calculate improvements
    improvements = {
        'unified_views': final_status['unified_views'] - initial_status['unified_views'],
        'facet_terms': final_status['facet_terms'] - initial_status['facet_terms'],
        'facet_mappings': final_status['facet_mappings'] - initial_status['facet_mappings'],
        'document_chunks': final_status['document_chunks'] - initial_status['document_chunks'],
        'search_metadata': final_status['search_metadata'] - initial_status['search_metadata'],
        'vector_indexes': final_status['vector_indexes'] - initial_status['vector_indexes'],
        'keyword_indexes': final_status['keyword_indexes'] - initial_status['keyword_indexes']
    }
    
    # Pipeline summary
    print(f"\n🎉 PIPELINE COMPLETION SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Successful Steps: {successful_steps}/{len(pipeline_steps)}")
    print(f"❌ Failed Steps: {len(failed_steps)}")
    print(f"⏱️ Total Execution Time: {total_time:.2f} seconds ({total_time/60:.2f} minutes)")
    
    if failed_steps:
        print(f"\n❌ Failed Steps:")
        for step in failed_steps:
            print(f"   - {step}")
    
    print(f"\n📈 System Improvements:")
    for metric, improvement in improvements.items():
        if improvement > 0:
            print(f"   ✅ {metric.replace('_', ' ').title()}: +{improvement}")
    
    print(f"\n🚀 Final System Status:")
    print(f"   📊 Total Cases: {final_status['total_cases']}")
    print(f"   🏷️ Facet Terms: {final_status['facet_terms']}")
    print(f"   🔗 Facet Mappings: {final_status['facet_mappings']}")
    print(f"   📄 Document Chunks: {final_status['document_chunks']}")
    print(f"   🔍 Search Metadata: {final_status['search_metadata']}")
    print(f"   🧠 Vector Indexes: {final_status['vector_indexes']}")
    print(f"   🔤 Keyword Indexes: {final_status['keyword_indexes']}")
    
    if successful_steps == len(pipeline_steps):
        print(f"\n🎉 SUCCESS: Complete pipeline executed successfully!")
        print(f"🚀 Your indexing system is ready for production use!")
    else:
        print(f"\n⚠️ WARNING: Some pipeline steps failed. Check the errors above.")
    
    print(f"\n🕐 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
