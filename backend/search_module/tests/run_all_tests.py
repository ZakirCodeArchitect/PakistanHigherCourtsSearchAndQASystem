#!/usr/bin/env python
"""
Comprehensive Test Runner
Runs all test suites and generates a combined report for the entire system.
Use this to verify data quality and pipeline performance after scraping new data.
"""

import os
import sys
import django
from pathlib import Path
import unittest
from datetime import datetime
import argparse

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from test_data_quality import run_data_quality_tests
from test_pdf_pipeline import run_pdf_pipeline_tests


class ComprehensiveTestRunner:
    """Comprehensive test runner for the entire system"""
    
    def __init__(self):
        self.overall_results = {
            'data_quality': {},
            'pdf_pipeline': {},
            'total_passed': 0,
            'total_failed': 0,
            'total_warnings': 0,
            'start_time': None,
            'end_time': None
        }
    
    def run_data_quality_tests(self):
        """Run data quality tests"""
        print("\n" + "="*80)
        print("🧪 RUNNING DATA QUALITY TESTS")
        print("="*80)
        
        try:
            results = run_data_quality_tests()
            self.overall_results['data_quality'] = results
            self.overall_results['total_passed'] += results.get('passed', 0)
            self.overall_results['total_failed'] += results.get('failed', 0)
            self.overall_results['total_warnings'] += results.get('warnings', 0)
            return True
        except Exception as e:
            print(f"❌ Error running data quality tests: {str(e)}")
            self.overall_results['data_quality'] = {'error': str(e)}
            return False
    
    def run_pdf_pipeline_tests(self):
        """Run PDF pipeline tests"""
        print("\n" + "="*80)
        print("🧪 RUNNING PDF PIPELINE TESTS")
        print("="*80)
        
        try:
            results = run_pdf_pipeline_tests()
            self.overall_results['pdf_pipeline'] = results
            self.overall_results['total_passed'] += results.get('passed', 0)
            self.overall_results['total_failed'] += results.get('failed', 0)
            self.overall_results['total_warnings'] += results.get('warnings', 0)
            return True
        except Exception as e:
            print(f"❌ Error running PDF pipeline tests: {str(e)}")
            self.overall_results['pdf_pipeline'] = {'error': str(e)}
            return False
    
    def run_all_tests(self, skip_data_quality=False, skip_pdf_pipeline=False):
        """Run all test suites"""
        print("🚀 COMPREHENSIVE TEST SUITE RUNNER")
        print("="*80)
        print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        self.overall_results['start_time'] = datetime.now()
        
        # Run data quality tests
        if not skip_data_quality:
            self.run_data_quality_tests()
        else:
            print("⏭️ Skipping data quality tests")
        
        # Run PDF pipeline tests
        if not skip_pdf_pipeline:
            self.run_pdf_pipeline_tests()
        else:
            print("⏭️ Skipping PDF pipeline tests")
        
        self.overall_results['end_time'] = datetime.now()
        
        # Generate comprehensive report
        self.generate_comprehensive_report()
    
    def generate_comprehensive_report(self):
        """Generate a comprehensive report combining all test results"""
        print("\n" + "="*80)
        print("📋 COMPREHENSIVE TEST REPORT")
        print("="*80)
        
        # Calculate timing
        duration = self.overall_results['end_time'] - self.overall_results['start_time']
        
        print(f"⏱️ Total Duration: {duration}")
        print(f"📅 Started: {self.overall_results['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📅 Finished: {self.overall_results['end_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        
        print(f"\n📊 OVERALL RESULTS:")
        print(f"   ✅ Total Tests Passed: {self.overall_results['total_passed']}")
        print(f"   ❌ Total Tests Failed: {self.overall_results['total_failed']}")
        print(f"   ⚠️ Total Warnings: {self.overall_results['total_warnings']}")
        
        # Individual test suite results
        print(f"\n🔍 INDIVIDUAL TEST SUITE RESULTS:")
        
        # Data Quality Results
        if 'error' in self.overall_results['data_quality']:
            print(f"   📋 Data Quality Tests: ❌ ERROR - {self.overall_results['data_quality']['error']}")
        else:
            dq_results = self.overall_results['data_quality']
            dq_passed = dq_results.get('passed', 0)
            dq_failed = dq_results.get('failed', 0)
            dq_total = dq_passed + dq_failed
            dq_rate = (dq_passed / dq_total * 100) if dq_total > 0 else 0
            print(f"   📋 Data Quality Tests: {dq_passed}/{dq_total} passed ({dq_rate:.1f}%)")
        
        # PDF Pipeline Results
        if 'error' in self.overall_results['pdf_pipeline']:
            print(f"   📄 PDF Pipeline Tests: ❌ ERROR - {self.overall_results['pdf_pipeline']['error']}")
        else:
            pdf_results = self.overall_results['pdf_pipeline']
            pdf_passed = pdf_results.get('passed', 0)
            pdf_failed = pdf_results.get('failed', 0)
            pdf_total = pdf_passed + pdf_failed
            pdf_rate = (pdf_passed / pdf_total * 100) if pdf_total > 0 else 0
            print(f"   📄 PDF Pipeline Tests: {pdf_passed}/{pdf_total} passed ({pdf_rate:.1f}%)")
        
        # Overall assessment
        total_tests = self.overall_results['total_passed'] + self.overall_results['total_failed']
        if total_tests > 0:
            overall_rate = (self.overall_results['total_passed'] / total_tests) * 100
            
            print(f"\n🎯 OVERALL ASSESSMENT:")
            print(f"   📊 Overall Pass Rate: {overall_rate:.1f}%")
            
            if overall_rate >= 90:
                print("   🎉 EXCELLENT: System is working perfectly!")
                print("   ✅ All components are functioning as expected")
                print("   ✅ Data quality is high")
                print("   ✅ Pipeline is performing well")
            elif overall_rate >= 80:
                print("   ✅ GOOD: System is working well")
                print("   ⚠️ Some minor issues detected")
                print("   💡 Review warnings for potential improvements")
            elif overall_rate >= 70:
                print("   ⚠️ FAIR: System has some issues")
                print("   🔧 Some components need attention")
                print("   📋 Review failed tests for specific problems")
            else:
                print("   ❌ POOR: System has significant issues")
                print("   🚨 Multiple components are failing")
                print("   🔧 Immediate attention required")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        
        if self.overall_results['total_failed'] > 0:
            print("   🔧 Address failed tests before proceeding")
        
        if self.overall_results['total_warnings'] > 0:
            print("   📋 Review warnings for potential improvements")
        
        if self.overall_results['total_passed'] > 0:
            print("   ✅ System is ready for production use")
        
        print(f"\n📅 Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)


def main():
    """Main function to run tests with command line arguments"""
    parser = argparse.ArgumentParser(
        description='Comprehensive Test Runner for Pakistan Higher Courts System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Comprehensive Test Runner

This script runs all test suites to verify data quality and pipeline performance.
Use this after scraping new data or running the PDF pipeline to ensure everything is working correctly.

Examples:
    python run_all_tests.py                    # Run all tests
    python run_all_tests.py --skip-data        # Skip data quality tests
    python run_all_tests.py --skip-pdf         # Skip PDF pipeline tests
    python run_all_tests.py --data-only        # Run only data quality tests
    python run_all_tests.py --pdf-only         # Run only PDF pipeline tests
        """
    )
    
    parser.add_argument('--skip-data', action='store_true', 
                       help='Skip data quality tests')
    parser.add_argument('--skip-pdf', action='store_true', 
                       help='Skip PDF pipeline tests')
    parser.add_argument('--data-only', action='store_true', 
                       help='Run only data quality tests')
    parser.add_argument('--pdf-only', action='store_true', 
                       help='Run only PDF pipeline tests')
    
    args = parser.parse_args()
    
    # Determine which tests to run
    skip_data_quality = args.skip_data or args.pdf_only
    skip_pdf_pipeline = args.skip_pdf or args.data_only
    
    # Run tests
    runner = ComprehensiveTestRunner()
    runner.run_all_tests(
        skip_data_quality=skip_data_quality,
        skip_pdf_pipeline=skip_pdf_pipeline
    )


if __name__ == '__main__':
    main()
