#!/usr/bin/env python
"""
Simple Data Quality Check

A standalone script to check data quality without Django test framework.
Use this for quick verification after scraping new data.

Usage:
    python tests/simple_data_quality_check.py [--quick] [--save-report]
"""

import os
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

def main():
    parser = argparse.ArgumentParser(
        description='Simple data quality check',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python tests/simple_data_quality_check.py                    # Full check
    python tests/simple_data_quality_check.py --quick           # Quick check only
    python tests/simple_data_quality_check.py --save-report     # Save report
        """
    )
    parser.add_argument('--quick', action='store_true', 
                       help='Run quick verification only')
    parser.add_argument('--save-report', action='store_true',
                       help='Save detailed report to JSON file')
    
    args = parser.parse_args()
    
    # Import after Django setup
    import django
    django.setup()
    
    from apps.cases.models import (
        Case, OrdersData, CommentsData, CaseDetail, PartiesDetailData,
        Document, DocumentText, UnifiedCaseView
    )
    from apps.cases.services.data_cleaner import DataCleaner
    
    print("🔍 SIMPLE DATA QUALITY CHECK")
    print("=" * 50)
    
    # Initialize results
    results = {
        'timestamp': datetime.now().isoformat(),
        'total_cases': 0,
        'issues_found': [],
        'recommendations': []
    }
    
    try:
        # Basic counts
        total_cases = Case.objects.count()
        results['total_cases'] = total_cases
        
        print(f"📊 Database Statistics:")
        print(f"   Cases: {total_cases}")
        print(f"   Orders: {OrdersData.objects.count()}")
        print(f"   Comments: {CommentsData.objects.count()}")
        print(f"   Case Details: {CaseDetail.objects.count()}")
        print(f"   Parties: {PartiesDetailData.objects.count()}")
        print(f"   Documents: {Document.objects.count()}")
        print(f"   Document Texts: {DocumentText.objects.count()}")
        print(f"   Unified Views: {UnifiedCaseView.objects.count()}")
        
        if args.quick:
            # Quick verification
            print(f"\n⚡ QUICK VERIFICATION:")
            
            # Check for essential data
            cases_with_titles = Case.objects.exclude(case_title__isnull=True).exclude(case_title='').count()
            cases_with_vs = Case.objects.filter(case_title__icontains=' VS ').count()
            
            print(f"   Cases with titles: {cases_with_titles}/{total_cases}")
            print(f"   Cases with 'VS' separator: {cases_with_vs}/{total_cases}")
            
            # Basic quality checks
            if cases_with_titles < total_cases:
                results['issues_found'].append(f"{total_cases - cases_with_titles} cases missing titles")
            
            if cases_with_vs < total_cases * 0.8:
                results['issues_found'].append("Low standardization of case title separators")
            
            # Check for suspicious cases
            suspicious_cases = Case.objects.filter(case_title__in=['. VS .', 'VS', '']).count()
            if suspicious_cases > 0:
                results['issues_found'].append(f"{suspicious_cases} suspicious case titles")
            
            print(f"\n✅ Quick verification completed!")
            
        else:
            # Comprehensive verification
            print(f"\n🔍 COMPREHENSIVE VERIFICATION:")
            
            cleaner = DataCleaner()
            
            # Data completeness
            print(f"\n📈 Data Completeness:")
            cases_with_orders = Case.objects.filter(orders_data__isnull=False).distinct().count()
            cases_with_comments = Case.objects.filter(comments_data__isnull=False).distinct().count()
            cases_with_details = Case.objects.filter(case_detail__isnull=False).count()
            cases_with_parties = Case.objects.filter(parties_detail_data__isnull=False).distinct().count()
            
            coverage = {
                'orders': (cases_with_orders / total_cases) * 100 if total_cases > 0 else 0,
                'comments': (cases_with_comments / total_cases) * 100 if total_cases > 0 else 0,
                'details': (cases_with_details / total_cases) * 100 if total_cases > 0 else 0,
                'parties': (cases_with_parties / total_cases) * 100 if total_cases > 0 else 0,
            }
            
            for metric, percentage in coverage.items():
                print(f"   {metric.title()} coverage: {percentage:.1f}%")
                if percentage < 50:
                    results['issues_found'].append(f"Low {metric} coverage: {percentage:.1f}%")
            
            # Data quality scoring
            print(f"\n📊 Data Quality Scoring:")
            case_titles = list(Case.objects.values_list('case_title', flat=True))
            title_scores = [cleaner.get_data_quality_score(title) for title in case_titles]
            avg_title_score = sum(title_scores) / len(title_scores) if title_scores else 0
            
            print(f"   Average case title quality: {avg_title_score:.3f}")
            if avg_title_score < 0.8:
                results['issues_found'].append(f"Low case title quality score: {avg_title_score:.3f}")
            
            # Pipeline performance
            print(f"\n⚡ Pipeline Performance:")
            total_documents = Document.objects.count()
            downloaded_documents = Document.objects.filter(is_downloaded=True).count()
            documents_with_text = Document.objects.filter(document_texts__isnull=False).distinct().count()
            
            if total_documents > 0:
                download_rate = (downloaded_documents / total_documents) * 100
                text_extraction_rate = (documents_with_text / total_documents) * 100
                
                print(f"   Document download rate: {download_rate:.1f}%")
                print(f"   Text extraction rate: {text_extraction_rate:.1f}%")
                
                if download_rate < 80:
                    results['issues_found'].append(f"Low document download rate: {download_rate:.1f}%")
                if text_extraction_rate < 80:
                    results['issues_found'].append(f"Low text extraction rate: {text_extraction_rate:.1f}%")
            
            # Unified views
            total_unified_views = UnifiedCaseView.objects.count()
            complete_unified_views = UnifiedCaseView.objects.filter(
                case_metadata__isnull=False
            ).exclude(case_metadata={}).count()
            
            if total_unified_views > 0:
                unified_completion_rate = (complete_unified_views / total_unified_views) * 100
                print(f"   Unified views completion: {unified_completion_rate:.1f}%")
                
                if unified_completion_rate < 80:
                    results['issues_found'].append(f"Low unified views completion: {unified_completion_rate:.1f}%")
            
            print(f"\n✅ Comprehensive verification completed!")
        
        # Generate recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if not results['issues_found']:
            results['recommendations'].append("Data quality is excellent! Ready for advanced processing")
            print("   ✅ Data quality is excellent! Ready for advanced processing")
        else:
            results['recommendations'].append("Address the identified issues before proceeding")
            print("   ⚠️ Address the identified issues before proceeding")
        
        if total_cases < 10:
            results['recommendations'].append("Consider scraping more data for better analysis")
            print("   💡 Consider scraping more data for better analysis")
        
        # Print summary
        print(f"\n📋 SUMMARY:")
        print(f"   Total Cases: {total_cases}")
        print(f"   Issues Found: {len(results['issues_found'])}")
        print(f"   Recommendations: {len(results['recommendations'])}")
        
        if results['issues_found']:
            print(f"\n⚠️ Issues Found:")
            for issue in results['issues_found']:
                print(f"   • {issue}")
        
        # Save report if requested
        if args.save_report:
            report_path = Path(__file__).parent / 'reports' / f'data_quality_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            report_path.parent.mkdir(exist_ok=True)
            
            with open(report_path, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            print(f"\n📄 Report saved to: {report_path}")
        
        print(f"\n🎉 Data quality check completed!")
        
    except Exception as e:
        print(f"❌ Error during data quality check: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
