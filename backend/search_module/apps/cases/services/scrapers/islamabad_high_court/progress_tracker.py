"""
Progress Tracking System for IHC Scraper
Allows resuming scraping from where it left off with granular row-level tracking
"""

import os
import json
import pickle
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class ScrapingProgressTracker:
    """Tracks scraping progress and allows resuming from where it left off with row-level granularity"""
    
    def __init__(self, progress_file="scraping_progress.json", backup_file="scraping_progress_backup.pkl"):
        self.progress_file = progress_file
        self.backup_file = backup_file
        self.progress_data = self._load_progress()
    
    def _load_progress(self) -> Dict:
        """Load progress from file or create new if doesn't exist"""
        try:
            if os.path.exists(self.progress_file):
                with open(self.progress_file, 'r') as f:
                    data = json.load(f)
                    print(f"📂 Loaded existing progress: {data.get('description', 'Unknown session')}")
                    return data
            else:
                print("📂 No existing progress found. Starting fresh session.")
                return self._create_new_session()
        except Exception as e:
            print(f"⚠️ Error loading progress: {e}")
            return self._create_new_session()
    
    def _create_new_session(self) -> Dict:
        """Create a new scraping session"""
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        return {
            "session_id": session_id,
            "description": "",
            "start_time": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "total_batches": 0,
            "completed_batches": [],
            "failed_batches": [],
            "current_batch": 1,
            "total_cases_scraped": 0,
            "cases_per_batch": 5,
            "max_workers": 3,
            "fetch_details": True,
            "status": "running",
            "batch_errors": {},
            # NEW: Granular case and row tracking
            "case_progress": {},  # {case_number: {"last_row": 0, "total_rows": 0, "pages_completed": [], "status": "in_progress"}}
            "row_progress": {},   # {case_number: {"page": 1, "row": 0, "total_processed": 0}}
        }
    
    def _save_progress(self):
        """Save progress to both JSON and pickle files"""
        self.progress_data["last_updated"] = datetime.now().isoformat()
        
        try:
            # Save to JSON
            with open(self.progress_file, 'w') as f:
                json.dump(self.progress_data, f, indent=2)
            
            # Save backup to pickle
            with open(self.backup_file, 'wb') as f:
                pickle.dump(self.progress_data, f)
                
        except Exception as e:
            print(f"⚠️ Error saving progress: {e}")
    
    def start_session(self, start_batch: int, end_batch: int, cases_per_batch: int, 
                     max_workers: int, fetch_details: bool, description: str = "") -> Tuple[int, int]:
        """Start or resume a scraping session"""
        
        # Check if we have an existing session
        if self.progress_data.get("session_id") and self._ask_resume_question():
            return self._resume_session(start_batch, end_batch, cases_per_batch, max_workers, fetch_details)
        else:
            return self._start_new_session(start_batch, end_batch, cases_per_batch, max_workers, fetch_details, description)
    
    def _ask_resume_question(self) -> bool:
        """Ask user if they want to resume (for automated mode, always resume)"""
        # For automated mode, always resume
        return True
    
    def _resume_session(self, start_batch: int, end_batch: int, cases_per_batch: int, 
                       max_workers: int, fetch_details: bool) -> Tuple[int, int]:
        """Resume existing session with granular row tracking"""
        
        completed = self.progress_data.get("completed_batches", [])
        failed = self.progress_data.get("failed_batches", [])
        case_progress = self.progress_data.get("case_progress", {})
        
        # Update total_batches if it was 0 (session not properly initialized)
        if self.progress_data.get("total_batches", 0) == 0:
            self.progress_data["total_batches"] = end_batch - start_batch + 1
            print(f"📊 Updated total_batches to {self.progress_data['total_batches']}")
        
        # Find the next batch to process
        all_processed = set(completed + failed)
        next_batch = None
        
        for batch in range(start_batch, end_batch + 1):
            if batch not in all_processed:
                next_batch = batch
                break
        
        if next_batch is None:
            print("✅ All batches already completed!")
            return start_batch, end_batch
        
        print(f"🔄 Found existing session: {self.progress_data.get('description', 'Unknown session')}")
        print(f"🔄 Resuming from batch {next_batch}")
        print(f"📊 Progress: {len(completed)} completed, {len(failed)} failed")
        print(f"📈 Remaining: {end_batch - next_batch + 1} batches")
        
        # Show case-level progress if available
        if case_progress:
            print("📋 Case-level progress:")
            for case_num, progress in case_progress.items():
                status = progress.get("status", "unknown")
                last_row = progress.get("last_row", 0)
                total_rows = progress.get("total_rows", 0)
                pages_completed = progress.get("pages_completed", [])
                print(f"   Case {case_num}: {status}, Last row: {last_row}/{total_rows}, Pages: {pages_completed}")
        
        # Update session info
        self.progress_data.update({
            "current_batch": next_batch,
            "cases_per_batch": cases_per_batch,
            "max_workers": max_workers,
            "fetch_details": fetch_details
        })
        
        self._save_progress()
        return next_batch, end_batch
    
    def _start_new_session(self, start_batch: int, end_batch: int, cases_per_batch: int, 
                          max_workers: int, fetch_details: bool, description: str) -> Tuple[int, int]:
        """Start a new scraping session"""
        
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.progress_data = {
            "session_id": session_id,
            "description": description,
            "start_time": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "total_batches": end_batch - start_batch + 1,
            "completed_batches": [],
            "failed_batches": [],
            "current_batch": start_batch,
            "total_cases_scraped": 0,
            "cases_per_batch": cases_per_batch,
            "max_workers": max_workers,
            "fetch_details": fetch_details,
            "status": "running",
            "batch_errors": {},
            # NEW: Initialize granular tracking
            "case_progress": {},
            "row_progress": {},
        }
        
        self._save_progress()
        print(f"🚀 Starting new session: {description}")
        return start_batch, end_batch
    
    def mark_batch_completed(self, batch_number: int, cases_scraped: int = 0):
        """Mark a batch as completed"""
        if batch_number not in self.progress_data.get("completed_batches", []):
            self.progress_data.setdefault("completed_batches", []).append(batch_number)
        
        self.progress_data["total_cases_scraped"] += cases_scraped
        self.progress_data["current_batch"] = batch_number + 1
        self._save_progress()
        
        print(f"✅ Batch {batch_number} marked as completed")
    
    def mark_batch_failed(self, batch_number: int, error: str = ""):
        """Mark a batch as failed"""
        if batch_number not in self.progress_data.get("failed_batches", []):
            self.progress_data.setdefault("failed_batches", []).append(batch_number)
        
        if error:
            self.progress_data.setdefault("batch_errors", {})[str(batch_number)] = error
        
        self._save_progress()
        print(f"❌ Batch {batch_number} marked as failed: {error}")
    
    # NEW: Granular case and row tracking methods
    
    def get_case_progress(self, case_number: int) -> Dict:
        """Get progress for a specific case"""
        return self.progress_data.get("case_progress", {}).get(str(case_number), {
            "last_row": 0,
            "total_rows": 0,
            "pages_completed": [],
            "status": "not_started"
        })
    
    def update_case_progress(self, case_number: int, last_row: int, total_rows: int = None, 
                           page_number: int = None, status: str = "in_progress"):
        """Update progress for a specific case"""
        case_key = str(case_number)
        if case_key not in self.progress_data.get("case_progress", {}):
            self.progress_data.setdefault("case_progress", {})[case_key] = {
                "last_row": 0,
                "total_rows": 0,
                "pages_completed": [],
                "status": "not_started"
            }
        
        case_progress = self.progress_data["case_progress"][case_key]
        case_progress["last_row"] = last_row
        case_progress["status"] = status
        
        if total_rows is not None:
            case_progress["total_rows"] = total_rows
        
        if page_number is not None and page_number not in case_progress["pages_completed"]:
            case_progress["pages_completed"].append(page_number)
        
        self._save_progress()
        print(f"📊 Updated case {case_number} progress: row {last_row}/{total_rows or 'unknown'}, status: {status}")
    
    def mark_case_completed(self, case_number: int, total_rows: int):
        """Mark a case as completed"""
        self.update_case_progress(case_number, total_rows, total_rows, status="completed")
        print(f"✅ Case {case_number} marked as completed ({total_rows} rows)")
    
    def get_resume_point(self, case_number: int) -> Tuple[int, int]:
        """Get the resume point for a case (page, row)"""
        case_progress = self.get_case_progress(case_number)
        last_row = case_progress.get("last_row", 0)
        pages_completed = case_progress.get("pages_completed", [])
        
        # If we have completed pages, start from the next page
        if pages_completed:
            next_page = max(pages_completed) + 1
            return next_page, 1  # Start from row 1 of next page
        else:
            # If no pages completed, start from row after last_row
            return 1, last_row + 1 if last_row > 0 else 1
    
    def should_skip_case(self, case_number: int) -> bool:
        """Check if a case should be skipped (already completed)"""
        
        # ALWAYS check database first - if empty, NEVER skip ANY cases
        try:
            from apps.cases.models import Case
            total_cases = Case.objects.count()
            if total_cases == 0:
                # Fresh start - NEVER skip any cases, regardless of progress tracking
                return False
        except Exception as e:
            print(f"⚠️ Error checking database: {e}")
            # If we can't check database, be conservative and don't skip
            return False
        
        # Only check progress tracking if database has data
        case_progress = self.get_case_progress(case_number)
        return case_progress.get("status") == "completed"
    
    def should_skip_row(self, case_number: int, page_number: int, row_number: int) -> bool:
        """Check if a specific row should be skipped (already processed)"""
        
        # ALWAYS check database first - if empty, NEVER skip ANY rows
        try:
            from apps.cases.models import Case
            total_cases = Case.objects.count()
            if total_cases == 0:
                # Fresh start - NEVER skip any rows, regardless of progress tracking
                return False
        except Exception as e:
            print(f"⚠️ Error checking database: {e}")
            # If we can't check database, be conservative and don't skip
            return False
        
        # Only check progress tracking if database has data
        case_progress = self.get_case_progress(case_number)
        
        # If case is completed, skip all rows
        if case_progress.get("status") == "completed":
            return True
        
        # If page is already completed, skip all rows on this page
        if page_number in case_progress.get("pages_completed", []):
            return True
        
        # If we're on the current page, check if this row was already processed
        last_row = case_progress.get("last_row", 0)
        if page_number == 1 and row_number <= last_row:
            return True
        
        return False
    
    def reset_session(self):
        """Reset the current session"""
        self.progress_data = self._create_new_session()
        self._save_progress()
        print("🔄 Session reset successfully")
    
    def check_and_reset_for_fresh_start(self):
        """Check if database is empty and reset progress if needed"""
        try:
            from apps.cases.models import Case
            total_cases = Case.objects.count()
            if total_cases == 0:
                print("🔄 Database is empty - resetting progress tracking for fresh start")
                self.progress_data["case_progress"] = {}
                self.progress_data["row_progress"] = {}
                self._save_progress()
                return True
        except Exception as e:
            print(f"⚠️ Error checking database for fresh start: {e}")
        return False
    
    def get_progress_summary(self) -> Dict:
        """Get a summary of current progress"""
        completed = len(self.progress_data.get("completed_batches", []))
        failed = len(self.progress_data.get("failed_batches", []))
        total = self.progress_data.get("total_batches", 0)
        
        # Count completed cases
        completed_cases = sum(1 for progress in self.progress_data.get("case_progress", {}).values() 
                            if progress.get("status") == "completed")
        
        return {
            "session_id": self.progress_data.get("session_id"),
            "description": self.progress_data.get("description"),
            "total_batches": total,
            "completed_batches": completed,
            "failed_batches": failed,
            "remaining_batches": total - completed - failed,
            "total_cases_scraped": self.progress_data.get("total_cases_scraped", 0),
            "completed_cases": completed_cases,
            "current_batch": self.progress_data.get("current_batch"),
            "status": self.progress_data.get("status"),
            "case_progress": self.progress_data.get("case_progress", {})
        }
    
    def get_remaining_batches(self) -> List[int]:
        """Get list of remaining batches to process"""
        completed = self.progress_data.get("completed_batches", [])
        failed = self.progress_data.get("failed_batches", [])
        start_batch = 1  # Default start batch
        end_batch = self.progress_data.get("total_batches", 0)
        
        # If total_batches is 0, it means session wasn't properly initialized
        # Return a default range based on current_batch
        if end_batch == 0:
            current_batch = self.progress_data.get("current_batch", 1)
            # Assume we want to process at least 5 batches if not specified
            end_batch = max(current_batch + 4, 5)
            print(f"⚠️ total_batches was 0, assuming end_batch={end_batch}")
        
        all_processed = set(completed + failed)
        remaining = []
        
        for batch in range(start_batch, end_batch + 1):
            if batch not in all_processed:
                remaining.append(batch)
        
        return remaining
    
    def print_progress_summary(self):
        """Print a formatted progress summary"""
        summary = self.get_progress_summary()
        
        if not summary.get("session_id"):
            print("📊 No active scraping session found")
            return
        
        print("\n" + "="*60)
        print("📊 SCRAPING PROGRESS SUMMARY")
        print("="*60)
        print(f"Session ID: {summary['session_id']}")
        print(f"Description: {summary['description']}")
        print(f"Status: {summary['status']}")
        print(f"Total Batches: {summary['total_batches']}")
        print(f"Completed: {summary['completed_batches']} batches")
        print(f"Failed: {summary['failed_batches']} batches")
        print(f"Remaining: {summary['remaining_batches']} batches")
        print(f"Total Cases: {summary['total_cases_scraped']}")
        print(f"Completed Cases: {summary['completed_cases']}")
        print(f"Current Batch: {summary['current_batch']}")
        
        # Show case-level progress
        if summary['case_progress']:
            print("\n📋 Case-Level Progress:")
            for case_num, progress in summary['case_progress'].items():
                status = progress.get("status", "unknown")
                last_row = progress.get("last_row", 0)
                total_rows = progress.get("total_rows", 0)
                pages_completed = progress.get("pages_completed", [])
                print(f"   Case {case_num}: {status}, Row {last_row}/{total_rows}, Pages: {pages_completed}")
        
        print("="*60)
    
    def complete_session(self):
        """Mark the session as completed"""
        self.progress_data["status"] = "completed"
        self.progress_data["end_time"] = datetime.now().isoformat()
        self._save_progress()
        print("🎉 Scraping session marked as completed!")
    
    def cleanup_old_sessions(self, days_old: int = 7):
        """Clean up old session files"""
        try:
            if os.path.exists(self.progress_file):
                file_time = datetime.fromtimestamp(os.path.getmtime(self.progress_file))
                if (datetime.now() - file_time).days > days_old:
                    os.remove(self.progress_file)
                    print(f"🗑️ Cleaned up old progress file ({days_old}+ days old)")
        except Exception as e:
            print(f"⚠️ Error cleaning up old sessions: {e}")


# Global instance
progress_tracker = ScrapingProgressTracker()
