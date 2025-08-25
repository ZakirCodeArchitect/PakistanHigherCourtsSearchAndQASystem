#!/usr/bin/env python
"""
Data Quality Verification Test Suite

This test suite provides comprehensive verification of data quality and pipeline performance.
Run this after any scraping session to ensure data integrity and quality.

Usage:
    python manage.py test tests.test_data_quality_verification
    python -m pytest tests/test_data_quality_verification.py -v
"""

import os
import sys
import django
from pathlib import Path
from datetime import datetime
import json
from typing import Dict, List, Tuple, Any

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import TestCase
from django.db import connection
from apps.cases.models import (
    Case, OrdersData, CommentsData, CaseDetail, PartiesDetailData,
    Document, DocumentText, UnifiedCaseView
)
from apps.cases.services.data_cleaner import DataCleaner


class DataQualityVerificationTest(TestCase):
    """
    Comprehensive data quality verification test suite.
    
    This test class provides methods to verify:
    1. Data completeness and integrity
    2. Data cleaning effectiveness
    3. Pipeline performance
    4. Data consistency across tables
    5. Quality metrics and scores
    """
    
    def setUp(self):
        """Set up test environment"""
        self.cleaner = DataCleaner()
        self.test_results = {
            'timestamp': datetime.now().isoformat(),
            'total_cases': 0,
            'data_quality_scores': {},
            'cleaning_effectiveness': {},
            'pipeline_performance': {},
            'issues_found': [],
            'recommendations': []
        }
    
    def test_data_completeness(self):
        """Test data completeness across all tables"""
        print("\n🔍 TESTING DATA COMPLETENESS")
        print("=" * 50)
        
        # Count records in each table
        counts = {
            'cases': Case.objects.count(),
            'orders': OrdersData.objects.count(),
            'comments': CommentsData.objects.count(),
            'case_details': CaseDetail.objects.count(),
            'parties': PartiesDetailData.objects.count(),
            'documents': Document.objects.count(),
            'document_texts': DocumentText.objects.count(),
            'unified_views': UnifiedCaseView.objects.count(),
        }
        
        self.test_results['total_cases'] = counts['cases']
        
        print(f"📊 Database Statistics:")
        for table, count in counts.items():
            print(f"   {table.replace('_', ' ').title()}: {count}")
        
        # Check for empty tables
        empty_tables = [table for table, count in counts.items() if count == 0]
        if empty_tables:
            self.test_results['issues_found'].append(f"Empty tables: {', '.join(empty_tables)}")
            print(f"⚠️ Empty tables found: {', '.join(empty_tables)}")
        else:
            print("✅ All tables have data")
        
        # Check case coverage
        cases_with_orders = Case.objects.filter(orders_data__isnull=False).distinct().count()
        cases_with_comments = Case.objects.filter(comments_data__isnull=False).distinct().count()
        cases_with_details = Case.objects.filter(case_detail__isnull=False).count()
        cases_with_parties = Case.objects.filter(parties_detail_data__isnull=False).distinct().count()
        
        coverage = {
            'orders_coverage': (cases_with_orders / counts['cases']) * 100 if counts['cases'] > 0 else 0,
            'comments_coverage': (cases_with_comments / counts['cases']) * 100 if counts['cases'] > 0 else 0,
            'details_coverage': (cases_with_details / counts['cases']) * 100 if counts['cases'] > 0 else 0,
            'parties_coverage': (cases_with_parties / counts['cases']) * 100 if counts['cases'] > 0 else 0,
        }
        
        print(f"\n📈 Case Coverage:")
        for metric, percentage in coverage.items():
            print(f"   {metric.replace('_', ' ').title()}: {percentage:.1f}%")
            if percentage < 50:
                self.test_results['issues_found'].append(f"Low {metric}: {percentage:.1f}%")
        
        self.test_results['data_quality_scores']['completeness'] = coverage
    
    def test_data_cleaning_effectiveness(self):
        """Test the effectiveness of data cleaning"""
        print("\n🧹 TESTING DATA CLEANING EFFECTIVENESS")
        print("=" * 50)
        
        # Test case title quality
        case_titles = list(Case.objects.values_list('case_title', flat=True))
        title_scores = [self.cleaner.get_data_quality_score(title) for title in case_titles]
        avg_title_score = sum(title_scores) / len(title_scores) if title_scores else 0
        
        # Test order text quality
        order_texts = list(OrdersData.objects.values_list('short_order', flat=True))
        order_scores = [self.cleaner.get_data_quality_score(text) for text in order_texts]
        avg_order_score = sum(order_scores) / len(order_scores) if order_scores else 0
        
        # Check for standardized separators
        cases_with_vs = Case.objects.filter(case_title__icontains=' VS ').count()
        total_cases = Case.objects.count()
        separator_standardization = (cases_with_vs / total_cases) * 100 if total_cases > 0 else 0
        
        # Check for expanded legal terms
        orders_with_full_terms = OrdersData.objects.filter(
            short_order__icontains='District & Sessions Judge'
        ).count()
        total_orders = OrdersData.objects.count()
        legal_term_expansion = (orders_with_full_terms / total_orders) * 100 if total_orders > 0 else 0
        
        cleaning_metrics = {
            'avg_case_title_score': avg_title_score,
            'avg_order_text_score': avg_order_score,
            'separator_standardization': separator_standardization,
            'legal_term_expansion': legal_term_expansion,
        }
        
        print(f"📊 Cleaning Effectiveness Metrics:")
        for metric, value in cleaning_metrics.items():
            print(f"   {metric.replace('_', ' ').title()}: {value:.2f}")
            if 'score' in metric and value < 0.7:
                self.test_results['issues_found'].append(f"Low {metric}: {value:.2f}")
        
        self.test_results['cleaning_effectiveness'] = cleaning_metrics
        
        # Check for specific cleaning issues
        self._check_cleaning_issues()
    
    def _check_cleaning_issues(self):
        """Check for specific cleaning issues"""
        print(f"\n🔍 Checking for Cleaning Issues:")
        
        # Check for overly short titles
        short_titles = [title for title in Case.objects.values_list('case_title', flat=True) 
                       if len(title.strip()) < 5]
        if short_titles:
            print(f"   ⚠️ Found {len(short_titles)} very short titles")
            self.test_results['issues_found'].append(f"{len(short_titles)} very short case titles")
        
        # Check for empty fields
        empty_titles = Case.objects.filter(case_title__isnull=True).count()
        if empty_titles > 0:
            print(f"   ⚠️ Found {empty_titles} cases with null titles")
            self.test_results['issues_found'].append(f"{empty_titles} cases with null titles")
        
        # Check for suspicious patterns
        suspicious_cases = Case.objects.filter(
            case_title__in=['. VS .', 'VS', '']
        ).count()
        if suspicious_cases > 0:
            print(f"   ⚠️ Found {suspicious_cases} suspicious case titles")
            self.test_results['issues_found'].append(f"{suspicious_cases} suspicious case titles")
        
        # Check for preserved important information
        cases_with_others = Case.objects.filter(case_title__icontains='& others').count()
        cases_with_and_others = Case.objects.filter(case_title__icontains='and others').count()
        total_preserved = cases_with_others + cases_with_and_others
        print(f"   ✅ {total_preserved} cases properly preserved '& others' information")
    
    def test_data_consistency(self):
        """Test data consistency across tables"""
        print("\n🔄 TESTING DATA CONSISTENCY")
        print("=" * 50)
        
        # Check for orphaned records
        orphaned_orders = OrdersData.objects.filter(case__isnull=True).count()
        orphaned_comments = CommentsData.objects.filter(case__isnull=True).count()
        orphaned_parties = PartiesDetailData.objects.filter(case__isnull=True).count()
        
        consistency_issues = []
        if orphaned_orders > 0:
            consistency_issues.append(f"{orphaned_orders} orphaned orders")
        if orphaned_comments > 0:
            consistency_issues.append(f"{orphaned_comments} orphaned comments")
        if orphaned_parties > 0:
            consistency_issues.append(f"{orphaned_parties} orphaned parties")
        
        if consistency_issues:
            print(f"⚠️ Consistency issues found: {', '.join(consistency_issues)}")
            self.test_results['issues_found'].extend(consistency_issues)
        else:
            print("✅ No orphaned records found")
        
        # Check for duplicate case numbers
        from django.db.models import Count
        duplicate_cases = Case.objects.values('case_number').annotate(
            count=Count('id')
        ).filter(count__gt=1)
        
        if duplicate_cases.exists():
            print(f"⚠️ Found {len(duplicate_cases)} duplicate case numbers")
            self.test_results['issues_found'].append(f"{len(duplicate_cases)} duplicate case numbers")
        else:
            print("✅ No duplicate case numbers found")
        
        # Check status consistency
        status_values = list(Case.objects.values_list('status', flat=True).distinct())
        print(f"📋 Status values found: {', '.join(status_values)}")
        
        # Check bench consistency
        bench_values = list(Case.objects.values_list('bench', flat=True).distinct())
        print(f"👨‍⚖️ Bench values found: {len(bench_values)} unique benches")
    
    def test_pipeline_performance(self):
        """Test pipeline performance and completeness"""
        print("\n⚡ TESTING PIPELINE PERFORMANCE")
        print("=" * 50)
        
        # Check PDF processing pipeline
        total_documents = Document.objects.count()
        downloaded_documents = Document.objects.filter(is_downloaded=True).count()
        documents_with_text = Document.objects.filter(document_texts__isnull=False).distinct().count()
        
        # Check unified views
        total_unified_views = UnifiedCaseView.objects.count()
        complete_unified_views = UnifiedCaseView.objects.filter(
            case_metadata__isnull=False
        ).exclude(case_metadata={}).count()
        
        pipeline_metrics = {
            'documents_downloaded': (downloaded_documents / total_documents) * 100 if total_documents > 0 else 0,
            'documents_with_text': (documents_with_text / total_documents) * 100 if total_documents > 0 else 0,
            'unified_views_complete': (complete_unified_views / total_unified_views) * 100 if total_unified_views > 0 else 0,
        }
        
        print(f"📊 Pipeline Performance Metrics:")
        for metric, value in pipeline_metrics.items():
            print(f"   {metric.replace('_', ' ').title()}: {value:.1f}%")
            if value < 80:
                self.test_results['issues_found'].append(f"Low {metric}: {value:.1f}%")
        
        self.test_results['pipeline_performance'] = pipeline_metrics
        
        # Check for pipeline issues
        if total_documents > 0 and downloaded_documents == 0:
            self.test_results['issues_found'].append("No documents downloaded")
        if total_unified_views == 0:
            self.test_results['issues_found'].append("No unified views created")
    
    def test_data_quality_scoring(self):
        """Test overall data quality scoring"""
        print("\n📊 TESTING DATA QUALITY SCORING")
        print("=" * 50)
        
        # Calculate quality scores for different data types
        quality_scores = {}
        
        # Case titles quality
        case_titles = list(Case.objects.values_list('case_title', flat=True))
        title_scores = [self.cleaner.get_data_quality_score(title) for title in case_titles]
        quality_scores['case_titles'] = {
            'avg_score': sum(title_scores) / len(title_scores) if title_scores else 0,
            'min_score': min(title_scores) if title_scores else 0,
            'max_score': max(title_scores) if title_scores else 0,
            'scores_above_0.8': len([s for s in title_scores if s > 0.8]),
            'total_samples': len(title_scores)
        }
        
        # Order texts quality
        order_texts = list(OrdersData.objects.values_list('short_order', flat=True))
        order_scores = [self.cleaner.get_data_quality_score(text) for text in order_texts]
        quality_scores['order_texts'] = {
            'avg_score': sum(order_scores) / len(order_scores) if order_scores else 0,
            'min_score': min(order_scores) if order_scores else 0,
            'max_score': max(order_scores) if order_scores else 0,
            'scores_above_0.8': len([s for s in order_scores if s > 0.8]),
            'total_samples': len(order_scores)
        }
        
        print(f"📈 Quality Scores:")
        for data_type, scores in quality_scores.items():
            print(f"   {data_type.replace('_', ' ').title()}:")
            print(f"     Average: {scores['avg_score']:.3f}")
            print(f"     Range: {scores['min_score']:.3f} - {scores['max_score']:.3f}")
            print(f"     High Quality (>0.8): {scores['scores_above_0.8']}/{scores['total_samples']}")
        
        self.test_results['data_quality_scores']['detailed_scores'] = quality_scores
    
    def generate_recommendations(self):
        """Generate recommendations based on test results"""
        print("\n💡 GENERATING RECOMMENDATIONS")
        print("=" * 50)
        
        recommendations = []
        
        # Check data volume
        if self.test_results['total_cases'] < 10:
            recommendations.append("Consider scraping more data for better analysis")
        
        # Check cleaning effectiveness
        cleaning_metrics = self.test_results.get('cleaning_effectiveness', {})
        if cleaning_metrics.get('avg_case_title_score', 1) < 0.8:
            recommendations.append("Review case title cleaning logic")
        
        # Check pipeline performance
        pipeline_metrics = self.test_results.get('pipeline_performance', {})
        if pipeline_metrics.get('documents_downloaded', 100) < 80:
            recommendations.append("Check PDF download pipeline")
        
        # Check for issues
        if self.test_results['issues_found']:
            recommendations.append("Address the identified issues before proceeding")
        
        # Add positive feedback
        if not self.test_results['issues_found']:
            recommendations.append("Data quality is excellent! Ready for advanced processing")
        
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec}")
        
        self.test_results['recommendations'] = recommendations
    
    def save_test_report(self):
        """Save test results to a JSON report"""
        report_path = Path(__file__).parent / 'reports' / f'data_quality_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        print(f"\n📄 Test report saved to: {report_path}")
        return report_path
    
    def test_comprehensive_verification(self):
        """Run comprehensive data quality verification"""
        print("🚀 STARTING COMPREHENSIVE DATA QUALITY VERIFICATION")
        print("=" * 70)
        
        # Run all verification tests
        self.test_data_completeness()
        self.test_data_cleaning_effectiveness()
        self.test_data_consistency()
        self.test_pipeline_performance()
        self.test_data_quality_scoring()
        self.generate_recommendations()
        
        # Save report
        report_path = self.save_test_report()
        
        # Print summary
        print("\n" + "=" * 70)
        print("📋 VERIFICATION SUMMARY")
        print("=" * 70)
        
        print(f"Total Cases: {self.test_results['total_cases']}")
        print(f"Issues Found: {len(self.test_results['issues_found'])}")
        print(f"Recommendations: {len(self.test_results['recommendations'])}")
        
        if self.test_results['issues_found']:
            print(f"\n⚠️ Issues Found:")
            for issue in self.test_results['issues_found']:
                print(f"   • {issue}")
        else:
            print(f"\n✅ No issues found!")
        
        print(f"\n💡 Key Recommendations:")
        for rec in self.test_results['recommendations'][:3]:  # Show top 3
            print(f"   • {rec}")
        
        # Assertions for automated testing
        self.assertGreater(self.test_results['total_cases'], 0, "No cases found in database")
        self.assertLess(len(self.test_results['issues_found']), 10, "Too many issues found")
        
        print(f"\n🎉 Verification completed! Report saved to: {report_path}")


class QuickDataQualityCheck(TestCase):
    """
    Quick data quality check for rapid verification.
    Use this for quick checks during development.
    """
    
    def test_quick_verification(self):
        """Quick verification of essential data quality metrics"""
        print("\n⚡ QUICK DATA QUALITY CHECK")
        print("=" * 40)
        
        # Essential checks
        total_cases = Case.objects.count()
        cases_with_titles = Case.objects.exclude(case_title__isnull=True).exclude(case_title='').count()
        cases_with_vs = Case.objects.filter(case_title__icontains=' VS ').count()
        
        print(f"Total Cases: {total_cases}")
        print(f"Cases with Titles: {cases_with_titles}")
        print(f"Cases with 'VS' Separator: {cases_with_vs}")
        
        # Basic assertions
        self.assertGreater(total_cases, 0, "No cases found")
        self.assertEqual(cases_with_titles, total_cases, "Some cases missing titles")
        self.assertGreater(cases_with_vs, total_cases * 0.8, "Most cases should have 'VS' separator")
        
        print("✅ Quick verification passed!")


if __name__ == '__main__':
    # Run the test directly
    import django
    django.setup()
    
    test = DataQualityVerificationTest()
    test.setUp()
    test.test_comprehensive_verification()
