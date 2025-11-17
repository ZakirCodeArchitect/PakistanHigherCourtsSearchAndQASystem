import os
import sys
import django

# Fix Unicode encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.cases.services.scrapers.islamabad_high_court.ihc_selenium_scraper import IHCSeleniumScraper

print("Starting IHC Scraper - SEQUENTIAL MODE (Using Main Browser)")
print("Configuration: 1 case at a time, no worker threads")
print()

scraper = IHCSeleniumScraper(headless=False, fetch_details=True, worker_id=1)

# Start the driver - MUST succeed before continuing
if not scraper.start_driver():
    print("\n❌ FATAL ERROR: Failed to start browser. Cannot continue.")
    print("💡 TIP: Close any running Chrome windows and try again.")
    exit(1)

if not scraper.navigate_to_case_status():
    print("\n❌ FATAL ERROR: Failed to navigate to case status page.")
    scraper.stop_driver()
    exit(1)

# Process cases sequentially using the main browser
START_CASE = 1
END_CASE = 1000

case_no = START_CASE
while case_no <= END_CASE:
    try:
        # Check if case should be skipped
        if scraper.should_skip_case(case_no):
            print(f"⏭️ Skipping case {case_no} (already completed)")
            case_no += 1
            continue
        
        # Get resume point and check if truly complete
        resume_row = scraper.get_case_resume_point(case_no)
        case_no_str = str(case_no)
        if case_no_str in scraper.progress_data:
            progress = scraper.progress_data[case_no_str]
            current_row = progress.get('current_row', 0)
            total_rows = progress.get('total_rows')
            
            # Check if case is truly complete
            if total_rows and total_rows > 0 and current_row >= total_rows:
                print(f"⏭️ Case {case_no} already fully processed ({current_row}/{total_rows} rows)")
                case_no += 1
                continue
            
            if resume_row > 0:
                print(f"\n🔄 Resuming case {case_no} from row {resume_row + 1}")
            else:
                print(f"\n🆕 Starting case {case_no} from beginning")
        else:
            print(f"\n🆕 Starting case {case_no} from beginning")
        
        # Check if we're still on the correct page (detect session timeout)
        current_url = scraper.driver.current_url
        if "index" in current_url or "frmCseSrch" not in current_url:
            print(f"⚠️ Session expired (redirected to {current_url}), re-navigating...")
            if not scraper.navigate_to_case_status():
                print("❌ Failed to re-navigate, stopping")
                break
        
        # Fill search form
        print(f"📝 Searching for case {case_no}...")
        if scraper.fill_search_form_simple(case_no=case_no):
            # Scrape results using the main browser (basic data only, no detailed fetching)
            results = scraper.scrape_results_table(case_type_empty=True, case_no=case_no)
            
            # Check if case is now complete
            if case_no_str in scraper.progress_data:
                progress = scraper.progress_data[case_no_str]
                current_row = progress.get('current_row', 0)
                total_rows = progress.get('total_rows')
                
                if total_rows and total_rows > 0 and current_row >= total_rows:
                    print(f"✅ Case {case_no} FULLY completed: {current_row}/{total_rows} rows")
                    case_no += 1  # Move to next case only if truly complete
                else:
                    print(f"⚠️ Case {case_no} INCOMPLETE: {current_row}/{total_rows if total_rows else '?'} rows - Will retry")
                    # Don't increment case_no, will retry same case
                    import time
                    time.sleep(5)
            else:
                print(f"⚠️ Case {case_no}: No progress data found")
                case_no += 1
        else:
            print(f"❌ Case {case_no}: Failed to fill search form - Will retry")
            import time
            time.sleep(5)
        
    except KeyboardInterrupt:
        print(f"\n\n🛑 Interrupted at case {case_no}. Progress saved.")
        break
    except Exception as e:
        print(f"❌ Error processing case {case_no}: {e}")
        import time
        time.sleep(5)
        # Don't increment, will retry

print("\n✅ Scraping session completed!")
scraper.stop_driver()

