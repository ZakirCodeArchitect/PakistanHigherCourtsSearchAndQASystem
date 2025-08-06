#!/usr/bin/env python3
"""
Utility script to manage the IHC cases data file
"""

import json
import sys
import os
from datetime import datetime

OUTPUT_FILE = "../../../../../cases_metadata/Islamabad_High_Court/ihc_cases_2023.json"

def load_cases():
    """Load cases from the JSON file"""
    try:
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ File {OUTPUT_FILE} not found")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ Error reading {OUTPUT_FILE}: {e}")
        return []

def save_cases(cases):
    """Save cases to the JSON file"""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(cases, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved {len(cases)} cases to {OUTPUT_FILE}")
    except Exception as e:
        print(f"❌ Error saving to {OUTPUT_FILE}: {e}")

def view_cases(limit=None):
    """View cases in the JSON file"""
    cases = load_cases()
    if not cases:
        print(f"📁 No cases found in {OUTPUT_FILE}")
        return
    
    print(f"📊 Found {len(cases)} cases in {OUTPUT_FILE}")
    print("=" * 50)
    
    for i, case in enumerate(cases[:limit]):
        print(f"\n📋 Case {i+1}:")
        
        # Handle both old and new data structures
        if "CaseNo" in case and "CaseTitle" in case:
            # New structure (website format)
            print(f"   SR: {case.get('SR', 'N/A')}")
            print(f"   Institution: {case.get('Institution', 'N/A')}")
            print(f"   Case No: {case.get('CaseNo', 'N/A')}")
            print(f"   Case Title: {case.get('CaseTitle', 'N/A')}")
            print(f"   Bench: {case.get('Bench', 'N/A')}")
            print(f"   Hearing Date: {case.get('HearingDate', 'N/A')}")
            print(f"   Status: {case.get('Status', 'N/A')}")
            
            # Show history availability
            history = case.get('History', {})
            if history:
                print(f"   History:")
                print(f"     Orders: {history.get('Orders', 'N/A')}")
                print(f"     Comments: {history.get('Comments', 'N/A')}")
                print(f"     Case CMs: {history.get('CaseCMs', 'N/A')}")
                print(f"     Judgement: {history.get('Judgement', 'N/A')}")
            
            print(f"   Details: {case.get('Details', 'N/A')}")
            
        else:
            # Old structure (mock data format)
            print(f"   Case No: {case.get('CaseNo', 'N/A')}")
            print(f"   Title: {case.get('Title', 'N/A')}")
            print(f"   Petitioner: {case.get('Petitioner', 'N/A')}")
            print(f"   Respondent: {case.get('Respondent', 'N/A')}")
            print(f"   Status: {case.get('Status', 'N/A')}")
            print(f"   Date: {case.get('Date', 'N/A')}")
            print(f"   Court: {case.get('Court', 'N/A')}")
            print(f"   Type: {case.get('Type', 'N/A')}")
        
        # Show metadata
        if 'ScrapedTimestamp' in case:
            print(f"   Scraped: {case['ScrapedTimestamp']}")
        if 'IsMockData' in case:
            print(f"   Mock Data: {case['IsMockData']}")
        
        print("-" * 30)

def clear_cases():
    """Clear all cases from the JSON file"""
    confirm = input(f"⚠️  Are you sure you want to clear all cases from {OUTPUT_FILE}? (y/N): ")
    if confirm.lower() == 'y':
        save_cases([])
        print(f"🗑️  Cleared all cases from {OUTPUT_FILE}")
    else:
        print("❌ Operation cancelled")

def analyze_cases():
    """Analyze the cases data"""
    cases = load_cases()
    if not cases:
        print(f"📁 No cases found in {OUTPUT_FILE}")
        return
    
    print(f"📊 Analysis of {len(cases)} cases:")
    print("=" * 50)
    
    # Count by status
    status_counts = {}
    bench_counts = {}
    case_type_counts = {}
    year_counts = {}
    mock_data_count = 0
    
    for case in cases:
        status = case.get('Status', 'Unknown')
        bench = case.get('Bench', 'Unknown')
        case_type = case.get('CaseNo', 'Unknown').split()[0] if case.get('CaseNo') else 'Unknown'
        year = case.get('ScrapedYear', 'Unknown')
        is_mock = case.get('IsMockData', False)
        
        status_counts[status] = status_counts.get(status, 0) + 1
        bench_counts[bench] = bench_counts.get(bench, 0) + 1
        case_type_counts[case_type] = case_type_counts.get(case_type, 0) + 1
        year_counts[year] = year_counts.get(year, 0) + 1
        
        if is_mock:
            mock_data_count += 1
    
    print(f"\n📈 Status Distribution:")
    for status, count in status_counts.items():
        print(f"   {status}: {count}")
    
    print(f"\n🏛️  Bench Distribution:")
    for bench, count in bench_counts.items():
        print(f"   {bench}: {count}")
    
    print(f"\n📋 Case Type Distribution:")
    for case_type, count in case_type_counts.items():
        print(f"   {case_type}: {count}")
    
    print(f"\n📅 Year Distribution:")
    for year, count in year_counts.items():
        print(f"   {year}: {count}")
    
    print(f"\n🎭 Data Quality:")
    print(f"   Real Data: {len(cases) - mock_data_count}")
    print(f"   Mock Data: {mock_data_count}")

def export_cases(format_type='json'):
    """Export cases in different formats"""
    cases = load_cases()
    if not cases:
        print(f"📁 No cases found in {OUTPUT_FILE}")
        return
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if format_type == 'json':
        filename = f"ihc_cases_export_{timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(cases, f, indent=2, ensure_ascii=False)
        print(f"💾 Exported {len(cases)} cases to {filename}")
    
    elif format_type == 'csv':
        import csv
        filename = f"ihc_cases_export_{timestamp}.csv"
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            if cases:
                # Get all possible fieldnames
                fieldnames = set()
                for case in cases:
                    fieldnames.update(case.keys())
                
                writer = csv.DictWriter(f, fieldnames=sorted(fieldnames))
                writer.writeheader()
                writer.writerows(cases)
        print(f"💾 Exported {len(cases)} cases to {filename}")
    
    else:
        print(f"❌ Unsupported format: {format_type}")

def main():
    """Main function to handle command line arguments"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python manage_cases.py view [limit]     - View cases (optional limit)")
        print("  python manage_cases.py clear            - Clear all cases")
        print("  python manage_cases.py analyze          - Analyze cases data")
        print("  python manage_cases.py export [format]  - Export cases (json/csv)")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'view':
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
        view_cases(limit)
    
    elif command == 'clear':
        clear_cases()
    
    elif command == 'analyze':
        analyze_cases()
    
    elif command == 'export':
        format_type = sys.argv[2] if len(sys.argv) > 2 else 'json'
        export_cases(format_type)
    
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == "__main__":
    main() 