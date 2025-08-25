#!/usr/bin/env python
"""
Data Quality Test Suite
Tests for verifying the quality and consistency of scraped case data.
Run these tests after scraping new data to ensure quality standards are met.
"""

import os
import sys
import django
from pathlib import Path
import unittest
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.cases.models import Case, OrdersData, CommentsData, CaseDetail, PartiesDetailData
from apps.cases.services.data_cleaner import DataCleaner


class DataQualityTestSuite(unittest.TestCase):
    """Comprehensive test suite for data quality verification"""
    
    def setUp(self):
        """Set up test environment"""
        self.cleaner = DataCleaner()
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'issues': []
        }
    
    def tearDown(self):
        """Clean up after tests"""
        pass
    
    def test_case_titles_consistency(self):
        """Test that case titles follow consistent formatting"""
        print("\n🔍 Testing Case Titles Consistency...")
        
        cases = Case.objects.all()
        total_cases = cases.count()
        issues_found = 0
        
        for case in cases:
            title = case.case_title
            
            # Check for basic formatting issues
            if not title or title.strip() == "":
                self.test_results['issues'].append(f"Empty case title for case {case.case_number}")
                issues_found += 1
                continue
            
            # Check for consistent VS separator
            if " VS " not in title and total_cases > 0:
                # Allow some cases without VS if they're legitimate
                if not any(keyword in title.lower() for keyword in ['misc', 'reference', 'review']):
                    self.test_results['issues'].append(f"Inconsistent separator in: {title}")
                    issues_found += 1
            
            # Check for excessive whitespace
            if "   " in title or title.startswith(" ") or title.endswith(" "):
                self.test_results['issues'].append(f"Excessive whitespace in: {title}")
                issues_found += 1
            
            # Check for quality score
            quality_score = self.cleaner.get_data_quality_score(title)
            if quality_score < 0.7:
                self.test_results['issues'].append(f"Low quality score ({quality_score:.2f}) for: {title}")
                issues_found += 1
        
        print(f"   ✅ Tested {total_cases} cases")
        print(f"   ⚠️ Found {issues_found} issues")
        
        if issues_found == 0:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1
    
    def test_case_numbers_validity(self):
        """Test that case numbers are valid and consistent"""
        print("\n🔍 Testing Case Numbers Validity...")
        
        cases = Case.objects.all()
        total_cases = cases.count()
        issues_found = 0
        
        for case in cases:
            case_number = case.case_number
            
            if not case_number or case_number.strip() == "":
                self.test_results['issues'].append(f"Empty case number for case ID {case.id}")
                issues_found += 1
                continue
            
            # Check for basic case number patterns
            if len(case_number) < 5:
                self.test_results['issues'].append(f"Very short case number: {case_number}")
                issues_found += 1
        
        print(f"   ✅ Tested {total_cases} case numbers")
        print(f"   ⚠️ Found {issues_found} issues")
        
        if issues_found == 0:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1
    
    def test_status_values_consistency(self):
        """Test that status values are consistent and valid"""
        print("\n🔍 Testing Status Values Consistency...")
        
        cases = Case.objects.all()
        total_cases = cases.count()
        issues_found = 0
        
        valid_statuses = ['Pending', 'Decided', 'Disposed', 'Dismissed', 'Allowed', 'Rejected', 'Withdrawn', 'Adjourned', 'Fixed', 'Consigned', 'N/A']
        
        for case in cases:
            status = case.status
            
            if not status or status.strip() == "":
                self.test_results['issues'].append(f"Empty status for case {case.case_number}")
                issues_found += 1
                continue
            
            # Check if status is in valid list
            if status not in valid_statuses:
                self.test_results['issues'].append(f"Invalid status '{status}' for case {case.case_number}")
                issues_found += 1
        
        print(f"   ✅ Tested {total_cases} status values")
        print(f"   ⚠️ Found {issues_found} issues")
        
        if issues_found == 0:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1
    
    def test_orders_data_quality(self):
        """Test quality of orders data"""
        print("\n🔍 Testing Orders Data Quality...")
        
        orders = OrdersData.objects.all()
        total_orders = orders.count()
        issues_found = 0
        
        for order in orders:
            short_order = order.short_order
            
            if not short_order or short_order.strip() == "":
                self.test_results['issues'].append(f"Empty order text for order ID {order.id}")
                issues_found += 1
                continue
            
            # Check for quality score
            quality_score = self.cleaner.get_data_quality_score(short_order)
            if quality_score < 0.6:
                self.test_results['issues'].append(f"Low quality order text (score: {quality_score:.2f}): {short_order[:50]}...")
                issues_found += 1
        
        print(f"   ✅ Tested {total_orders} orders")
        print(f"   ⚠️ Found {issues_found} issues")
        
        if issues_found == 0:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1
    
    def test_parties_data_completeness(self):
        """Test completeness of parties data"""
        print("\n🔍 Testing Parties Data Completeness...")
        
        parties = PartiesDetailData.objects.all()
        total_parties = parties.count()
        issues_found = 0
        
        for party in parties:
            party_name = party.party_name
            party_side = party.party_side
            
            if not party_name or party_name.strip() == "":
                self.test_results['issues'].append(f"Empty party name for party ID {party.id}")
                issues_found += 1
            
            if not party_side or party_side.strip() == "":
                self.test_results['issues'].append(f"Empty party side for party {party_name}")
                issues_found += 1
            
            # Check for valid party sides
            valid_sides = ['Petitioner', 'Respondent', 'Appellant', 'Defendant', 'Plaintiff', 'Other']
            if party_side and party_side not in valid_sides:
                self.test_results['issues'].append(f"Invalid party side '{party_side}' for {party_name}")
                issues_found += 1
        
        print(f"   ✅ Tested {total_parties} parties")
        print(f"   ⚠️ Found {issues_found} issues")
        
        if issues_found == 0:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1
    
    def test_data_relationships(self):
        """Test that data relationships are maintained"""
        print("\n🔍 Testing Data Relationships...")
        
        cases = Case.objects.all()
        total_cases = cases.count()
        issues_found = 0
        
        for case in cases:
            # Check if case has related data
            orders_count = case.orders_data.count()
            comments_count = case.comments_data.count()
            parties_count = case.parties_detail_data.count()
            
            # Check if case has at least some related data
            if orders_count == 0 and comments_count == 0 and parties_count == 0:
                self.test_results['issues'].append(f"Case {case.case_number} has no related data")
                issues_found += 1
        
        print(f"   ✅ Tested {total_cases} case relationships")
        print(f"   ⚠️ Found {issues_found} issues")
        
        if issues_found == 0:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1
    
    def test_cleaning_effectiveness(self):
        """Test that data cleaning was effective"""
        print("\n🔍 Testing Cleaning Effectiveness...")
        
        cases = Case.objects.all()
        total_cases = cases.count()
        issues_found = 0
        
        for case in cases:
            title = case.case_title
            
            # Check for noise patterns that should have been cleaned
            if "   " in title:  # Multiple spaces
                self.test_results['issues'].append(f"Multiple spaces in title: {title}")
                issues_found += 1
            
            if title and (title.startswith(" ") or title.endswith(" ")):
                self.test_results['issues'].append(f"Leading/trailing spaces in title: {title}")
                issues_found += 1
            
            # Check for placeholder values
            if any(placeholder in title for placeholder in ['N/A', 'NA', 'None', 'null']):
                self.test_results['issues'].append(f"Placeholder value in title: {title}")
                issues_found += 1
        
        print(f"   ✅ Tested {total_cases} cases for cleaning effectiveness")
        print(f"   ⚠️ Found {issues_found} issues")
        
        if issues_found == 0:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1
    
    def test_overall_data_quality(self):
        """Test overall data quality metrics"""
        print("\n🔍 Testing Overall Data Quality...")
        
        # Calculate quality metrics
        total_cases = Case.objects.count()
        total_orders = OrdersData.objects.count()
        total_comments = CommentsData.objects.count()
        total_parties = PartiesDetailData.objects.count()
        
        # Check for minimum data requirements
        if total_cases == 0:
            self.test_results['issues'].append("No cases found in database")
            self.test_results['failed'] += 1
            return
        
        # Calculate average quality scores
        case_titles = [case.case_title for case in Case.objects.all() if case.case_title]
        order_texts = [order.short_order for order in OrdersData.objects.all() if order.short_order]
        
        avg_case_score = sum(self.cleaner.get_data_quality_score(title) for title in case_titles) / len(case_titles) if case_titles else 0
        avg_order_score = sum(self.cleaner.get_data_quality_score(text) for text in order_texts) / len(order_texts) if order_texts else 0
        
        print(f"   📊 Data Statistics:")
        print(f"      Total Cases: {total_cases}")
        print(f"      Total Orders: {total_orders}")
        print(f"      Total Comments: {total_comments}")
        print(f"      Total Parties: {total_parties}")
        print(f"      Average Case Title Quality: {avg_case_score:.2f}")
        print(f"      Average Order Text Quality: {avg_order_score:.2f}")
        
        # Quality thresholds
        if avg_case_score < 0.8:
            self.test_results['issues'].append(f"Low average case title quality: {avg_case_score:.2f}")
            self.test_results['failed'] += 1
        else:
            self.test_results['passed'] += 1
        
        if avg_order_score < 0.7:
            self.test_results['issues'].append(f"Low average order text quality: {avg_order_score:.2f}")
            self.test_results['failed'] += 1
        else:
            self.test_results['passed'] += 1
    
    def generate_quality_report(self):
        """Generate a comprehensive quality report"""
        print("\n" + "="*60)
        print("📋 DATA QUALITY TEST REPORT")
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
                print("🎉 EXCELLENT: Data quality is very high!")
            elif pass_rate >= 80:
                print("✅ GOOD: Data quality is acceptable")
            elif pass_rate >= 70:
                print("⚠️ FAIR: Some quality issues need attention")
            else:
                print("❌ POOR: Significant quality issues detected")
        
        print(f"\n📅 Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)


def run_data_quality_tests():
    """Run all data quality tests and generate report"""
    print("🧪 RUNNING DATA QUALITY TEST SUITE")
    print("="*60)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    test_loader = unittest.TestLoader()
    
    # Add all test methods
    test_methods = [
        'test_case_titles_consistency',
        'test_case_numbers_validity', 
        'test_status_values_consistency',
        'test_orders_data_quality',
        'test_parties_data_completeness',
        'test_data_relationships',
        'test_cleaning_effectiveness',
        'test_overall_data_quality'
    ]
    
    for method in test_methods:
        test_suite.addTest(test_loader.loadTestsFromName(method, DataQualityTestSuite))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Generate report
    test_instance = DataQualityTestSuite()
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
    
    test_instance.generate_quality_report()
    
    return test_instance.test_results


if __name__ == '__main__':
    run_data_quality_tests()
