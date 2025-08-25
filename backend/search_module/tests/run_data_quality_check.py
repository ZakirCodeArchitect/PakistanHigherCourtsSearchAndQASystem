#!/usr/bin/env python
"""
Data Quality Check Runner

Simple script to run data quality verification tests.
Use this after scraping new data to verify quality and pipeline performance.

Usage:
    python tests/run_data_quality_check.py [--quick] [--save-report]
"""

import os
import sys
import argparse
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

def main():
    parser = argparse.ArgumentParser(
        description='Run data quality verification tests',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python tests/run_data_quality_check.py                    # Full verification
    python tests/run_data_quality_check.py --quick           # Quick check only
    python tests/run_data_quality_check.py --save-report     # Save detailed report
    python tests/run_data_quality_check.py --quick --save-report
        """
    )
    parser.add_argument('--quick', action='store_true', 
                       help='Run quick verification only')
    parser.add_argument('--save-report', action='store_true',
                       help='Save detailed report to JSON file')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # Import after Django setup
    import django
    django.setup()
    
    from tests.test_data_quality_verification import DataQualityVerificationTest, QuickDataQualityCheck
    
    print("🔍 DATA QUALITY VERIFICATION")
    print("=" * 50)
    
    if args.quick:
        print("Running quick verification...")
        test = QuickDataQualityCheck()
        test.test_quick_verification()
        print("\n✅ Quick verification completed!")
    else:
        print("Running comprehensive verification...")
        test = DataQualityVerificationTest()
        test.setUp()
        test.test_comprehensive_verification()
        
        if args.save_report:
            report_path = test.save_test_report()
            print(f"\n📄 Detailed report saved to: {report_path}")
        
        print("\n✅ Comprehensive verification completed!")
    
    print("\n🎉 All tests passed!")

if __name__ == '__main__':
    main()
