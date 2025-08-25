#!/usr/bin/env python
"""
PDF Processing Pipeline Test Suite
Tests for verifying the PDF processing pipeline functionality and performance.
Run these tests after running the PDF pipeline to ensure everything worked correctly.
"""

import os
import sys
import django
from pathlib import Path
import unittest
from datetime import datetime
from django.db import models

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.cases.models import (
    Case, Document, CaseDocument, DocumentText, UnifiedCaseView,
    OrdersData, CommentsData, JudgementData
)


class PDFPipelineTestSuite(unittest.TestCase):
    """Comprehensive test suite for PDF processing pipeline verification"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'issues': []
        }
    
    def tearDown(self):
        """Clean up after tests"""
        pass
    
    def test_documents_table_population(self):
        """Test that documents table is properly populated"""
        print("\n🔍 Testing Documents Table Population...")
        
        documents = Document.objects.all()
        total_documents = documents.count()
        
        if total_documents == 0:
            self.test_results['issues'].append("No documents found in documents table")
            self.test_results['failed'] += 1
            print("   ❌ No documents found")
            return
        
        # Check document properties
        downloaded_docs = documents.filter(is_downloaded=True).count()
        failed_docs = documents.filter(is_downloaded=False).count()
        
        print(f"   ✅ Total Documents: {total_documents}")
        print(f"   ✅ Downloaded: {downloaded_docs}")
        print(f"   ⚠️ Failed: {failed_docs}")
        
        # Check for required fields
        issues_found = 0
        for doc in documents:
            if not doc.file_path:
                self.test_results['issues'].append(f"Document {doc.id} missing file path")
                issues_found += 1
            
            if not doc.sha256_hash:
                self.test_results['issues'].append(f"Document {doc.id} missing SHA256 hash")
                issues_found += 1
            
            if doc.file_size <= 0:
                self.test_results['issues'].append(f"Document {doc.id} has invalid file size: {doc.file_size}")
                issues_found += 1
        
        if issues_found == 0:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1
        
        print(f"   ⚠️ Found {issues_found} issues")
    
    def test_case_document_relationships(self):
        """Test that case-document relationships are properly established"""
        print("\n🔍 Testing Case-Document Relationships...")
        
        case_documents = CaseDocument.objects.all()
        total_relationships = case_documents.count()
        
        if total_relationships == 0:
            self.test_results['issues'].append("No case-document relationships found")
            self.test_results['failed'] += 1
            print("   ❌ No relationships found")
            return
        
        print(f"   ✅ Total Relationships: {total_relationships}")
        
        # Check relationship properties
        issues_found = 0
        for rel in case_documents:
            if not rel.case:
                self.test_results['issues'].append(f"CaseDocument {rel.id} missing case reference")
                issues_found += 1
            
            if not rel.document:
                self.test_results['issues'].append(f"CaseDocument {rel.id} missing document reference")
                issues_found += 1
            
            if not rel.source_table:
                self.test_results['issues'].append(f"CaseDocument {rel.id} missing source table")
                issues_found += 1
        
        if issues_found == 0:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1
        
        print(f"   ⚠️ Found {issues_found} issues")
    
    def test_document_text_extraction(self):
        """Test that document text extraction was successful"""
        print("\n🔍 Testing Document Text Extraction...")
        
        document_texts = DocumentText.objects.all()
        total_texts = document_texts.count()
        
        if total_texts == 0:
            self.test_results['issues'].append("No document texts found")
            self.test_results['failed'] += 1
            print("   ❌ No texts found")
            return
        
        print(f"   ✅ Total Text Records: {total_texts}")
        
        # Check text extraction quality
        texts_with_content = document_texts.filter(raw_text__isnull=False).exclude(raw_text='').count()
        texts_with_clean_content = document_texts.filter(clean_text__isnull=False).exclude(clean_text='').count()
        
        print(f"   ✅ Texts with Raw Content: {texts_with_content}")
        print(f"   ✅ Texts with Clean Content: {texts_with_clean_content}")
        
        # Check extraction methods
        pymupdf_texts = document_texts.filter(extraction_method='pymupdf').count()
        ocr_texts = document_texts.filter(extraction_method='ocr').count()
        
        print(f"   📄 PyMuPDF Extractions: {pymupdf_texts}")
        print(f"   📄 OCR Extractions: {ocr_texts}")
        
        # Check for issues
        issues_found = 0
        for text in document_texts:
            if not text.raw_text and not text.clean_text:
                self.test_results['issues'].append(f"DocumentText {text.id} has no content")
                issues_found += 1
            
            if text.confidence_score and text.confidence_score < 0.5:
                self.test_results['issues'].append(f"DocumentText {text.id} has low confidence: {text.confidence_score}")
                issues_found += 1
        
        if issues_found == 0:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1
        
        print(f"   ⚠️ Found {issues_found} issues")
    
    def test_unified_case_views(self):
        """Test that unified case views are properly created"""
        print("\n🔍 Testing Unified Case Views...")
        
        unified_views = UnifiedCaseView.objects.all()
        total_views = unified_views.count()
        total_cases = Case.objects.count()
        
        print(f"   ✅ Total Cases: {total_cases}")
        print(f"   ✅ Unified Views: {total_views}")
        
        if total_views == 0:
            self.test_results['issues'].append("No unified case views found")
            self.test_results['failed'] += 1
            print("   ❌ No views found")
            return
        
        # Check coverage
        coverage_percentage = (total_views / total_cases) * 100 if total_cases > 0 else 0
        print(f"   📊 Coverage: {coverage_percentage:.1f}%")
        
        if coverage_percentage < 90:
            self.test_results['issues'].append(f"Low coverage: {coverage_percentage:.1f}%")
            self.test_results['warnings'] += 1
        
        # Check view content
        issues_found = 0
        views_with_pdfs = 0
        views_with_text = 0
        
        for view in unified_views:
            if not view.case_metadata:
                self.test_results['issues'].append(f"UnifiedCaseView {view.id} missing case metadata")
                issues_found += 1
            
            if view.has_pdf:
                views_with_pdfs += 1
            
            if view.text_extracted:
                views_with_text += 1
        
        print(f"   📄 Views with PDFs: {views_with_pdfs}")
        print(f"   📄 Views with Extracted Text: {views_with_text}")
        
        if issues_found == 0:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1
        
        print(f"   ⚠️ Found {issues_found} issues")
    
    def test_pdf_link_extraction(self):
        """Test that PDF links were properly extracted from all sources"""
        print("\n🔍 Testing PDF Link Extraction...")
        
        # Check orders_data for PDF links
        orders_with_links = OrdersData.objects.filter(view_link__isnull=False).exclude(view_link=[]).count()
        total_orders = OrdersData.objects.count()
        
        # Check comments_data for PDF links
        comments_with_links = CommentsData.objects.filter(view_link__isnull=False).exclude(view_link=[]).count()
        total_comments = CommentsData.objects.count()
        
        # Check judgement_data for PDF links
        judgements_with_links = JudgementData.objects.filter(pdf_url__isnull=False).exclude(pdf_url='').count()
        total_judgements = JudgementData.objects.count()
        
        print(f"   📄 Orders with PDF links: {orders_with_links}/{total_orders}")
        print(f"   📄 Comments with PDF links: {comments_with_links}/{total_comments}")
        print(f"   📄 Judgements with PDF links: {judgements_with_links}/{total_judgements}")
        
        # Check if links were processed
        total_expected_links = orders_with_links + comments_with_links + judgements_with_links
        total_documents = Document.objects.count()
        
        if total_expected_links > 0 and total_documents == 0:
            self.test_results['issues'].append(f"Found {total_expected_links} PDF links but no documents were downloaded")
            self.test_results['failed'] += 1
        elif total_expected_links > 0:
            self.test_results['passed'] += 1
        else:
            self.test_results['warnings'].append("No PDF links found in any source table")
            self.test_results['warnings'] += 1
    
    def test_pipeline_completeness(self):
        """Test that the complete pipeline was executed"""
        print("\n🔍 Testing Pipeline Completeness...")
        
        # Check if all pipeline steps were completed
        total_cases = Case.objects.count()
        total_documents = Document.objects.count()
        total_texts = DocumentText.objects.count()
        total_views = UnifiedCaseView.objects.count()
        
        print(f"   📊 Pipeline Statistics:")
        print(f"      Total Cases: {total_cases}")
        print(f"      Total Documents: {total_documents}")
        print(f"      Total Text Extractions: {total_texts}")
        print(f"      Total Unified Views: {total_views}")
        
        # Check pipeline flags
        views_with_flags = UnifiedCaseView.objects.filter(
            has_pdf__isnull=False,
            text_extracted__isnull=False,
            text_cleaned__isnull=False,
            metadata_complete__isnull=False
        ).count()
        
        print(f"      Views with Complete Flags: {views_with_flags}")
        
        # Assess pipeline completeness
        if total_cases > 0 and total_views > 0:
            self.test_results['passed'] += 1
            print("   ✅ Pipeline appears to be complete")
        else:
            self.test_results['issues'].append("Pipeline appears incomplete - missing core data")
            self.test_results['failed'] += 1
            print("   ❌ Pipeline appears incomplete")
    
    def test_data_integrity(self):
        """Test data integrity across the pipeline"""
        print("\n🔍 Testing Data Integrity...")
        
        issues_found = 0
        
        # Check for orphaned documents
        orphaned_docs = Document.objects.filter(case_documents__isnull=True).count()
        if orphaned_docs > 0:
            self.test_results['issues'].append(f"Found {orphaned_docs} orphaned documents")
            issues_found += 1
        
        # Check for orphaned document texts
        orphaned_texts = DocumentText.objects.filter(document__isnull=True).count()
        if orphaned_texts > 0:
            self.test_results['issues'].append(f"Found {orphaned_texts} orphaned document texts")
            issues_found += 1
        
        # Check for cases without unified views
        cases_without_views = Case.objects.filter(unified_case_view__isnull=True).count()
        if cases_without_views > 0:
            self.test_results['issues'].append(f"Found {cases_without_views} cases without unified views")
            issues_found += 1
        
        print(f"   ✅ Orphaned Documents: {orphaned_docs}")
        print(f"   ✅ Orphaned Texts: {orphaned_texts}")
        print(f"   ✅ Cases without Views: {cases_without_views}")
        
        if issues_found == 0:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1
        
        print(f"   ⚠️ Found {issues_found} integrity issues")
    
    def test_performance_metrics(self):
        """Test pipeline performance metrics"""
        print("\n🔍 Testing Performance Metrics...")
        
        # Calculate performance metrics
        total_documents = Document.objects.count()
        downloaded_docs = Document.objects.filter(is_downloaded=True).count()
        total_texts = DocumentText.objects.count()
        
        if total_documents > 0:
            download_success_rate = (downloaded_docs / total_documents) * 100
            print(f"   📊 Download Success Rate: {download_success_rate:.1f}%")
            
            if download_success_rate < 80:
                self.test_results['issues'].append(f"Low download success rate: {download_success_rate:.1f}%")
                self.test_results['warnings'] += 1
        
        if total_documents > 0:
            text_extraction_rate = (total_texts / total_documents) * 100
            print(f"   📊 Text Extraction Rate: {text_extraction_rate:.1f}%")
            
            if text_extraction_rate < 70:
                self.test_results['issues'].append(f"Low text extraction rate: {text_extraction_rate:.1f}%")
                self.test_results['warnings'] += 1
        
        # Check processing times
        texts_with_time = DocumentText.objects.filter(processing_time__isnull=False)
        if texts_with_time.exists():
            avg_processing_time = texts_with_time.aggregate(avg_time=models.Avg('processing_time'))['avg_time']
            print(f"   ⏱️ Average Processing Time: {avg_processing_time:.2f} seconds")
        
        self.test_results['passed'] += 1
    
    def generate_pipeline_report(self):
        """Generate a comprehensive pipeline report"""
        print("\n" + "="*60)
        print("📋 PDF PIPELINE TEST REPORT")
        print("="*60)
        
        print(f"✅ Tests Passed: {self.test_results['passed']}")
        print(f"❌ Tests Failed: {self.test_results['failed']}")
        print(f"⚠️ Warnings: {self.test_results['warnings']}")
        
        if self.test_results['issues']:
            print(f"\n🔍 Issues Found:")
            for i, issue in enumerate(self.test_results['issues'], 1):
                print(f"   {i}. {issue}")
        
        # Overall assessment
        total_tests = self.test_results['passed'] + self.test_results['failed']
        if total_tests > 0:
            pass_rate = (self.test_results['passed'] / total_tests) * 100
            print(f"\n📊 Overall Pass Rate: {pass_rate:.1f}%")
            
            if pass_rate >= 90:
                print("🎉 EXCELLENT: Pipeline is working perfectly!")
            elif pass_rate >= 80:
                print("✅ GOOD: Pipeline is working well")
            elif pass_rate >= 70:
                print("⚠️ FAIR: Pipeline has some issues")
            else:
                print("❌ POOR: Pipeline has significant issues")
        
        print(f"\n📅 Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)


def run_pdf_pipeline_tests():
    """Run all PDF pipeline tests and generate report"""
    print("🧪 RUNNING PDF PIPELINE TEST SUITE")
    print("="*60)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    test_loader = unittest.TestLoader()
    
    # Add all test methods
    test_methods = [
        'test_documents_table_population',
        'test_case_document_relationships',
        'test_document_text_extraction',
        'test_unified_case_views',
        'test_pdf_link_extraction',
        'test_pipeline_completeness',
        'test_data_integrity',
        'test_performance_metrics'
    ]
    
    for method in test_methods:
        test_suite.addTest(test_loader.loadTestsFromName(method, PDFPipelineTestSuite))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Generate report
    test_instance = PDFPipelineTestSuite()
    test_instance.test_results = {
        'passed': len(result.passed) if hasattr(result, 'passed') else 0,
        'failed': len(result.failures) + len(result.errors),
        'warnings': 0,
        'issues': []
    }
    
    # Collect issues from failures
    for failure in result.failures:
        test_instance.test_results['issues'].append(f"Test failed: {failure[0]}")
    
    for error in result.errors:
        test_instance.test_results['issues'].append(f"Test error: {error[0]}")
    
    test_instance.generate_pipeline_report()
    
    return test_instance.test_results


if __name__ == '__main__':
    run_pdf_pipeline_tests()
