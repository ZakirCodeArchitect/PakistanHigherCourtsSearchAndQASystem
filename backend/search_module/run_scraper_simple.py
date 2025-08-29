#!/usr/bin/env python3
"""
Simple script to run the IHC scraper without complex database dependencies
"""

import sys
import os

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    print("🚀 IHC Scraper - Simple Version")
    print("=" * 50)
    
    # Ask user for number of workers
    while True:
        try:
            workers_input = input("How many workers do you want to use? (1-5 recommended): ").strip()
            max_workers = int(workers_input)
            if 1 <= max_workers <= 10:
                break
            else:
                print("❌ Please enter a number between 1 and 10")
        except ValueError:
            print("❌ Please enter a valid number")
    
    # Ask user for batch configuration
    while True:
        try:
            start_batch = int(input("Start from batch number (default 1): ").strip() or "1")
            end_batch = int(input("End at batch number (default 3): ").strip() or "3")
            cases_per_batch = int(input("Cases per batch (default 3): ").strip() or "3")
            break
        except ValueError:
            print("❌ Please enter valid numbers")
    
    # Ask user for fetch details
    fetch_details_input = input("Fetch case details? (y/n, default y): ").strip().lower()
    fetch_details = fetch_details_input != 'n'
    
    # Ask user for resume
    resume_input = input("Resume from previous progress? (y/n, default y): ").strip().lower()
    resume = resume_input != 'n'
    
    print(f"\n📊 Configuration:")
    print(f"   Workers: {max_workers}")
    print(f"   Batches: {start_batch} to {end_batch}")
    print(f"   Cases per batch: {cases_per_batch}")
    print(f"   Fetch details: {fetch_details}")
    print(f"   Resume: {resume}")
    
    # Confirm before starting
    confirm = input(f"\n🚀 Start scraper with these settings? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ Scraper cancelled")
        return
    
    print(f"\n🚀 Starting IHC Scraper...")
    
    try:
        # Import the scraper class directly
        from apps.cases.services.scrapers.islamabad_high_court.ihc_selenium_scraper import IHCSeleniumScraper
        
        # Create scraper instance
        scraper = IHCSeleniumScraper()
        
        # Show current progress
        print(f"\n📊 Current Progress Status:")
        scraper.print_progress_summary()
        
        # Run the scraper with user settings
        results = scraper.run_multiple_batches(
            start_batch=start_batch,
            end_batch=end_batch,
            cases_per_batch=cases_per_batch,
            max_workers=max_workers,
            fetch_details=fetch_details,
            description=f"User-initiated scraping session with {max_workers} workers",
            resume=resume
        )
        
        print(f"\n✅ Scraper completed!")
        print(f"📊 Results: {len(results) if results else 0} cases processed")
        
        # Show final progress
        print(f"\n📊 Final Progress Status:")
        scraper.print_progress_summary()
        
    except KeyboardInterrupt:
        print(f"\n⚠️ Scraper interrupted by user")
    except Exception as e:
        print(f"\n❌ Scraper error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"\n🏁 Scraper finished")

if __name__ == "__main__":
    main()
