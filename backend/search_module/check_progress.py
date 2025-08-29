#!/usr/bin/env python3
"""
Check the current scraper progress
"""

import pickle
import os
from datetime import datetime

def check_progress():
    progress_file = 'scraper_progress.pkl'
    
    print('📊 Current Scraper Progress:')
    print('=' * 50)
    print(f'Progress file exists: {os.path.exists(progress_file)}')
    print()
    
    if not os.path.exists(progress_file):
        print('❌ No progress file found - scraper will start fresh')
        return
    
    try:
        print('📂 Loading progress data...')
        with open(progress_file, 'rb') as f:
            progress = pickle.load(f)
        
        print(f'Total cases tracked: {len(progress)}')
        print()
        
        print('📋 Case Details:')
        print('-' * 30)
        
        for case_no, data in progress.items():
            current_row = data.get('current_row', 'N/A')
            total_rows = data.get('total_rows', 'N/A')
            status = data.get('status', 'N/A')
            last_updated = data.get('last_updated', 'N/A')
            
            print(f'Case {case_no}: Row {current_row}/{total_rows} - Status: {status}')
            if last_updated != 'N/A':
                try:
                    dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                    print(f'  Last Updated: {dt.strftime("%Y-%m-%d %H:%M:%S")}')
                except:
                    print(f'  Last Updated: {last_updated}')
            print()
        
        print('🔄 Resume Points:')
        print('-' * 20)
        
        in_progress_cases = []
        for case_no, data in progress.items():
            if data.get('status') == 'in_progress':
                current_row = data.get('current_row', 0)
                total_rows = data.get('total_rows', 'N/A')
                resume_row = current_row + 1
                in_progress_cases.append((case_no, resume_row, total_rows))
        
        if in_progress_cases:
            for case_no, resume_row, total_rows in in_progress_cases:
                print(f'Case {case_no}: Will resume from row {resume_row}/{total_rows}')
        else:
            print('No cases in progress - all cases completed or not started')
            
        print()
        print('💡 Next Steps:')
        print('-' * 15)
        if in_progress_cases:
            print('✅ Scraper will resume from the cases listed above')
            print('✅ Progress will be maintained - no data will be lost')
        else:
            print('🆕 Scraper will start fresh with new cases')
            
    except Exception as e:
        print(f'❌ Error reading progress file: {e}')

if __name__ == "__main__":
    check_progress()
