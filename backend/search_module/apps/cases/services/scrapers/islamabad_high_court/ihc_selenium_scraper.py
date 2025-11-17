import time
import random
import json
import os
import sys
import pickle
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException, 
    TimeoutException, 
    StaleElementReferenceException,
    WebDriverException,
    SessionNotCreatedException
)
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
import signal
import atexit
import threading

# Add project root to Python path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
if project_root not in sys.path:
    sys.path.append(project_root)

# Also add the current directory's parent (search_module) to path
current_dir = os.path.dirname(os.path.abspath(__file__))
search_module_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))))
if search_module_path not in sys.path:
    sys.path.append(search_module_path)

# Import the database saver
from apps.cases.services.db_saver import DBSaver

# ------------------------------------------------------------------
# Ensure all relative file operations (e.g., saving JSON) happen
# with respect to the *project* root directory (search_module) rather
# than the deep scraper sub-directory from where this script is run.
# This keeps every scraper run writing to
#     search_module/cases_metadata/...
# regardless of the current working directory.
# ------------------------------------------------------------------
from pathlib import Path

# Determine the project root (the directory named "search_module")
PROJECT_ROOT = None
for parent in Path(__file__).resolve().parents:
    if parent.name == "search_module":
        PROJECT_ROOT = parent
        break

# Fall back to five levels up if the directory name was not found
if PROJECT_ROOT is None:
    PROJECT_ROOT = Path(__file__).resolve().parents[5]

# Change the working directory only if it's different
try:
    if Path.cwd() != PROJECT_ROOT:
        os.chdir(PROJECT_ROOT)
except Exception as _e:
    # If changing directory fails, continue; absolute paths can still be built
    pass

# Global shutdown flag for graceful termination
SHUTDOWN_REQUESTED = False

def global_signal_handler(signum, frame):
    """Global signal handler for graceful shutdown"""
    global SHUTDOWN_REQUESTED
    print(f"\n🛑 Received shutdown signal {signum}. Cleaning up...")
    SHUTDOWN_REQUESTED = True

# Set up global signal handlers only in main thread
if threading.current_thread() is threading.main_thread():
    signal.signal(signal.SIGINT, global_signal_handler)
    signal.signal(signal.SIGTERM, global_signal_handler)


class IHCSeleniumScraper:
    def __init__(
        self, headless=False, fetch_details=True, worker_id=None
    ):  # Added worker_id parameter
        self.base_url = "https://mis.ihc.gov.pk/index.aspx"
        self.driver = None
        self.headless = headless
        self.fetch_details = fetch_details  # Whether to fetch detailed case information
        self.worker_id = worker_id  # Track worker ID for isolation

        # Initialize database saver for real-time saving
        self.db_saver = DBSaver()

        # Enhanced stability settings
        self.max_retries = 3
        self.retry_delay = 5
        self.page_load_timeout = 120
        self.implicit_wait = 30
        
        # Session management
        self.session_start_time = time.time()
        self.last_activity_time = time.time()
        self.session_timeout = 1800  # Reduced to 30 minutes for better stability
        self.activity_update_interval = 30  # Update activity every 30 seconds
        self.last_activity_update = time.time()

        

        
        # Resume functionality
        self.progress_file = "scraper_progress.pkl"
        self.progress_data = self.load_progress()
        
        # Only set up cleanup for main thread
        if threading.current_thread() is threading.main_thread():
            atexit.register(self._cleanup_on_exit)

        # Define comprehensive search filters
        self.case_types = [
            "Writ Petition",
            "Civil Appeal",
            "Criminal Appeal",
            "Constitutional Petition",
            "Civil Revision",
            "Criminal Revision",
            "Civil Misc.",
            "Criminal Misc.",
            "Tax Appeal",
            "Service Appeal",
            "Customs Appeal",
            "Income Tax Appeal",
            "Sales Tax Appeal",
            "Federal Excise Appeal",
            "Anti-Narcotics Appeal",
            "Anti-Terrorism Appeal",
            "Family Appeal",
            "Rent Appeal",
            "Labour Appeal",
            "Insurance Appeal",
        ]

        self.years = list(range(2010, 2026))  # From 2010 to 2025
        self.case_numbers = list(range(1, 1001))  # Case numbers 1-1000

        # Limit history table extraction to first N rows for performance
        self.max_history_rows = 2

    def _cleanup_on_exit(self):
        """Cleanup function called on exit"""
        if hasattr(self, 'driver') and self.driver:
            try:
                self.save_progress()  # Save progress before shutting down
                self.driver.quit()
                print("🛑 WebDriver stopped during cleanup")
            except:
                pass





    def _safe_find_element(self, driver, by, value, timeout=10):
        """Safely find element with simple error handling"""
        try:
            self._update_activity_time()
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except (StaleElementReferenceException, TimeoutException) as e:
            print(f"⚠️ Element not found: {by}={value}")
            return None

    def _safe_find_elements(self, driver, by, value, timeout=10):
        """Safely find elements with simple error handling"""
        try:
            self._update_activity_time()
            elements = WebDriverWait(driver, timeout).until(
                EC.presence_of_all_elements_located((by, value))
            )
            return elements
        except (StaleElementReferenceException, TimeoutException) as e:
            print(f"⚠️ Element not found: {by}={value}")
            return []

    def _safe_get_text(self, element):
        """Safely get text from element"""
        try:
            return element.text.strip()
        except StaleElementReferenceException:
            return ""

    def _safe_click(self, element):
        """Safely click element"""
        try:
            element.click()
            return True
        except StaleElementReferenceException:
            return False

    def _update_activity_time(self):
        """Update last activity time for session management with throttling"""
        current_time = time.time()
        
        # Only update if enough time has passed (throttling)
        if current_time - self.last_activity_update >= self.activity_update_interval:
            self.last_activity_time = current_time
            self.last_activity_update = current_time
            print(f"🔄 Activity time updated: {time.strftime('%H:%M:%S', time.localtime(current_time))}")

    def _check_session_timeout(self):
        """Check if session has timed out"""
        if self.last_activity_time and (time.time() - self.last_activity_time) > self.session_timeout:
            return True
        return False

    def _handle_session_timeout(self, case_no, current_row, session_saved_count):
        """Handle session timeout by saving progress and attempting recovery"""
        print("⏰ Session timeout detected - attempting graceful recovery...")
        
        try:
            # Save current progress
            if case_no:
                total_rows = self.progress_data.get(str(case_no), {}).get('total_rows')
                self.update_case_progress(case_no, current_row, total_rows)
                print(f"💾 Progress saved: Case {case_no} at row {current_row}")
            
            # Save session progress
            self.save_progress()
            print(f"💾 Session progress saved: {session_saved_count} rows processed")
            
            # Try graceful recovery first
            if self._attempt_session_recovery():
                print("✅ Session recovered successfully")
                return False  # Continue with current session
            
            # If recovery fails, restart driver
            print("🔄 Recovery failed, restarting driver...")
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
            
            print("🔄 Worker restarting due to session timeout...")
            return True  # Signal to restart worker
            
        except Exception as e:
            print(f"❌ Error handling session timeout: {e}")
            return True  # Force restart on error

    def _attempt_session_recovery(self):
        """Attempt to recover the session without restarting the driver"""
        try:
            print("🔄 Attempting session recovery...")
            
            # Check if driver is still responsive
            if not self.driver:
                return False
            
            # Try to refresh the current page
            current_url = self.driver.current_url
            print(f"🔄 Refreshing page: {current_url}")
            
            self.driver.refresh()
            time.sleep(5)  # Wait for page to reload
            
            # Verify we're still on a valid page
            if "mis.ihc.gov.pk" in self.driver.current_url:
                print("✅ Session recovery successful - page refreshed")
                self._update_activity_time()
                return True
            else:
                print("⚠️ Session recovery failed - redirected to invalid page")
                return False
                
        except Exception as e:
            print(f"❌ Session recovery failed: {e}")
            return False

    def load_progress(self):
        """Load progress data from file with enhanced error handling"""
        try:
            if os.path.exists(self.progress_file):
                with open(self.progress_file, 'rb') as f:
                    progress = pickle.load(f)
                    print(f"📂 Loaded progress data: {len(progress)} cases tracked")
                    return progress
            else:
                print("📂 No existing progress file found - starting fresh")
                return {}
        except Exception as e:
            print(f"⚠️ Error loading progress: {e} - starting fresh")
            return {}

    def save_progress(self):
        """Save progress data to file with enhanced error handling"""
        try:
            # Create backup of existing file
            if os.path.exists(self.progress_file):
                backup_file = f"{self.progress_file}.backup"
                import shutil
                shutil.copy2(self.progress_file, backup_file)
            
            with open(self.progress_file, 'wb') as f:
                pickle.dump(self.progress_data, f)
            print(f"💾 Progress saved: {len(self.progress_data)} cases tracked")
        except Exception as e:
            print(f"❌ Error saving progress: {e}")

    def update_case_progress(self, case_no, row_index, total_rows=None, status="in_progress"):
        """Update progress for a specific case with enhanced error handling"""
        try:
            # Convert case_no to string for consistent storage
            case_no_str = str(case_no)
            
            if case_no_str not in self.progress_data:
                self.progress_data[case_no_str] = {
                    'case_no': case_no_str,  # Store the case number as string
                    'start_time': datetime.now().isoformat(),
                    'status': status,
                    'current_row': row_index,
                    'total_rows': total_rows,
                    'last_updated': datetime.now().isoformat()
                }
            else:
                update_data = {
                    'current_row': row_index,
                    'status': status,
                    'last_updated': datetime.now().isoformat()
                }
                # Only update total_rows if provided and not already set
                if total_rows and ('total_rows' not in self.progress_data[case_no_str] or self.progress_data[case_no_str]['total_rows'] is None):
                    update_data['total_rows'] = total_rows
                
                self.progress_data[case_no_str].update(update_data)
            
            self.save_progress()
        except Exception as e:
            print(f"⚠️ Error updating progress for case {case_no}: {e}")

    def mark_case_completed(self, case_no):
        """Mark a case as completed with enhanced error handling"""
        try:
            # Convert case_no to string for consistent lookup
            case_no_str = str(case_no)
            if case_no_str in self.progress_data:
                progress = self.progress_data[case_no_str]
                current_row = progress.get('current_row', 0)
                total_rows = progress.get('total_rows')
                
                # Only mark as completed if we have processed all rows
                if total_rows and total_rows > 0 and current_row >= total_rows:
                    progress['status'] = 'completed'
                    progress['completed_time'] = datetime.now().isoformat()
                    print(f"✅ Case {case_no} truly completed: {current_row}/{total_rows} rows")
                    self.save_progress()
                elif total_rows is None:
                    print(f"⚠️ Case {case_no} has no total rows set, keeping in progress: {current_row} rows")
                    # Keep status as in_progress until total rows are determined
                    progress['status'] = 'in_progress'
                    self.save_progress()
                else:
                    print(f"⚠️ Case {case_no} not completed yet: {current_row}/{total_rows} rows")
                    # Keep status as in_progress
                    progress['status'] = 'in_progress'
                    self.save_progress()
        except Exception as e:
            print(f"⚠️ Error marking case {case_no} as completed: {e}")

    def get_case_resume_point(self, case_no):
        """Get the resume point for a specific case"""
        try:
            # Convert case_no to string for consistent lookup
            case_no_str = str(case_no)
            if case_no_str in self.progress_data:
                progress = self.progress_data[case_no_str]
                if progress['status'] == 'in_progress':
                    current_row = progress.get('current_row', 0)
                    # If we have rows in database, resume from the next row
                    if current_row > 0:
                        return current_row + 1  # Resume from next row after what's already in DB
                    return current_row
            return 0
        except Exception as e:
            print(f"⚠️ Error getting resume point for case {case_no}: {e}")
            return 0

    def get_total_rows_for_case(self, case_no):
        """Get the total number of rows for a specific case from the database"""
        try:
            from apps.cases.models import Case
            
            # Count cases in database for this case number
            # The case_number field contains patterns like "1/2025", "2/2024", etc.
            case_pattern = f"{case_no}/"
            total_rows = Case.objects.filter(case_number__icontains=case_pattern).count()
            
            print(f"📊 Database count for case {case_no}: {total_rows} rows")
            return total_rows
        except Exception as e:
            print(f"⚠️ Error getting total rows for case {case_no}: {e}")
            return 0

    def extract_total_rows_from_pagination(self):
        """Extract total rows from pagination text like 'Showing 1 to 100 of 559 entries'"""
        try:
            # Look for pagination text that shows total entries
            pagination_selectors = [
                "//div[contains(text(), 'Showing') and contains(text(), 'of') and contains(text(), 'entries')]",
                "//span[contains(text(), 'Showing') and contains(text(), 'of') and contains(text(), 'entries')]",
                "//p[contains(text(), 'Showing') and contains(text(), 'of') and contains(text(), 'entries')]",
                "//div[contains(text(), 'entries')]",
                "//span[contains(text(), 'entries')]",
                "//p[contains(text(), 'entries')]"
            ]
            
            for selector in pagination_selectors:
                try:
                    element = self.driver.find_element(By.XPATH, selector)
                    text = element.text.strip()
                    print(f"🔍 Found pagination text: {text}")
                    
                    # Extract total from "Showing X to Y of Z entries"
                    import re
                    match = re.search(r'of\s+(\d+)\s+entries', text, re.IGNORECASE)
                    if match:
                        total_rows = int(match.group(1))
                        print(f"✅ Extracted total rows: {total_rows}")
                        return total_rows
                except:
                    continue
            
            print("⚠️ Could not find pagination text with total entries")
            return None
            
        except Exception as e:
            print(f"⚠️ Error extracting total rows from pagination: {e}")
            return None

    def should_skip_case(self, case_no):
        """Check if a case should be skipped (already completed)"""
        try:
            # Convert case_no to string for consistent lookup
            case_no_str = str(case_no)
            if case_no_str in self.progress_data:
                progress = self.progress_data[case_no_str]
                # Only skip if marked as completed
                if progress['status'] == 'completed':
                    if 'completed_time' in progress:
                        return True
                    else:
                        # Mark as in_progress if not truly completed
                        print(f"⚠️ Case {case_no} marked as completed but missing completed_time, resetting to in_progress")
                        progress['status'] = 'in_progress'
                        self.save_progress()
                        return False
            return False
        except Exception as e:
            print(f"⚠️ Error checking if case {case_no} should be skipped: {e}")
            return False

    def print_progress_summary(self):
        """Print a summary of current progress with enhanced error handling"""
        try:
            if not self.progress_data:
                print("📊 No progress data available")
                return
            
            completed = sum(1 for p in self.progress_data.values() if p['status'] == 'completed')
            in_progress = sum(1 for p in self.progress_data.values() if p['status'] == 'in_progress')
            
            print(f"📊 Progress Summary:")
            print(f"   - Total cases tracked: {len(self.progress_data)}")
            print(f"   - Completed: {completed}")
            print(f"   - In progress: {in_progress}")
            
            if in_progress > 0:
                print(f"   - Cases that can be resumed:")
                for case_no, progress in self.progress_data.items():
                    if progress['status'] == 'in_progress':
                        current_row = progress.get('current_row', 0)
                        total_rows = progress.get('total_rows')
                        if total_rows and total_rows > 0:
                            print(f"     Case {case_no}: Row {current_row}/{total_rows}")
                        else:
                            print(f"     Case {case_no}: Row {current_row}")
        except Exception as e:
            print(f"⚠️ Error printing progress summary: {e}")

    def clear_progress(self):
        """Clear all progress data (start fresh) with enhanced error handling"""
        try:
            if os.path.exists(self.progress_file):
                os.remove(self.progress_file)
                print(f"🗑️ Deleted progress file: {self.progress_file}")
            self.progress_data = {}
            print("🔄 Progress cleared - will start fresh on next run")
        except Exception as e:
            print(f"❌ Error clearing progress: {e}")

    def start_driver(self):
        """Initialize and start the Chrome WebDriver"""
        try:
            print("🚀 Initializing Selenium WebDriver...")
            options = Options()

            # Set headless mode (disabled for testing)
            options.headless = self.headless

            # Critical: Set explicit window size for iframe loading
            options.add_argument("--window-size=1920,1080")

            # Add arguments to help with stability and iframe loading
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--ignore-certificate-errors")

            # Add arguments to make the browser appear more like a real user
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)

            # Set a realistic user agent
            options.add_argument(
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            # Add arguments to prevent file access issues
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-plugins")
            options.add_argument("--disable-images")
            options.add_argument("--disable-javascript")
            options.add_argument("--disable-web-security")
            options.add_argument("--allow-running-insecure-content")
            options.add_argument("--disable-features=VizDisplayCompositor")

            # Use a custom download directory to avoid permission issues
            import tempfile

            # Create unique temp directory for each worker to prevent interference
            if hasattr(self, 'worker_id'):
                temp_dir = tempfile.mkdtemp(prefix=f"worker_{self.worker_id}_")
            else:
                temp_dir = tempfile.mkdtemp()
            
            options.add_argument(f"--user-data-dir={temp_dir}")
            options.add_argument(f"--data-path={temp_dir}")
            # Store temp dir for cleanup
            self.temp_dir = temp_dir

            # Try multiple approaches for ChromeDriver installation
            driver_path = None
            service = None

            # Clear ChromeDriver cache first
            try:
                import shutil

                cache_dir = os.path.expanduser("~/.wdm")
                if os.path.exists(cache_dir):
                    print(f"🧹 Clearing ChromeDriver cache at: {cache_dir}")
                    shutil.rmtree(cache_dir, ignore_errors=True)
            except Exception as cache_e:
                print(f"⚠️ Could not clear cache: {cache_e}")

            # Method 1: Try ChromeDriverManager with custom cache
            try:
                from webdriver_manager.core.os_manager import ChromeType

                driver_path = ChromeDriverManager(
                    chrome_type=ChromeType.GOOGLE
                ).install()
                service = Service(driver_path)
                print(f"✅ ChromeDriver installed at: {driver_path}")
            except Exception as e1:
                print(f"⚠️ ChromeDriverManager failed: {e1}")

                # Method 2: Try to find existing ChromeDriver
                try:
                    import subprocess

                    result = subprocess.run(
                        ["where", "chromedriver"], capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        driver_path = result.stdout.strip().split("\n")[0]
                        service = Service(driver_path)
                        print(f"✅ Found existing ChromeDriver at: {driver_path}")
                    else:
                        raise Exception("ChromeDriver not found in PATH")
                except Exception as e2:
                    print(f"⚠️ Existing ChromeDriver not found: {e2}")

                    # Method 3: Manual download to temp directory
                    try:
                        import urllib.request
                        import zipfile

                        # Download ChromeDriver to temp directory
                        temp_chrome_dir = os.path.join(temp_dir, "chromedriver")
                        os.makedirs(temp_chrome_dir, exist_ok=True)

                        # You would need to implement manual download here
                        # For now, we'll raise an exception
                        raise Exception("Manual ChromeDriver download not implemented")

                    except Exception as e3:
                        print(f"❌ All ChromeDriver installation methods failed")
                        raise Exception(
                            f"ChromeDriver installation failed: {e1}, {e2}, {e3}"
                        )

            # Initialize Chrome WebDriver
            if service:
                self.driver = webdriver.Chrome(service=service, options=options)
            else:
                raise Exception("No valid ChromeDriver service available")

            # Set longer timeouts
            self.driver.set_page_load_timeout(self.page_load_timeout)
            self.driver.implicitly_wait(self.implicit_wait)
            
            # Initialize session management
            self.session_start_time = time.time()
            self.last_activity_time = time.time()

            # Explicitly set window size again after driver initialization
            self.driver.set_window_size(1920, 1080)

            # Execute CDP commands to modify navigator.webdriver flag
            self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                """
                },
            )

            return True
        except Exception as e:
            print(f"❌ Error starting WebDriver: {e}")
            return False

    def stop_driver(self):
        """Stop and clean up the WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                print("🛑 WebDriver stopped")
            except:
                pass
            self.driver = None
        
        # Clean up temp directory to prevent interference
        if hasattr(self, 'temp_dir') and self.temp_dir:
            try:
                import shutil
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                print(f"🧹 Cleaned up temp directory: {self.temp_dir}")
            except Exception as e:
                print(f"⚠️ Could not clean up temp directory: {e}")

    def navigate_to_case_status(self):
        """Navigate to the Case Status page"""
        try:
            print("🌐 Navigating to MIS page...")
            self.driver.get(self.base_url)

            # Wait for page to load
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            print("✅ Successfully loaded MIS page")
            time.sleep(2)

            # Click the Case Status link
            print("🔍 Looking for Case Status element...")
            case_status_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//div[contains(@class, 'GrdB')]//h4[contains(text(), 'Case Status')]",
                    )
                )
            )

            # Get the href attribute before clicking
            href = case_status_button.get_attribute("href")
            print(f"🔗 Case Status href: {href}")

            # Try clicking with JavaScript
            self.driver.execute_script("arguments[0].click();", case_status_button)
            print("✅ Clicked Case Status button")

            # Check if we're still on the same page
            time.sleep(2)
            current_url = self.driver.current_url
            print(f"📍 Current URL after click: {current_url}")

            # Check if a new window opened or if we're still on the same page
            print("⏳ Checking for navigation...")
            time.sleep(3)  # Give time for any navigation to happen

            # Check if a new window opened
            if len(self.driver.window_handles) > 1:
                print("🔄 New window detected, switching...")
                self.driver.switch_to.window(self.driver.window_handles[1])
                print("✅ Switched to new tab")

                # Wait for iframe to load in new window
                print("⏳ Waiting for iframe to load...")
                iframe = WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//iframe[contains(@src, 'frmCaseStatus.a')]")
                    )
                )
                print(f"📝 Found iframe: {iframe.get_attribute('src')}")
                self.driver.switch_to.frame(iframe)
                print("✅ Switched to iframe")
            else:
                print("ℹ️ No new window detected, staying on current page")
                # The form elements should already be available on the current page
                print("⏳ Waiting for form to load on current page...")

            # Wait for the form to load (either in iframe or on current page)
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.NAME, "ctl00$ContentPlaceHolder1$ddlCaseType")
                    )
                )
                print("✅ Form loaded successfully")
            except TimeoutException:
                # Try alternative element names based on our debugging
                print("⏳ Trying alternative form elements...")
                try:
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.ID, "ddlCategory"))
                    )
                    print("✅ Alternative form elements found")
                except TimeoutException:
                    print("❌ No form elements found")
                    raise

            return True

        except Exception as e:
            print(f"❌ Error navigating to case status: {e}")
            return False

    def fill_search_form_simple(self, case_no=1):
        """Simple form filling: reset form, set case number, search"""
        try:
            print(f"📝 Filling search form (SIMPLE MODE) for case {case_no}...")

            # Step 1: Clear all fields
            print("🧹 Step 1: Clearing all fields...")
            try:
                # First, try to remove any overlay that might be blocking the button
                print(
                    "🔍 Checking for overlay div that might block the Clear button..."
                )
                try:
                    overlay_selectors = [
                        "//div[@id='divstart']",
                        "//div[contains(@style, 'z-index:10')]",
                        "//div[contains(@style, 'position:absolute')]",
                        "//div[contains(@style, 'background-color:white')]",
                    ]

                    for selector in overlay_selectors:
                        try:
                            overlays = self.driver.find_elements(By.XPATH, selector)
                            for overlay in overlays:
                                if overlay.is_displayed():
                                    print(
                                        f"⚠️ Found overlay div, attempting to remove it..."
                                    )
                                    self.driver.execute_script(
                                        "arguments[0].remove();", overlay
                                    )
                                    print("✅ Removed overlay div")
                                    time.sleep(1)
                        except Exception as e:
                            continue
                except Exception as e:
                    print(f"⚠️ Error handling overlay: {e}")

                # Now try to click the Clear button
                clear_button = self.driver.find_element(By.ID, "btnClear")

                # Try multiple approaches to click the button
                try:
                    # Approach 1: Direct click
                    clear_button.click()
                    print("✅ Cleared all form fields (direct click)")
                except Exception as e1:
                    print(f"⚠️ Direct click failed: {e1}")
                    try:
                        # Approach 2: JavaScript click
                        self.driver.execute_script(
                            "arguments[0].click();", clear_button
                        )
                        print("✅ Cleared all form fields (JavaScript click)")
                    except Exception as e2:
                        print(f"⚠️ JavaScript click failed: {e2}")
                        try:
                            # Approach 3: Scroll into view and click
                            self.driver.execute_script(
                                "arguments[0].scrollIntoView(true);", clear_button
                            )
                            time.sleep(1)
                            clear_button.click()
                            print("✅ Cleared all form fields (scroll + click)")
                        except Exception as e3:
                            print(f"⚠️ Scroll + click failed: {e3}")
                            # Approach 4: Try to clear fields manually
                            print("🔄 Attempting manual field clearing...")
                            try:
                                # Clear case number field manually
                                case_input = self.driver.find_element(
                                    By.ID, "txtCaseno"
                                )
                                case_input.clear()
                                print("✅ Manually cleared case number field")
                            except:
                                pass
                            try:
                                # Reset institution dropdown manually
                                institution_select = Select(
                                    self.driver.find_element(By.ID, "ddlInst")
                                )
                                institution_select.select_by_index(0)
                                print("✅ Manually reset institution dropdown")
                            except:
                                pass

                time.sleep(3)  # Wait for form to reset
                print("✅ Form clearing completed")

            except Exception as e:
                print(f"❌ Could not find Clear button: {e}")
                # Continue anyway - the form might already be clear
                print("🔄 Continuing without clearing form...")

            # Step 2: Select institution (required)
            print("🏛️ Step 2: Selecting institution...")
            try:
                # Try multiple selectors for institution dropdown
                institution_selectors = [
                    (By.ID, "ddlInst"),
                    (By.NAME, "ddlInst"),
                    (By.CSS_SELECTOR, "select[id*='Inst']"),
                    (By.CSS_SELECTOR, "select[name*='Inst']"),
                    (By.XPATH, "//select[contains(@id, 'Inst')]"),
                    (By.XPATH, "//select[contains(@name, 'Inst')]")
                ]
                
                institution_select = None
                for selector in institution_selectors:
                    try:
                        element = self.driver.find_element(*selector)
                        institution_select = Select(element)
                        print(f"✅ Found institution dropdown with selector: {selector}")
                        break
                    except:
                        continue
                
                if institution_select:
                    # Try to select by index, value, or visible text
                    try:
                        institution_select.select_by_value("1")  # Islamabad High Court
                        time.sleep(3)  # Wait for dropdown to populate
                        print("✅ Selected Islamabad High Court by value")
                    except:
                        try:
                            institution_select.select_by_index(1)
                            time.sleep(3)
                            print("✅ Selected Islamabad High Court by index")
                        except:
                            try:
                                institution_select.select_by_visible_text("Islamabad High Court")
                                time.sleep(3)
                                print("✅ Selected Islamabad High Court by text")
                            except:
                                print("⚠️ Could not select institution, continuing anyway...")
                else:
                    print("⚠️ Institution dropdown not found, continuing anyway...")
                    
            except Exception as e:
                print(f"⚠️ Institution selection issue: {e}, continuing anyway...")

            # Step 3: Enter the specified case number
            print(f"🔢 Step 3: Entering case number = {case_no}...")
            try:
                case_input = self.driver.find_element(By.ID, "txtCaseno")
                case_input.clear()
                case_input.send_keys(str(case_no))
                print(f"✅ Entered case number: {case_no}")
            except Exception as e:
                print(f"❌ Failed to enter case number: {e}")
                return False

            # Step 4: Click search button
            print("🔍 Step 4: Clicking search button...")
            try:
                search_button = self.driver.find_element(By.ID, "btnSearch")
                search_button.click()
                print("✅ Clicked search button")
                print("✅ Form submitted successfully")
                return True
            except Exception as e:
                print(f"❌ Failed to click search button: {e}")
                return False

        except Exception as e:
            print(f"❌ Error filling search form: {e}")
            return False

    def scrape_results_table(self, case_type_empty=False, case_no=None):
        """Scrape the results table and return case data with granular progress tracking"""
        try:
            print("🔍 Looking for results...")

            # Validate we're still on the correct page before scraping
            if not self.validate_current_page():
                print(f"❌ Page validation failed before scraping")
                return None
            
            # Check for unexpected redirects
            if not self.check_for_unexpected_redirects():
                print(f"❌ Unexpected redirect detected before scraping")
                return None

            # Get resume point for this case
            resume_row = self.get_case_resume_point(case_no) if case_no else 0
            resume_page = 1  # Always start from page 1, but can resume from specific row
            
            # Track rows saved in this session
            session_saved_count = 0
            
            if resume_row > 0:
                print(f"🔄 Resuming case {case_no} from row {resume_row}")
            else:
                print(f"🆕 Starting case {case_no} from beginning")

            # Check for any alerts that might appear
            try:
                alert = self.driver.switch_to.alert
                alert_text = alert.text
                print(f"⚠️ Alert detected: {alert_text}")
                alert.accept()  # Dismiss the alert
                print("✅ Alert dismissed")
                time.sleep(2)  # Wait a bit after dismissing alert
            except:
                # No alert present, continue normally
                pass

            # If case type is empty, we expect 500+ results, so wait much longer
            if case_type_empty:
                print(
                    "⏳ Case type is empty - expecting 500+ results, waiting longer..."
                )
                initial_wait = 30  # Wait 30 seconds initially for bulk data
                stability_check_interval = 10  # Check for stability every 10 seconds
                stability_threshold = (
                    60  # Consider stable if no new data for 60 seconds
                )
            else:
                initial_wait = 15  # Normal wait for filtered results
                stability_check_interval = 5  # Check for stability every 5 seconds
                stability_threshold = (
                    30  # Consider stable if no new data for 30 seconds
                )

            print(f"⏳ Initial wait: {initial_wait} seconds...")
            time.sleep(initial_wait)

            # Phase 1: Wait for table to appear
            print("🔍 Phase 1: Waiting for results table to appear...")
            table = None
            used_selector = None
            table_wait_time = 0
            max_table_wait = 120  # Wait up to 2 minutes for table to appear

            while table_wait_time < max_table_wait:
                # Try different table selectors
                table_selectors = [
                    (By.ID, "grdCaseStatus"),
                    (By.TAG_NAME, "table"),
                    (By.XPATH, "//table[contains(@class, 'Grid')]"),
                    (By.XPATH, "//table[contains(@class, 'table')]"),
                    (By.XPATH, "//div[contains(@class, 'Grid')]//table"),
                    (By.CSS_SELECTOR, "table.Grid"),
                    (By.CSS_SELECTOR, "table.table"),
                    (By.CSS_SELECTOR, "div.Grid table"),
                    (By.CSS_SELECTOR, "div.table table"),
                ]

                for selector in table_selectors:
                    try:
                        table = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located(selector)
                        )
                        used_selector = selector
                        print(f"✅ Found results table with selector: {selector}")
                        break
                    except TimeoutException:
                        continue

                if table:
                    break
                else:
                    print(
                        f"⏳ No table found yet, waiting... ({table_wait_time}/{max_table_wait}s)"
                    )
                    time.sleep(10)
                    table_wait_time += 10

            if not table:
                print("❌ Table not found after maximum wait time")
                return []

            # Phase 2: Wait for data to be fully loaded - specifically wait for 50+ rows
            print("🔍 Phase 2: Waiting for 50+ rows to be loaded...")
            last_row_count = 0
            stable_count = 0
            data_wait_time = 0

            while True:  # Infinite loop - wait until we have 50+ rows
                try:
                    # Get all rows from the table
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    current_row_count = len(rows)

                    print(
                        f"📊 Found {current_row_count} table rows (was {last_row_count})"
                    )

                    # Check if we have enough rows (50+)
                    if current_row_count >= 50:
                        print(
                            f"🎯 SUCCESS! Found {current_row_count} rows (50+ required)"
                        )
                        stable_count += stability_check_interval

                        # If we have 50+ rows and they've been stable, we're done
                        if stable_count >= stability_threshold:
                            print(
                                f"✅ Data loading complete: {current_row_count} rows stable for {stable_count}s"
                            )
                            break
                        else:
                            print(
                                f"⏳ Have 50+ rows but waiting for stability ({stable_count}/{stability_threshold}s)"
                            )
                    elif current_row_count > last_row_count:
                        print(
                            f"🔄 Data still loading... {current_row_count - last_row_count} new rows detected"
                        )
                        last_row_count = current_row_count
                        stable_count = 0  # Reset stability counter
                    elif current_row_count == last_row_count:
                        stable_count += stability_check_interval
                        print(
                            f"⏳ Waiting for more rows... ({stable_count}s without new rows)"
                        )

                        # If we've been waiting too long without reaching 50 rows, something is wrong
                        if stable_count > 120:  # 2 minutes without progress
                            print(
                                f"⚠️ Warning: Only {current_row_count} rows found after 2 minutes"
                            )
                            print("⏳ Continuing to wait for more rows...")
                            stable_count = 0  # Reset and keep waiting
                    elif current_row_count == 0:
                        print("ℹ️ No rows found yet, waiting for initial data...")
                        stable_count = 0
                    elif current_row_count == 1:
                        print("ℹ️ Only header row found, waiting for data rows...")
                        stable_count = 0

                    # Wait before next chec
                    time.sleep(stability_check_interval)

                except Exception as e:
                    print(f"⚠️ Error while monitoring data loading: {e}")
                    time.sleep(stability_check_interval)
                    data_wait_time += stability_check_interval

            # Phase 3: Extract total rows from pagination
            print("🔍 Phase 3: Extracting total rows from pagination...")
            total_rows = self.extract_total_rows_from_pagination()
            if total_rows:
                print(f"📊 Total rows for this case: {total_rows}")
                # Update progress with total rows if this is a new case or if total_rows is not set
                if case_no:
                    current_total = self.progress_data.get(str(case_no), {}).get('total_rows') if str(case_no) in self.progress_data else None
                    if current_total is None:
                        self.update_case_progress(case_no, 0, total_rows)
                        print(f"✅ Updated Case {case_no} with total rows: {total_rows}")
                    else:
                        print(f"ℹ️ Case {case_no} already has total rows: {current_total}")
            else:
                print("⚠️ Could not extract total rows from pagination")
                # Try to get from existing progress data
                if case_no and str(case_no) in self.progress_data:
                    total_rows = self.progress_data[str(case_no)].get('total_rows')
                    if total_rows:
                        print(f"📊 Using existing total rows for Case {case_no}: {total_rows}")
                    else:
                        print(f"⚠️ No total rows available for Case {case_no}")
                else:
                    total_rows = None

            # Phase 4: Change rows display to 100 and wait for more data
            print("🔍 Phase 4: Changing rows display to 100...")
            try:
                # Find and change the "Show" dropdown to 100
                print("📊 Looking for 'Show' dropdown...")
                show_dropdown = None

                # Try different selectors for the dropdown
                dropdown_selectors = [
                    (By.XPATH, "//select[contains(@onchange, 'Show')]"),
                    (By.XPATH, "//select[contains(@name, 'Show')]"),
                    (By.XPATH, "//select[contains(@id, 'Show')]"),
                    (By.XPATH, "//select[option[contains(text(), '50')]]"),
                    (By.XPATH, "//select[option[contains(text(), '100')]]"),
                    (By.CSS_SELECTOR, "select"),
                    (By.TAG_NAME, "select"),
                ]

                for selector in dropdown_selectors:
                    try:
                        show_dropdown = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located(selector)
                        )
                        print(f"✅ Found dropdown with selector: {selector}")
                        break
                    except TimeoutException:
                        continue

                if show_dropdown:
                    # Change to 100 rows
                    print("📊 Changing dropdown to 100 rows...")
                    try:
                        dropdown_select = Select(show_dropdown)
                        dropdown_select.select_by_value("100")
                        print("✅ Changed dropdown to 100 rows")

                        # Wait for the page to reload with 100 rows
                        print("⏳ Waiting for page to reload with 100 rows...")
                        time.sleep(5)  # Initial wait for page reload

                        # Wait for new data to load (100 rows)
                        print("🔍 Phase 4: Waiting for 100 rows to load...")
                        new_row_count = 0
                        stable_count = 0

                        while True:  # Wait until we have 100+ rows
                            try:
                                # Get current rows
                                current_rows = table.find_elements(By.TAG_NAME, "tr")
                                current_count = len(current_rows)

                                print(
                                    f"📊 Found {current_count} table rows (target: 100+)"
                                )

                                if current_count >= 100:
                                    print(
                                        f"🎯 SUCCESS! Found {current_count} rows (100+ required)"
                                    )
                                    stable_count += stability_check_interval

                                    if stable_count >= stability_threshold:
                                        print(
                                            f"✅ 100 rows loading complete: {current_count} rows stable for {stable_count}s"
                                        )
                                        break
                                    else:
                                        print(
                                            f"⏳ Have 100+ rows but waiting for stability ({stable_count}/{stability_threshold}s)"
                                        )
                                elif current_count > new_row_count:
                                    print(
                                        f"🔄 More rows loading... {current_count - new_row_count} new rows detected"
                                    )
                                    new_row_count = current_count
                                    stable_count = 0
                                else:
                                    stable_count += stability_check_interval
                                    print(
                                        f"⏳ Waiting for more rows... ({stable_count}s without new rows)"
                                    )

                                    if stable_count > 120:  # 2 minutes without progress
                                        print(
                                            f"⚠️ Warning: Only {current_count} rows found after 2 minutes"
                                        )
                                        print("⏳ Continuing to wait for more rows...")
                                        stable_count = 0

                                time.sleep(stability_check_interval)

                            except Exception as e:
                                print(f"⚠️ Error while monitoring 100 rows loading: {e}")
                                time.sleep(stability_check_interval)

                        # Now process all pages with pagination
                        print("🔍 Phase 5: Processing all pages with pagination...")
                        all_cases = []
                        page_number = resume_page if case_no else 1
                        total_processed = 0

                        # Skip to the resume page if needed
                        if case_no and resume_page > 1:
                            print(f"⏭️ Skipping to page {resume_page} for case {case_no}")
                            # Navigate to the resume page
                            for _ in range(resume_page - 1):
                                try:
                                    next_button = WebDriverWait(self.driver, 3).until(
                                        EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Next')]"))
                                    )
                                    if next_button and next_button.is_enabled():
                                        next_button.click()
                                        time.sleep(2)
                                        page_number += 1
                                    else:
                                        break
                                except:
                                    break

                        while True:  # Continue until no more pages
                            # Check for shutdown request before processing each page
                            if SHUTDOWN_REQUESTED:
                                print("🛑 Shutdown requested, stopping page processing")
                                return all_cases
                                
                            print(f"\n📄 Processing Page {page_number}...")

                            # Get current page rows
                            current_rows = table.find_elements(By.TAG_NAME, "tr")
                            print(f"📊 Found {len(current_rows)} rows on current page")

                            if len(current_rows) > 1:
                                page_cases = []

                                # Process rows on current page, starting from resume row if needed
                                # Calculate which row to start from based on resume point and current page
                                print(f"🔍 DEBUG: Checking resume condition - case_no: '{case_no}' (type: {type(case_no)}), resume_row: {resume_row} (type: {type(resume_row)})")
                                if case_no and resume_row > 0:
                                    # Calculate total rows processed before current page
                                    rows_per_page = 100  # Assuming 100 rows per page
                                    rows_before_current_page = (page_number - 1) * rows_per_page
                                    
                                    if page_number == 1:
                                        # On first page, start from resume_row
                                        start_row = resume_row
                                        print(f"🔍 DEBUG: Case {case_no}, Page {page_number}, Resume row: {resume_row}, Start row: {start_row}")
                                    else:
                                        # On subsequent pages, check if we've already processed this page
                                        if resume_row <= rows_before_current_page:
                                            # We've already processed this page, skip it
                                            print(f"⏭️ Skipping page {page_number} (already processed)")
                                            continue
                                        elif resume_row <= rows_before_current_page + rows_per_page:
                                            # We've partially processed this page, start from the correct row
                                            start_row = resume_row - rows_before_current_page
                                            print(f"🔍 DEBUG: Case {case_no}, Page {page_number}, Resume row: {resume_row}, Rows before page: {rows_before_current_page}, Start row on this page: {start_row}")
                                        else:
                                            # Start from beginning of this page
                                            start_row = 1
                                else:
                                    start_row = 1
                                    print(f"🔍 DEBUG: Case {case_no}, Page {page_number}, No resume row, Start row: {start_row}")
                                
                                # Track consecutive stale element errors (session timeout detection)
                                consecutive_stale_errors = 0
                                max_consecutive_stale = 5  # Stop after 5 consecutive stale errors
                                
                                for i, row in enumerate(current_rows, 1):
                                    # Check if too many consecutive stale errors (session timeout)
                                    if consecutive_stale_errors >= max_consecutive_stale:
                                        print(f"🚨 CRITICAL: {consecutive_stale_errors} consecutive stale element errors!")
                                        print(f"📍 Current URL: {self.driver.current_url}")
                                        print(f"⚠️ Session expired - page likely redirected. Stopping row processing.")
                                        # Return early to trigger re-navigation in run_scraper.py
                                        return all_cases
                                    
                                    # Skip rows before resume point (on any page when resuming)
                                    if case_no and resume_row > 0 and i < start_row:
                                        print(f"⏭️ Skipping row {i} (before resume point {start_row})")
                                        continue
                                    elif case_no and resume_row > 0 and i >= start_row:
                                        print(f"✅ Processing row {i} (resume point reached)")
                                    
                                    # Progress will be updated after successful save
                                    
                                    # Check for shutdown request
                                    if SHUTDOWN_REQUESTED:
                                        print("🛑 Shutdown requested, stopping row processing")
                                        return all_cases
                                    
                                    # Proactive session monitoring
                                    if self._check_session_timeout():
                                        print(f"⚠️ Session timeout detected at row {i}, attempting recovery...")
                                        if self._handle_session_timeout(case_no, i, session_saved_count):
                                            # Return None to signal worker restart
                                            return None
                                        else:
                                            # Session recovered, continue
                                            print(f"✅ Session recovered, continuing from row {i}")
                                            continue
                                    
                                    # Proactive activity updates during intensive operations
                                    if i % 5 == 0:  # Update every 5 rows during intensive operations
                                        self._update_activity_time()
                                    

                                    
                                    # Periodic navigation validation (every 10 rows)
                                    if i % 10 == 0:
                                        if not self.validate_current_page():
                                            print(f"⚠️ Navigation validation failed at row {i}, attempting recovery...")
                                            if not self.recover_navigation():
                                                print(f"❌ Navigation recovery failed, stopping scraping")
                                                return all_cases
                                        if not self.check_for_unexpected_redirects():
                                            print(f"⚠️ Unexpected redirect detected at row {i}, attempting recovery...")
                                            if not self.recover_navigation():
                                                print(f"❌ Navigation recovery failed, stopping scraping")
                                                return all_cases
                                    
                                    try:
                                        # Update activity time for session tracking
                                        self._update_activity_time()
                                        
                                        # Find cells directly from the row element
                                        cells = row.find_elements(By.TAG_NAME, "td")

                                        if len(cells) >= 7:
                                            case_data = {
                                                "SR": (
                                                    cells[0].text.strip() if len(cells) > 0 else ""
                                                ),
                                                "INSTITUTION": (
                                                    cells[1].text.strip() if len(cells) > 1 else ""
                                                ),
                                                "CASE_NO": (
                                                    cells[2].text.strip() if len(cells) > 2 else ""
                                                ),
                                                "CASE_TITLE": (
                                                    cells[3].text.strip() if len(cells) > 3 else ""
                                                ),
                                                "BENCH": (
                                                    cells[4].text.strip() if len(cells) > 4 else ""
                                                ),
                                                "HEARING_DATE": (
                                                    cells[5].text.strip() if len(cells) > 5 else ""
                                                ),
                                                "STATUS": (
                                                    cells[6].text.strip() if len(cells) > 6 else ""
                                                ),
                                                # HISTORY field removed - now computed from actual data relationships
                                                "DETAILS": (
                                                    cells[8].text.strip() if len(cells) > 8 else ""
                                                ),
                                            }

                                            # Only add if we have meaningful data
                                            if (
                                                case_data["SR"]
                                                and case_data["SR"].isdigit()
                                                and case_data["CASE_NO"]
                                            ):
                                                # Fetch detailed information for decided cases (if enabled)
                                                if (
                                                    self.fetch_details
                                                    and case_data["STATUS"] == "Decided"
                                                ):
                                                    print(
                                                        f"🔍 Page {page_number}, Row {i}: Fetching details for decided case {case_data['CASE_NO']}"
                                                    )

                                                    # First, fetch history data (Orders, Comments, Case CMs, Judgement)
                                                    history_data = (
                                                        self.fetch_case_history(
                                                            row, case_data
                                                        )
                                                    )
                                                    if history_data:
                                                        case_data.update(history_data)
                                                        print(
                                                            f"✅ Page {page_number}, Row {i}: Added history data for decided case"
                                                        )
                                                    else:
                                                        print(
                                                            f"⚠️ Page {page_number}, Row {i}: Failed to fetch history data for decided case"
                                                        )

                                                    # Then, fetch detailed case information
                                                    detailed_info = (
                                                        self.fetch_case_details(row)
                                                    )
                                                    if detailed_info:
                                                        case_data.update(detailed_info)
                                                        print(
                                                            f"✅ Page {page_number}, Row {i}: Added detailed info for decided case"
                                                        )
                                                    else:
                                                        print(
                                                            f"⚠️ Page {page_number}, Row {i}: Failed to fetch details for decided case"
                                                        )

                                                page_cases.append(case_data)
                                                print(
                                                    f"✅ Page {page_number}, Row {i}: Added case with SR={case_data['SR']}"
                                                )

                                                # PROGRESS TRACKING COMPLETELY REMOVED - NO PROGRESS UPDATES

                                                # REAL-TIME SAVING: Save this row immediately to prevent data loss
                                                saved = self.save_single_row_realtime(
                                                    case_data, case_no, page_number, i
                                                )
                                                if saved:
                                                    # Reset stale error counter on successful save (session is working)
                                                    consecutive_stale_errors = 0
                                                    # Update progress after successful save
                                                    actual_saved_count = self.get_total_rows_for_case(case_no)
                                                    session_saved_count += 1
                                                    # Get total rows from progress data
                                                    total_rows = self.progress_data.get(str(case_no), {}).get('total_rows')
                                                    # Update progress with new database count
                                                    self.update_case_progress(case_no, actual_saved_count, total_rows)
                                                    print(f"💾 REAL-TIME PROGRESS: Row saved to database for case {case_no} (Total in DB: {actual_saved_count}, Session total: {session_saved_count})")
                                            else:
                                                print(
                                                    f"⚠️ Page {page_number}, Row {i}: Skipped (SR='{case_data.get('SR', 'N/A')}', CASE_NO='{case_data.get('CASE_NO', 'N/A')}')"
                                                )
                                        else:
                                            print(
                                                f"⚠️ Page {page_number}, Row {i}: Not enough cells ({len(cells)})"
                                            )

                                    except StaleElementReferenceException as e:
                                        consecutive_stale_errors += 1  # Increment counter for session timeout detection
                                        print(f"⚠️ Stale element error on page {page_number}, row {i}: {e}")
                                        print(f"⚠️ Consecutive stale errors: {consecutive_stale_errors}/{max_consecutive_stale}")
                                        # Update progress even for failed rows to track where we reached
                                        if case_no:
                                            total_rows = self.progress_data.get(str(case_no), {}).get('total_rows')
                                            self.update_case_progress(case_no, i, total_rows)
                                        # Skip this problematic row and continue
                                        continue
                                    except Exception as e:
                                        print(
                                            f"⚠️ Error processing page {page_number}, row {i}: {e}"
                                        )
                                        continue

                                # Add page cases to total (for compatibility, but real saving is done in real-time)
                                all_cases.extend(page_cases)
                                total_processed += len(page_cases)
                                print(
                                    f"📊 Page {page_number}: Processed {len(page_cases)} cases (Total: {total_processed})"
                                )

                                # PROGRESS TRACKING COMPLETELY REMOVED - NO PAGE COMPLETION UPDATES

                                # Show real-time saving progress (actual database saves)
                                actual_saved_count = self.get_total_rows_for_case(case_no)
                                print(
                                    f"💾 REAL-TIME PROGRESS: {session_saved_count} rows saved in this session, {actual_saved_count} total in database for case {case_no}"
                                )

                                # Check if this is the last page by looking for Next button
                                # Don't assume less than 100 entries means last page
                                # Instead, always try to find the Next button

                                # Check if there's a "Next" button to go to next page
                                print("🔍 Looking for 'Next' button...")
                                next_button = None

                                # Try different selectors for the Next button
                                next_button_selectors = [
                                    (By.XPATH, "//a[contains(text(), 'Next')]"),
                                    (By.XPATH, "//button[contains(text(), 'Next')]"),
                                    (By.XPATH, "//input[@value='Next']"),
                                    (By.XPATH, "//a[contains(@class, 'next')]"),
                                    (By.XPATH, "//button[contains(@class, 'next')]"),
                                    (By.CSS_SELECTOR, "a.next"),
                                    (By.CSS_SELECTOR, "button.next"),
                                    (By.CSS_SELECTOR, "input[value='Next']"),
                                ]

                                for selector in next_button_selectors:
                                    try:
                                        next_button = WebDriverWait(
                                            self.driver, 3
                                        ).until(EC.element_to_be_clickable(selector))
                                        print(
                                            f"✅ Found Next button with selector: {selector}"
                                        )
                                        break
                                    except TimeoutException:
                                        continue

                                if next_button and next_button.is_enabled():
                                    print(
                                        f"⏭️ Clicking Next button to go to page {page_number + 1}..."
                                    )
                                    try:
                                        # Scroll to the Next button to make it visible
                                        self.driver.execute_script(
                                            "arguments[0].scrollIntoView(true);",
                                            next_button,
                                        )
                                        time.sleep(2)  # Wait for scroll

                                        next_button.click()
                                        print(f"✅ Clicked Next button")

                                        # Wait for new page to load
                                        print("⏳ Waiting for next page to load...")
                                        time.sleep(5)  # Wait for page load

                                        # Wait for table to reload
                                        table_reload_wait = 0
                                        while (
                                            table_reload_wait < 60
                                        ):  # Wait up to 60 seconds for table reload
                                            try:
                                                new_rows = table.find_elements(
                                                    By.TAG_NAME, "tr"
                                                )
                                                if len(new_rows) > 1:
                                                    print(
                                                        f"✅ New page loaded with {len(new_rows)} rows"
                                                    )
                                                    break
                                                else:
                                                    print(
                                                        f"⏳ Waiting for table to reload... ({table_reload_wait}/60s)"
                                                    )
                                                    time.sleep(2)
                                                    table_reload_wait += 2
                                            except Exception as e:
                                                print(
                                                    f"⚠️ Error checking table reload: {e}"
                                                )
                                                time.sleep(2)
                                                table_reload_wait += 2

                                        page_number += 1
                                        continue  # Process next page

                                    except Exception as e:
                                        print(f"❌ Error clicking Next button: {e}")
                                        print("🏁 Stopping due to Next button error")
                                        break
                                else:
                                    print(
                                        "🏁 No Next button found or it's disabled - reached last page"
                                    )
                                    print(
                                        f"✅ All pages processed successfully. Total: {total_processed} cases"
                                    )
                                    break
                            else:
                                print("❌ No data rows found on current page")
                                break

                        print(f"📊 Total cases processed: {len(all_cases)}")

                        # Mark case as completed in progress tracking
                        if case_no:
                            self.mark_case_completed(case_no)
                            print(f"✅ Case {case_no} marked as completed with {len(all_cases)} total cases")

                        if case_type_empty and len(all_cases) > 50:
                            print(
                                f"🎯 SUCCESS! Found {len(all_cases)} cases with empty case type (all pages)"
                            )

                        return all_cases

                    except Exception as e:
                        print(f"❌ Error changing dropdown to 100: {e}")
                        return []
                else:
                    print("❌ Could not find 'Show' dropdown")
                    return []

            except Exception as e:
                print(f"❌ Error in Phase 3: {e}")
                return []

        except Exception as e:
            print(f"❌ Error scraping results table: {e}")
            return []
        


    def fetch_case_details(self, case_row_element):
        """
        Fetch detailed case information by clicking the 'i' icon in the Details column
        for cases with 'Decided' status

        Args:
            case_row_element: The table row element containing the case

        Returns:
            dict: Detailed case information or empty dict if failed
        """
        try:
            # Check if this case has 'Decided' status
            cells = case_row_element.find_elements(By.TAG_NAME, "td")
            if len(cells) < 7:
                return {}

            status = cells[6].text.strip()
            if status != "Decided":
                return {}  # Only fetch details for decided cases

            print(f"🔍 Fetching details for decided case: {cells[2].text.strip()}")

            # Find the 'i' icon in the Details column (last column)
            details_cell = cells[-1] if len(cells) > 8 else None
            if not details_cell:
                print("⚠️ No details column found")
                return {}

            # Look for the 'i' icon or clickable element
            detail_links = details_cell.find_elements(By.TAG_NAME, "a")
            detail_icons = details_cell.find_elements(By.TAG_NAME, "i")
            detail_buttons = details_cell.find_elements(By.TAG_NAME, "button")
            detail_spans = details_cell.find_elements(By.TAG_NAME, "span")

            detail_element = None

            # Try to find the clickable element
            if detail_links:
                detail_element = detail_links[0]
                print("✅ Found detail link")
            elif detail_icons:
                detail_element = detail_icons[0]
                print("✅ Found detail icon")
            elif detail_buttons:
                detail_element = detail_buttons[0]
                print("✅ Found detail button")
            elif detail_spans:
                detail_element = detail_spans[0]
                print("✅ Found detail span")
            else:
                # Try to click the cell itself
                detail_element = details_cell
                print("✅ Using detail cell")

            if not detail_element:
                print("⚠️ No clickable detail element found")
                return {}

            # Store current URL and window handle
            original_url = self.driver.current_url
            original_window = self.driver.current_window_handle

            print(f"📍 Current URL before click: {original_url}")

            # Click the detail element
            try:
                # Try different click methods
                try:
                    detail_element.click()
                    print("✅ Clicked detail element (normal click)")
                except:
                    try:
                        self.driver.execute_script(
                            "arguments[0].click();", detail_element
                        )
                        print("✅ Clicked detail element (JavaScript click)")
                    except:
                        # Try to get the href if it's a link
                        href = detail_element.get_attribute("href")
                        if href:
                            self.driver.get(href)
                            print(f"✅ Navigated to detail URL: {href}")
                        else:
                            print("⚠️ Could not click or navigate to detail element")
                            return {}
            except Exception as e:
                print(f"⚠️ Error clicking detail element: {e}")
                return {}

            # Wait for page change
            time.sleep(3)

            # Check if we have a new window/tab
            new_window = None
            for window_handle in self.driver.window_handles:
                if window_handle != original_window:
                    new_window = window_handle
                    break

            if new_window:
                self.driver.switch_to.window(new_window)
                print("✅ Switched to new detail window")
            else:
                print("ℹ️ No new window opened, checking if current page changed")
                current_url = self.driver.current_url
                if current_url != original_url:
                    print(f"✅ Page URL changed to: {current_url}")
                else:
                    print("⚠️ Page URL did not change, might be a modal/popup")

            # Wait for detail page to load
            time.sleep(2)

            # Check if we got the "Details not available" popup first
            print("🔍 Checking for 'Details not available' popup...")

            try:
                # Look for the "Details are not available" popup
                details_not_available_selectors = [
                    "//*[contains(text(), 'Details are not available')]",
                    "//*[contains(text(), 'Case may not be fixed yet')]",
                    "//*[contains(text(), 'Case connected with main case')]",
                    "//*[contains(text(), 'Details are not available') or contains(text(), 'Case may not be fixed yet')]",
                ]

                details_popup_found = False
                for selector in details_not_available_selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        if elements:
                            for element in elements:
                                if element.is_displayed():
                                    details_popup_found = True
                                    print("⚠️ Found 'Details not available' popup")
                                    break
                        if details_popup_found:
                            break
                    except:
                        continue

                # If we found the "Details not available" popup, click the Close button
                if details_popup_found:
                    print(
                        "🔍 Looking for 'Close' button in details not available popup..."
                    )

                    close_button_selectors = [
                        "//button[contains(text(), 'Close')]",
                        "//button[@data-dismiss='modal']",
                        "//button[contains(@class, 'ButtonClass')]",
                        "//*[contains(text(), 'Close') and contains(@class, 'ButtonClass')]",
                        "//button[contains(@class, 'btn') and contains(text(), 'Close')]",
                    ]

                    close_button = None
                    for selector in close_button_selectors:
                        try:
                            elements = self.driver.find_elements(By.XPATH, selector)
                            for element in elements:
                                if element.is_displayed() and element.is_enabled():
                                    close_button = element
                                    print(
                                        f"✅ Found Close button with selector: {selector}"
                                    )
                                    break
                            if close_button:
                                break
                        except:
                            continue

                    if close_button:
                        try:
                            print("🖱️ Clicking Close button to dismiss popup...")
                            close_button.click()
                            print("✅ Clicked Close button")
                            time.sleep(2)  # Wait for popup to close
                            print(
                                "✅ Returned to search results after dismissing popup"
                            )
                            return (
                                {}
                            )  # Return empty dict since no details were available
                        except Exception as e:
                            print(f"⚠️ Error clicking Close button: {e}")
                            # Try JavaScript click as fallback
                            try:
                                self.driver.execute_script(
                                    "arguments[0].click();", close_button
                                )
                                print("✅ Clicked Close button using JavaScript")
                                time.sleep(2)
                                return (
                                    {}
                                )  # Return empty dict since no details were available
                            except Exception as e2:
                                print(f"⚠️ JavaScript click also failed: {e2}")
                                return (
                                    {}
                                )  # Return empty dict since no details were available
                    else:
                        print("⚠️ Could not find Close button in popup")
                        return {}  # Return empty dict since no details were available

            except Exception as e:
                print(f"⚠️ Error checking for details not available popup: {e}")

            # Extract detailed case information (only if we didn't get the "not available" popup)
            case_details = {}

            try:
                print("🔍 Extracting case details from modal/popup...")

                # Wait for the modal content to be visible
                time.sleep(1)

                # Look for the specific table structure with case details
                # The modal content is in a table with specific IDs

                # Extract Case Status
                try:
                    case_status_element = self.driver.find_element(By.ID, "lblCseSts")
                    if case_status_element:
                        case_details["CASE_STATUS"] = case_status_element.text.strip()
                        print(
                            f"✅ Extracted CASE_STATUS: {case_details['CASE_STATUS']}"
                        )
                except Exception as e:
                    print(f"⚠️ Error extracting CASE_STATUS: {e}")

                # Extract Hearing Date
                try:
                    hearing_date_element = self.driver.find_element(By.ID, "lblHdate")
                    if hearing_date_element:
                        case_details["HEARING_DATE_DETAILED"] = (
                            hearing_date_element.text.strip()
                        )
                        print(
                            f"✅ Extracted HEARING_DATE_DETAILED: {case_details['HEARING_DATE_DETAILED']}"
                        )
                except Exception as e:
                    print(f"⚠️ Error extracting HEARING_DATE_DETAILED: {e}")

                # Extract Case Stage
                try:
                    case_stage_element = self.driver.find_element(By.ID, "lblCseStge")
                    if case_stage_element:
                        case_details["CASE_STAGE"] = case_stage_element.text.strip()
                        print(f"✅ Extracted CASE_STAGE: {case_details['CASE_STAGE']}")
                except Exception as e:
                    print(f"⚠️ Error extracting CASE_STAGE: {e}")

                # Extract Tentative Date
                try:
                    tentative_date_element = self.driver.find_element(By.ID, "lblTdate")
                    if tentative_date_element:
                        case_details["TENTATIVE_DATE"] = (
                            tentative_date_element.text.strip()
                        )
                        print(
                            f"✅ Extracted TENTATIVE_DATE: {case_details['TENTATIVE_DATE']}"
                        )
                except Exception as e:
                    print(f"⚠️ Error extracting TENTATIVE_DATE: {e}")

                # Extract Short Order
                try:
                    short_order_element = self.driver.find_element(By.ID, "lblLstOrdr")
                    if short_order_element:
                        case_details["SHORT_ORDER"] = short_order_element.text.strip()
                        print(
                            f"✅ Extracted SHORT_ORDER: {case_details['SHORT_ORDER']}"
                        )
                except Exception as e:
                    print(f"⚠️ Error extracting SHORT_ORDER: {e}")

                # Extract Before Bench
                try:
                    before_bench_element = self.driver.find_element(By.ID, "lblBnch")
                    if before_bench_element:
                        case_details["BEFORE_BENCH"] = before_bench_element.text.strip()
                        print(
                            f"✅ Extracted BEFORE_BENCH: {case_details['BEFORE_BENCH']}"
                        )
                except Exception as e:
                    print(f"⚠️ Error extracting BEFORE_BENCH: {e}")

                # Extract Case Title
                try:
                    case_title_element = self.driver.find_element(By.ID, "lblPrtse")
                    if case_title_element:
                        case_details["CASE_TITLE_DETAILED"] = (
                            case_title_element.text.strip()
                        )
                        print(
                            f"✅ Extracted CASE_TITLE_DETAILED: {case_details['CASE_TITLE_DETAILED']}"
                        )
                except Exception as e:
                    print(f"⚠️ Error extracting CASE_TITLE_DETAILED: {e}")

                # Extract Advocates (Petitioner)
                try:
                    petitioner_element = self.driver.find_element(By.ID, "lblAdv1")
                    if petitioner_element:
                        case_details["ADVOCATES_PETITIONER"] = (
                            petitioner_element.text.strip()
                        )
                        print(
                            f"✅ Extracted ADVOCATES_PETITIONER: {case_details['ADVOCATES_PETITIONER']}"
                        )
                except Exception as e:
                    print(f"⚠️ Error extracting ADVOCATES_PETITIONER: {e}")

                # Extract Advocates (Respondent)
                try:
                    respondent_element = self.driver.find_element(By.ID, "lblAdv2")
                    if respondent_element:
                        case_details["ADVOCATES_RESPONDENT"] = (
                            respondent_element.text.strip()
                        )
                        print(
                            f"✅ Extracted ADVOCATES_RESPONDENT: {case_details['ADVOCATES_RESPONDENT']}"
                        )
                except Exception as e:
                    print(f"⚠️ Error extracting ADVOCATES_RESPONDENT: {e}")

                # Extract Case Description
                try:
                    description_element = self.driver.find_element(By.ID, "lblCseDesc")
                    if description_element:
                        case_details["CASE_DESCRIPTION"] = (
                            description_element.text.strip()
                        )
                        print(
                            f"✅ Extracted CASE_DESCRIPTION: {case_details['CASE_DESCRIPTION']}"
                        )
                except Exception as e:
                    print(f"⚠️ Error extracting CASE_DESCRIPTION: {e}")

                # Extract Disposed Of Status
                try:
                    disposal_status_element = self.driver.find_element(
                        By.ID, "lblDstatus"
                    )
                    if disposal_status_element:
                        case_details["DISPOSED_OF_STATUS"] = (
                            disposal_status_element.text.strip()
                        )
                        print(
                            f"✅ Extracted DISPOSED_OF_STATUS: {case_details['DISPOSED_OF_STATUS']}"
                        )
                except Exception as e:
                    print(f"⚠️ Error extracting DISPOSED_OF_STATUS: {e}")

                # Extract Case Disposal Date
                try:
                    disposal_date_element = self.driver.find_element(By.ID, "lblDdate")
                    if disposal_date_element:
                        case_details["CASE_DISPOSAL_DATE"] = (
                            disposal_date_element.text.strip()
                        )
                        print(
                            f"✅ Extracted CASE_DISPOSAL_DATE: {case_details['CASE_DISPOSAL_DATE']}"
                        )
                except Exception as e:
                    print(f"⚠️ Error extracting CASE_DISPOSAL_DATE: {e}")

                # Extract Disposal Bench
                try:
                    disposal_bench_element = self.driver.find_element(By.ID, "lblDBnch")
                    if disposal_bench_element:
                        case_details["DISPOSAL_BENCH"] = (
                            disposal_bench_element.text.strip()
                        )
                        print(
                            f"✅ Extracted DISPOSAL_BENCH: {case_details['DISPOSAL_BENCH']}"
                        )
                except Exception as e:
                    print(f"⚠️ Error extracting DISPOSAL_BENCH: {e}")

                # Extract Consigned Date
                try:
                    consigned_date_element = self.driver.find_element(
                        By.ID, "lblCnsgnDt"
                    )
                    if consigned_date_element:
                        case_details["CONSIGNED_DATE"] = (
                            consigned_date_element.text.strip()
                        )
                        print(
                            f"✅ Extracted CONSIGNED_DATE: {case_details['CONSIGNED_DATE']}"
                        )
                except Exception as e:
                    print(f"⚠️ Error extracting CONSIGNED_DATE: {e}")

                # Extract FIR Number
                try:
                    fir_number_element = self.driver.find_element(By.ID, "lblFir")
                    if fir_number_element:
                        case_details["FIR_NUMBER"] = fir_number_element.text.strip()
                        print(f"✅ Extracted FIR_NUMBER: {case_details['FIR_NUMBER']}")
                except Exception as e:
                    print(f"⚠️ Error extracting FIR_NUMBER: {e}")

                # Extract FIR Date
                try:
                    fir_date_element = self.driver.find_element(By.ID, "lblFirDate")
                    if fir_date_element:
                        case_details["FIR_DATE"] = fir_date_element.text.strip()
                        print(f"✅ Extracted FIR_DATE: {case_details['FIR_DATE']}")
                except Exception as e:
                    print(f"⚠️ Error extracting FIR_DATE: {e}")

                # Extract Police Station
                try:
                    police_station_element = self.driver.find_element(By.ID, "lblPstn")
                    if police_station_element:
                        case_details["POLICE_STATION"] = (
                            police_station_element.text.strip()
                        )
                        print(
                            f"✅ Extracted POLICE_STATION: {case_details['POLICE_STATION']}"
                        )
                except Exception as e:
                    print(f"⚠️ Error extracting POLICE_STATION: {e}")

                # Extract Under Section
                try:
                    under_section_element = self.driver.find_element(By.ID, "lblUs")
                    if under_section_element:
                        case_details["UNDER_SECTION"] = (
                            under_section_element.text.strip()
                        )
                        print(
                            f"✅ Extracted UNDER_SECTION: {case_details['UNDER_SECTION']}"
                        )
                except Exception as e:
                    print(f"⚠️ Error extracting UNDER_SECTION: {e}")

                # Extract Incident
                try:
                    incident_element = self.driver.find_element(By.ID, "lblIncdnt")
                    if incident_element:
                        case_details["INCIDENT"] = incident_element.text.strip()
                        print(f"✅ Extracted INCIDENT: {case_details['INCIDENT']}")
                except Exception as e:
                    print(f"⚠️ Error extracting INCIDENT: {e}")

                # Extract Name Of Accused
                try:
                    accused_element = self.driver.find_element(By.ID, "lblAcsd")
                    if accused_element:
                        case_details["NAME_OF_ACCUSED"] = accused_element.text.strip()
                        print(
                            f"✅ Extracted NAME_OF_ACCUSED: {case_details['NAME_OF_ACCUSED']}"
                        )
                except Exception as e:
                    print(f"⚠️ Error extracting NAME_OF_ACCUSED: {e}")

                print(f"✅ Successfully extracted {len(case_details)} detailed fields")
                print(f"📋 Extracted fields: {list(case_details.keys())}")

                # Now fetch data from the 4 additional options (Parties, Comments, Case CMs, Hearing Details)
                additional_details = self.fetch_case_detail_options()
                if additional_details:
                    case_details.update(additional_details)
                    print(
                        f"✅ Added data from case detail options: {list(additional_details.keys())}"
                    )
                    print(f"📊 Total case details fields: {len(case_details)}")
                else:
                    print("⚠️ No additional details extracted from case detail options")

                # If we didn't extract any fields, try alternative methods
                if len(case_details) == 0:
                    print("⚠️ No fields extracted, trying alternative methods...")

                    # Method 2: Try to find specific elements by their text content
                    try:
                        # Look for any element containing case details
                        detail_elements = self.driver.find_elements(
                            By.XPATH,
                            "//*[contains(text(), 'Case Status') or contains(text(), 'Short Order') or contains(text(), 'Advocates')]",
                        )
                        if detail_elements:
                            print(f"✅ Found {len(detail_elements)} detail elements")
                            # Extract text from all found elements
                            all_text = ""
                            for element in detail_elements:
                                all_text += element.text + "\n"

                            # Try to parse the combined text
                            if "Case Status:" in all_text:
                                case_details["CASE_STATUS"] = (
                                    "Found in alternative method"
                                )
                                print("✅ Found case details using alternative method")
                    except Exception as e:
                        print(f"⚠️ Alternative method also failed: {e}")

            except Exception as e:
                print(f"⚠️ Error extracting case details: {e}")

                # Case Status
                try:
                    if "Case Status:" in full_page_text:
                        status_start = full_page_text.find("Case Status:")
                        status_end = full_page_text.find("\n", status_start)
                        if status_end == -1:
                            status_end = len(full_page_text)
                        status_value = (
                            full_page_text[status_start:status_end]
                            .replace("Case Status:", "")
                            .strip()
                        )
                        case_details["CASE_STATUS"] = status_value
                        print(f"✅ Extracted CASE_STATUS: {status_value}")
                except Exception as e:
                    print(f"⚠️ Error extracting CASE_STATUS: {e}")

                # Case Stage
                try:
                    if "Case Stage:" in full_page_text:
                        stage_start = full_page_text.find("Case Stage:")
                        stage_end = full_page_text.find("\n", stage_start)
                        if stage_end == -1:
                            stage_end = len(full_page_text)
                        stage_value = (
                            full_page_text[stage_start:stage_end]
                            .replace("Case Stage:", "")
                            .strip()
                        )
                        case_details["CASE_STAGE"] = stage_value
                        print(f"✅ Extracted CASE_STAGE: {stage_value}")
                except Exception as e:
                    print(f"⚠️ Error extracting CASE_STAGE: {e}")

                # Hearing Date
                try:
                    if "Hearing Date:" in full_page_text:
                        hearing_start = full_page_text.find("Hearing Date:")
                        hearing_end = full_page_text.find("\n", hearing_start)
                        if hearing_end == -1:
                            hearing_end = len(full_page_text)
                        hearing_value = (
                            full_page_text[hearing_start:hearing_end]
                            .replace("Hearing Date:", "")
                            .strip()
                        )
                        case_details["HEARING_DATE_DETAILED"] = hearing_value
                        print(f"✅ Extracted HEARING_DATE_DETAILED: {hearing_value}")
                except Exception as e:
                    print(f"⚠️ Error extracting HEARING_DATE_DETAILED: {e}")

                # Tentative Date
                try:
                    if "Tentative Date:" in full_page_text:
                        tentative_start = full_page_text.find("Tentative Date:")
                        tentative_end = full_page_text.find("\n", tentative_start)
                        if tentative_end == -1:
                            tentative_end = len(full_page_text)
                        tentative_value = (
                            full_page_text[tentative_start:tentative_end]
                            .replace("Tentative Date:", "")
                            .strip()
                        )
                        case_details["TENTATIVE_DATE"] = tentative_value
                        print(f"✅ Extracted TENTATIVE_DATE: {tentative_value}")
                except Exception as e:
                    print(f"⚠️ Error extracting TENTATIVE_DATE: {e}")

                # Short Order
                try:
                    if "Short Order:" in full_page_text:
                        short_order_start = full_page_text.find("Short Order:")
                        short_order_end = full_page_text.find("\n", short_order_start)
                        if short_order_end == -1:
                            short_order_end = len(full_page_text)
                        short_order_value = (
                            full_page_text[short_order_start:short_order_end]
                            .replace("Short Order:", "")
                            .strip()
                        )
                        case_details["SHORT_ORDER"] = short_order_value
                        print(f"✅ Extracted SHORT_ORDER: {short_order_value}")
                except Exception as e:
                    print(f"⚠️ Error extracting SHORT_ORDER: {e}")

                # Before Bench
                try:
                    if "Before Bench:" in full_page_text:
                        bench_start = full_page_text.find("Before Bench:")
                        bench_end = full_page_text.find("\n", bench_start)
                        if bench_end == -1:
                            bench_end = len(full_page_text)
                        bench_value = (
                            full_page_text[bench_start:bench_end]
                            .replace("Before Bench:", "")
                            .strip()
                        )
                        case_details["BEFORE_BENCH"] = bench_value
                        print(f"✅ Extracted BEFORE_BENCH: {bench_value}")
                except Exception as e:
                    print(f"⚠️ Error extracting BEFORE_BENCH: {e}")

                # Case Title (Detailed)
                try:
                    if "Case Title:" in full_page_text:
                        title_start = full_page_text.find("Case Title:")
                        title_end = full_page_text.find("\n", title_start)
                        if title_end == -1:
                            title_end = len(full_page_text)
                        title_value = (
                            full_page_text[title_start:title_end]
                            .replace("Case Title:", "")
                            .strip()
                        )
                        case_details["CASE_TITLE_DETAILED"] = title_value
                        print(f"✅ Extracted CASE_TITLE_DETAILED: {title_value}")
                except Exception as e:
                    print(f"⚠️ Error extracting CASE_TITLE_DETAILED: {e}")

                # Advocates (Petitioner)
                try:
                    if "Advocates (Petitioner):" in full_page_text:
                        petitioner_start = full_page_text.find(
                            "Advocates (Petitioner):"
                        )
                        petitioner_end = full_page_text.find(
                            "Advocates (Respondent):", petitioner_start
                        )
                        if petitioner_end == -1:
                            petitioner_end = full_page_text.find("\n", petitioner_start)
                        petitioner_value = (
                            full_page_text[petitioner_start:petitioner_end]
                            .replace("Advocates (Petitioner):", "")
                            .strip()
                        )
                        case_details["ADVOCATES_PETITIONER"] = petitioner_value
                        print(f"✅ Extracted ADVOCATES_PETITIONER: {petitioner_value}")
                except Exception as e:
                    print(f"⚠️ Error extracting ADVOCATES_PETITIONER: {e}")

                # Advocates (Respondent)
                try:
                    if "Advocates (Respondent):" in full_page_text:
                        respondent_start = full_page_text.find(
                            "Advocates (Respondent):"
                        )
                        respondent_end = full_page_text.find(
                            "Case Description:", respondent_start
                        )
                        if respondent_end == -1:
                            respondent_end = full_page_text.find("\n", respondent_start)
                        respondent_value = (
                            full_page_text[respondent_start:respondent_end]
                            .replace("Advocates (Respondent):", "")
                            .strip()
                        )
                        case_details["ADVOCATES_RESPONDENT"] = respondent_value
                        print(f"✅ Extracted ADVOCATES_RESPONDENT: {respondent_value}")
                except Exception as e:
                    print(f"⚠️ Error extracting ADVOCATES_RESPONDENT: {e}")

                # Case Description
                try:
                    if "Case Description:" in full_page_text:
                        desc_start = full_page_text.find("Case Description:")
                        desc_end = full_page_text.find(
                            "Disposal Information:", desc_start
                        )
                        if desc_end == -1:
                            desc_end = full_page_text.find("\n", desc_start)
                        desc_value = (
                            full_page_text[desc_start:desc_end]
                            .replace("Case Description:", "")
                            .strip()
                        )
                        case_details["CASE_DESCRIPTION"] = desc_value
                        print(f"✅ Extracted CASE_DESCRIPTION: {desc_value}")
                except Exception as e:
                    print(f"⚠️ Error extracting CASE_DESCRIPTION: {e}")

                # Disposed Of Status
                try:
                    if "Disposed Of Status:" in full_page_text:
                        disposal_start = full_page_text.find("Disposed Of Status:")
                        disposal_end = full_page_text.find("\n", disposal_start)
                        if disposal_end == -1:
                            disposal_end = len(full_page_text)
                        disposal_value = (
                            full_page_text[disposal_start:disposal_end]
                            .replace("Disposed Of Status:", "")
                            .strip()
                        )
                        case_details["DISPOSED_OF_STATUS"] = disposal_value
                        print(f"✅ Extracted DISPOSED_OF_STATUS: {disposal_value}")
                except Exception as e:
                    print(f"⚠️ Error extracting DISPOSED_OF_STATUS: {e}")

                # Disposal Bench
                try:
                    if "Disposal Bench:" in full_page_text:
                        disposal_bench_start = full_page_text.find("Disposal Bench:")
                        disposal_bench_end = full_page_text.find(
                            "\n", disposal_bench_start
                        )
                        if disposal_bench_end == -1:
                            disposal_bench_end = len(full_page_text)
                        disposal_bench_value = (
                            full_page_text[disposal_bench_start:disposal_bench_end]
                            .replace("Disposal Bench:", "")
                            .strip()
                        )
                        case_details["DISPOSAL_BENCH"] = disposal_bench_value
                        print(f"✅ Extracted DISPOSAL_BENCH: {disposal_bench_value}")
                except Exception as e:
                    print(f"⚠️ Error extracting DISPOSAL_BENCH: {e}")

                # Case Disposal Date
                try:
                    if "Case Disposal Date:" in full_page_text:
                        disposal_date_start = full_page_text.find("Case Disposal Date:")
                        disposal_date_end = full_page_text.find(
                            "\n", disposal_date_start
                        )
                        if disposal_date_end == -1:
                            disposal_date_end = len(full_page_text)
                        disposal_date_value = (
                            full_page_text[disposal_date_start:disposal_date_end]
                            .replace("Case Disposal Date:", "")
                            .strip()
                        )
                        case_details["CASE_DISPOSAL_DATE"] = disposal_date_value
                        print(f"✅ Extracted CASE_DISPOSAL_DATE: {disposal_date_value}")
                except Exception as e:
                    print(f"⚠️ Error extracting CASE_DISPOSAL_DATE: {e}")

                # Consigned Date
                try:
                    if "Consigned date:" in full_page_text:
                        consigned_start = full_page_text.find("Consigned date:")
                        consigned_end = full_page_text.find("\n", consigned_start)
                        if consigned_end == -1:
                            consigned_end = len(full_page_text)
                        consigned_value = (
                            full_page_text[consigned_start:consigned_end]
                            .replace("Consigned date:", "")
                            .strip()
                        )
                        case_details["CONSIGNED_DATE"] = consigned_value
                        print(f"✅ Extracted CONSIGNED_DATE: {consigned_value}")
                except Exception as e:
                    print(f"⚠️ Error extracting CONSIGNED_DATE: {e}")

                # FIR Information Section
                try:
                    if "FIR Information:" in full_page_text:
                        fir_section_start = full_page_text.find("FIR Information:")
                        fir_section_end = full_page_text.find(
                            "Generated By:", fir_section_start
                        )
                        if fir_section_end == -1:
                            fir_section_end = len(full_page_text)
                        fir_section = full_page_text[fir_section_start:fir_section_end]

                        # Extract FIR #
                        if "FIR #:" in fir_section:
                            fir_start = fir_section.find("FIR #:")
                            fir_end = fir_section.find("\n", fir_start)
                            if fir_end == -1:
                                fir_end = len(fir_section)
                            fir_value = (
                                fir_section[fir_start:fir_end]
                                .replace("FIR #:", "")
                                .strip()
                            )
                            case_details["FIR_NUMBER"] = fir_value
                            print(f"✅ Extracted FIR_NUMBER: {fir_value}")

                        # Extract FIR Date
                        if "FIR Date:" in fir_section:
                            fir_date_start = fir_section.find("FIR Date:")
                            fir_date_end = fir_section.find("\n", fir_date_start)
                            if fir_date_end == -1:
                                fir_date_end = len(fir_section)
                            fir_date_value = (
                                fir_section[fir_date_start:fir_date_end]
                                .replace("FIR Date:", "")
                                .strip()
                            )
                            case_details["FIR_DATE"] = fir_date_value
                            print(f"✅ Extracted FIR_DATE: {fir_date_value}")

                        # Extract Police Station
                        if "Police Station:" in fir_section:
                            police_start = fir_section.find("Police Station:")
                            police_end = fir_section.find("\n", police_start)
                            if police_end == -1:
                                police_end = len(fir_section)
                            police_value = (
                                fir_section[police_start:police_end]
                                .replace("Police Station:", "")
                                .strip()
                            )
                            case_details["POLICE_STATION"] = police_value
                            print(f"✅ Extracted POLICE_STATION: {police_value}")

                        # Extract Under Section
                        if "Under Section:" in fir_section:
                            section_start = fir_section.find("Under Section:")
                            section_end = fir_section.find("\n", section_start)
                            if section_end == -1:
                                section_end = len(fir_section)
                            section_value = (
                                fir_section[section_start:section_end]
                                .replace("Under Section:", "")
                                .strip()
                            )
                            case_details["UNDER_SECTION"] = section_value
                            print(f"✅ Extracted UNDER_SECTION: {section_value}")

                        # Extract Incident
                        if "Incident:" in fir_section:
                            incident_start = fir_section.find("Incident:")
                            incident_end = fir_section.find("\n", incident_start)
                            if incident_end == -1:
                                incident_end = len(fir_section)
                            incident_value = (
                                fir_section[incident_start:incident_end]
                                .replace("Incident:", "")
                                .strip()
                            )
                            case_details["INCIDENT"] = incident_value
                            print(f"✅ Extracted INCIDENT: {incident_value}")

                        # Extract Name Of Accused
                        if "Name Of Accused:" in fir_section:
                            accused_start = fir_section.find("Name Of Accused:")
                            accused_end = fir_section.find("\n", accused_start)
                            if accused_end == -1:
                                accused_end = len(fir_section)
                            accused_value = (
                                fir_section[accused_start:accused_end]
                                .replace("Name Of Accused:", "")
                                .strip()
                            )
                            case_details["NAME_OF_ACCUSED"] = accused_value
                            print(f"✅ Extracted NAME_OF_ACCUSED: {accused_value}")

                except Exception as e:
                    print(f"⚠️ Error extracting FIR information: {e}")

                print(f"✅ Successfully extracted {len(case_details)} detailed fields")
                print(f"📋 Extracted fields: {list(case_details.keys())}")

                # If we didn't extract any fields, try alternative methods
                if len(case_details) == 0:
                    print("⚠️ No fields extracted, trying alternative methods...")

                    # Method 2: Try to find specific elements by their text content
                    try:
                        # Look for any element containing case details
                        detail_elements = self.driver.find_elements(
                            By.XPATH,
                            "//*[contains(text(), 'Case Status') or contains(text(), 'Short Order') or contains(text(), 'Advocates')]",
                        )
                        if detail_elements:
                            print(f"✅ Found {len(detail_elements)} detail elements")
                            # Extract text from all found elements
                            all_text = ""
                            for element in detail_elements:
                                all_text += element.text + "\n"

                            # Try to parse the combined text
                            if "Case Status:" in all_text:
                                case_details["CASE_STATUS"] = (
                                    "Found in alternative method"
                                )
                                print("✅ Found case details using alternative method")
                    except Exception as e:
                        print(f"⚠️ Alternative method also failed: {e}")

            except Exception as e:
                print(f"⚠️ Error extracting case details: {e}")

            # Close the modal/popup and return to search results
            print(
                "🔍 Looking for 'Close / Back' button (red X with tooltip) to return to search results..."
            )

            try:
                # Try to find the red X close button with "Close / Back" tooltip
                close_button_selectors = [
                    "//img[@id='btnclsIco']",  # Exact ID from HTML inspection
                    "//img[@src='img/close.ico']",  # Exact src from HTML inspection
                    "//img[@data-original-title='Close / Bac k']",  # Exact data-original-title
                    "//img[contains(@data-original-title, 'Close')]",  # Partial match
                    "//img[contains(@data-original-title, 'Back')]",  # Partial match
                    "//*[@id='btnclsIco']",  # Any element with this ID
                    "//*[@src='img/close.ico']",  # Any element with this src
                    "//img[contains(@src, 'close.ico')]",  # Partial src match
                    "//*[contains(@data-original-title, 'Close')]",  # Any element with Close in tooltip
                    "//*[contains(@data-original-title, 'Back')]",  # Any element with Back in tooltip
                    "//img[@title*='Close']",  # Title attribute containing Close
                    "//img[@title*='Back']",  # Title attribute containing Back
                    "//*[@title*='Close']",  # Any element with Close in title
                    "//*[@title*='Back']",  # Any element with Back in title
                ]

                close_button = None
                for selector in close_button_selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        for element in elements:
                            if element.is_displayed():
                                close_button = element
                                print(
                                    f"✅ Found close button with selector: {selector}"
                                )
                                break
                        if close_button:
                            break
                    except:
                        continue

                # If no close button found by selectors, try to find by looking for red X button
                if not close_button:
                    try:
                        # Look for red X button by various methods
                        red_x_selectors = [
                            "//img[contains(@src, 'close')]",  # Any close image
                            "//img[contains(@src, 'ico')]",  # Any ico image
                            "//*[contains(@style, 'red')]",  # Red styling
                            "//*[contains(@style, '#ff0000')]",  # Red color
                            "//*[contains(@style, '#f00')]",  # Short red color
                        ]

                        for selector in red_x_selectors:
                            elements = self.driver.find_elements(By.XPATH, selector)
                            for element in elements:
                                if element.is_displayed() and element.is_enabled():
                                    # Check if it's likely the close button
                                    element_src = element.get_attribute("src") or ""
                                    element_id = element.get_attribute("id") or ""
                                    element_title = element.get_attribute("title") or ""
                                    element_data_title = (
                                        element.get_attribute("data-original-title")
                                        or ""
                                    )

                                    if (
                                        "close" in element_src.lower()
                                        or "close" in element_id.lower()
                                        or "close" in element_title.lower()
                                        or "close" in element_data_title.lower()
                                    ):
                                        close_button = element
                                        print(
                                            f"✅ Found red X close button by fallback: {selector}"
                                        )
                                        break
                            if close_button:
                                break
                    except:
                        pass

                # If still no close button, try to find by position (top-right corner)
                if not close_button:
                    try:
                        # Look for buttons or clickable elements in the top-right area
                        all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                        all_links = self.driver.find_elements(By.TAG_NAME, "a")
                        all_spans = self.driver.find_elements(By.TAG_NAME, "span")
                        all_divs = self.driver.find_elements(By.TAG_NAME, "div")

                        potential_close_elements = (
                            all_buttons + all_links + all_spans + all_divs
                        )

                        for element in potential_close_elements:
                            try:
                                if element.is_displayed() and element.is_enabled():
                                    # Check if it's in the top-right area (you might need to adjust this logic)
                                    location = element.location
                                    size = element.size
                                    if location and size:
                                        # Simple check: if it's in the upper half of the page
                                        if location["y"] < 100:  # Top 100 pixels
                                            close_button = element
                                            print(
                                                "✅ Found potential close button in top area"
                                            )
                                            break
                            except:
                                continue
                    except:
                        pass

                # Click the close button if found
                if close_button:
                    try:
                        print("🖱️ Clicking close button...")
                        close_button.click()
                        print("✅ Clicked close button")
                        time.sleep(2)  # Wait for modal to close

                        # Verify we're back to the search results
                        current_url_after_close = self.driver.current_url
                        if current_url_after_close == original_url:
                            print("✅ Successfully returned to search results page")
                        else:
                            print(f"ℹ️ URL after close: {current_url_after_close}")

                    except Exception as e:
                        print(f"⚠️ Error clicking close button: {e}")
                        # Try JavaScript click as fallback
                        try:
                            self.driver.execute_script(
                                "arguments[0].click();", close_button
                            )
                            print("✅ Clicked close button using JavaScript")
                            time.sleep(2)
                        except Exception as e2:
                            print(f"⚠️ JavaScript click also failed: {e2}")
                else:
                    print("⚠️ Could not find close button")
                    # Try pressing Escape key as fallback
                    try:
                        from selenium.webdriver.common.keys import Keys

                        self.driver.find_element(By.TAG_NAME, "body").send_keys(
                            Keys.ESCAPE
                        )
                        print("✅ Pressed Escape key to close modal")
                        time.sleep(2)
                    except Exception as e:
                        print(f"⚠️ Escape key also failed: {e}")

            except Exception as e:
                print(f"⚠️ Error in modal closing process: {e}")

            # Close the detail window and switch back (for new window case)
            if new_window:
                self.driver.close()
                self.driver.switch_to.window(original_window)
                print("✅ Closed detail window and switched back")

            return case_details

        except Exception as e:
            print(f"❌ Error fetching case details: {e}")
            # Try to switch back to original window if possible
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass
            return {}

    def fetch_case_history(self, case_row_element, case_data):
        """
        Fetch case history data by clicking the four buttons in the HISTORY column:
        Orders, Comments, Case CMs, and Judgement

        Args:
            case_row_element: The table row element containing the case
            case_data: The current case data dictionary

        Returns:
            dict: History data or empty dict if failed
        """
        try:
            # Check if this case has 'Decided' status
            cells = case_row_element.find_elements(By.TAG_NAME, "td")
            if len(cells) < 8:
                return {}

            status = cells[6].text.strip()
            if status != "Decided":
                return {}  # Only fetch history for decided cases

            print(
                f"📋 Fetching history data for decided case: {case_data.get('CASE_NO', 'N/A')}"
            )

            # Find the HISTORY column (8th column, index 7)
            history_cell = cells[7] if len(cells) > 7 else None
            if not history_cell:
                print("⚠️ No history column found")
                return {}

            # Look for the four buttons: Orders, Comments, Case CMs, Judgement
            history_buttons = history_cell.find_elements(By.TAG_NAME, "button")
            history_links = history_cell.find_elements(By.TAG_NAME, "a")
            history_spans = history_cell.find_elements(By.TAG_NAME, "span")

            # Combine all potential clickable elements
            all_elements = history_buttons + history_links + history_spans

            if not all_elements:
                print("⚠️ No history buttons found")
                return {}

            print(f"🔍 Found {len(all_elements)} potential history elements")

            # Store current URL and window handle
            original_url = self.driver.current_url
            original_window = self.driver.current_window_handle

            history_data = {}

            # Define the four history types we want to fetch
            history_types = ["Orders", "Comments", "Case CMs", "Judgement"]

            for history_type in history_types:
                print(f"🔍 Looking for '{history_type}' button...")

                # Find the button for this history type
                target_element = None
                for element in all_elements:
                    try:
                        element_text = element.text.strip()
                        if history_type.lower() in element_text.lower():
                            target_element = element
                            print(f"✅ Found '{history_type}' button")
                            break
                    except:
                        continue

                if not target_element:
                    print(f"⚠️ Could not find '{history_type}' button")
                    continue

                # Click the history button
                try:
                    print(f"🖱️ Clicking '{history_type}' button...")
                    target_element.click()
                    time.sleep(3)  # Wait for modal/popup to load

                    # Special handling for Judgement (opens PDF in new tab)
                    if history_type == "Judgement":
                        # Check if we have a new window/tab for PDF
                        new_window = None
                        for window_handle in self.driver.window_handles:
                            if window_handle != original_window:
                                new_window = window_handle
                                break

                        if new_window:
                            self.driver.switch_to.window(new_window)
                            print(f"✅ Switched to new window for '{history_type}' PDF")

                            # Extract PDF data
                            history_content = self.extract_history_content(history_type)
                            if history_content and "content" in history_content:
                                history_data[
                                    f"{history_type.upper().replace(' ', '_')}_DATA"
                                ] = history_content["content"]
                                print(f"✅ Extracted '{history_type}' PDF data")
                            else:
                                print(f"⚠️ No data extracted for '{history_type}' PDF")

                            # Close the PDF window and return to main page
                            self.driver.close()
                            self.driver.switch_to.window(original_window)
                            print(
                                f"✅ Closed '{history_type}' PDF window and switched back"
                            )
                        else:
                            print(f"⚠️ No new window opened for '{history_type}' PDF")
                    else:
                        # For Orders, Comments, Case CMs - these open modals
                        # Check if we have a new window/tab (unlikely for modals)
                        new_window = None
                        for window_handle in self.driver.window_handles:
                            if window_handle != original_window:
                                new_window = window_handle
                                break

                        if new_window:
                            self.driver.switch_to.window(new_window)
                            print(f"✅ Switched to new window for '{history_type}'")
                        else:
                            print(
                                f"ℹ️ No new window opened for '{history_type}', using modal"
                            )

                        # Extract data from the history modal
                        history_content = self.extract_history_content(history_type)
                        if history_content and "content" in history_content:
                            history_data[
                                f"{history_type.upper().replace(' ', '_')}_DATA"
                            ] = history_content["content"]
                            print(f"✅ Extracted '{history_type}' data")
                        else:
                            print(f"⚠️ No data extracted for '{history_type}'")

                        # Close the history window/modal and return to main page
                        if new_window:
                            self.driver.close()
                            self.driver.switch_to.window(original_window)
                            print(
                                f"✅ Closed '{history_type}' window and switched back"
                            )
                        else:
                            # Close modal if it's a popup - IMPORTANT: Must close before next button
                            print(
                                f"🔍 Closing '{history_type}' modal before proceeding..."
                            )
                            if self.close_history_modal():
                                print(f"✅ Successfully closed '{history_type}' modal")
                            else:
                                print(
                                    f"⚠️ Failed to close '{history_type}' modal, trying alternative methods..."
                                )
                                # Try alternative closing methods
                                try:
                                    # Try Escape key
                                    from selenium.webdriver.common.keys import Keys

                                    self.driver.find_element(
                                        By.TAG_NAME, "body"
                                    ).send_keys(Keys.ESCAPE)
                                    print(
                                        f"✅ Used Escape key to close '{history_type}' modal"
                                    )
                                    time.sleep(1)
                                except:
                                    print(
                                        f"⚠️ Escape key also failed for '{history_type}' modal"
                                    )

                            # Wait a moment to ensure modal is fully closed
                            time.sleep(2)

                            # CRITICAL: Verify modal is actually closed before proceeding
                            modal_still_open = False
                            try:
                                modals = self.driver.find_elements(
                                    By.XPATH, "//div[contains(@class, 'modal')]"
                                )
                                for modal in modals:
                                    if modal.is_displayed():
                                        modal_still_open = True
                                        print(
                                            f"⚠️ Modal still open after closing '{history_type}' - attempting additional close..."
                                        )
                                        break
                            except:
                                pass

                            # If modal is still open, try additional closing methods
                            if modal_still_open:
                                print(
                                    f"🔄 Modal still open for '{history_type}', trying additional close methods..."
                                )

                                # Try clicking outside the modal
                                try:
                                    self.driver.find_element(
                                        By.TAG_NAME, "body"
                                    ).click()
                                    print("✅ Clicked outside modal")
                                    time.sleep(1)
                                except:
                                    pass

                                # Try Escape key again
                                try:
                                    from selenium.webdriver.common.keys import Keys

                                    self.driver.find_element(
                                        By.TAG_NAME, "body"
                                    ).send_keys(Keys.ESCAPE)
                                    print("✅ Pressed Escape key again")
                                    time.sleep(2)
                                except:
                                    pass

                                # Final verification
                                try:
                                    modals = self.driver.find_elements(
                                        By.XPATH, "//div[contains(@class, 'modal')]"
                                    )
                                    modal_still_open = False
                                    for modal in modals:
                                        if modal.is_displayed():
                                            modal_still_open = True
                                            break

                                    if not modal_still_open:
                                        print(
                                            f"✅ Modal finally closed for '{history_type}'"
                                        )
                                    else:
                                        print(
                                            f"❌ Modal still open for '{history_type}' - may cause issues with next button"
                                        )
                                except:
                                    pass
                            else:
                                print(
                                    f"✅ Modal successfully closed for '{history_type}'"
                                )

                            # Verify we're back to the main search results page
                            try:
                                current_url = self.driver.current_url
                                if "frmCseSrch" in current_url:
                                    print(
                                        f"✅ Verified back to main search page after closing '{history_type}' modal"
                                    )
                                else:
                                    print(
                                        f"⚠️ URL after closing '{history_type}' modal: {current_url}"
                                    )
                            except:
                                print(
                                    f"⚠️ Could not verify URL after closing '{history_type}' modal"
                                )

                except Exception as e:
                    print(f"⚠️ Error processing '{history_type}': {e}")
                    # Try to switch back to original window if possible
                    try:
                        if len(self.driver.window_handles) > 1:
                            self.driver.switch_to.window(original_window)
                    except:
                        pass
                    continue

            print(
                f"✅ Successfully extracted history data for {len(history_data)} types"
            )
            return history_data

        except Exception as e:
            print(f"❌ Error fetching case history: {e}")
            return {}

    def extract_history_content(self, history_type):
        """
        Extract content from a history page/modal based on the specific modal type

        Args:
            history_type: Type of history (Orders, Comments, Case CMs, Judgement)

        Returns:
            dict: Extracted history content
        """
        try:
            history_content = {"content": {}}

            # Wait for content to load
            time.sleep(2)

            # Handle different modal types based on the HTML structures provided
            if history_type == "Orders":
                # Orders opens "Case History" modal with table id="tblCseHstry"
                return self._extract_orders_data(history_content)
            elif history_type == "Comments":
                # Comments opens "Doc History" modal with table id="tblCmntsHstry"
                return self._extract_comments_data(history_content)
            elif history_type == "Case CMs":
                # Case CMs opens "CMs of Case" modal with table id="tblCmsHstry"
                return self._extract_case_cms_data(history_content)
            elif history_type == "Judgement":
                # Judgement opens PDF in new tab
                return self._extract_judgement_data(history_content)
            else:
                print(f"⚠️ Unknown history type: {history_type}")
                return None

        except Exception as e:
            print(f"❌ Error extracting history content: {e}")
            return None

    def _extract_orders_data(self, history_content):
        """Extract data from Orders modal (Case History)"""
        try:
            # Look for the specific table with id="tblCseHstry"
            table = self.driver.find_element(By.ID, "tblCseHstry")
            if table:
                # Extract headers
                headers = []
                header_elements = table.find_elements(By.TAG_NAME, "th")
                for header in header_elements:
                    headers.append(header.text.strip())

                if headers:
                    history_content["content"]["headers"] = headers
                    print(f"✅ Orders: Found {len(headers)} headers: {headers}")

                # Comprehensive row extraction - try multiple approaches
                rows = []

                # Method 1: Get ALL tr elements in the table (including nested ones)
                all_tr_elements = table.find_elements(By.XPATH, ".//tr")
                print(
                    f"🔍 Orders: Found {len(all_tr_elements)} total tr elements in table"
                )

                # Skip the first tr if it's a header
                data_tr_elements = all_tr_elements[1:] if all_tr_elements else []

                for tr_index, tr in enumerate(data_tr_elements):
                    if len(rows) >= self.max_history_rows:
                        print(
                            f"⏹️ Orders: Reached max history rows ({self.max_history_rows}) during primary extraction"
                        )
                        break
                    cells = tr.find_elements(By.TAG_NAME, "td")
                    row_data = []

                    for cell_index, cell in enumerate(cells):
                        cell_text = cell.text.strip()

                        # Special handling for VIEW column (last column)
                        if cell_index == len(cells) - 1 and "VIEW" in headers[-1]:
                            # Look for download links in the VIEW column
                            try:
                                # Find download links within this cell
                                download_links = cell.find_elements(By.TAG_NAME, "a")
                                if download_links:
                                    # Extract href attributes from download links
                                    link_data = []
                                    for link in download_links:
                                        href = link.get_attribute("href")
                                        title = link.get_attribute("title") or ""
                                        link_text = link.text.strip()

                                        if href:
                                            link_info = {
                                                "href": href,
                                                "title": title,
                                                "text": link_text,
                                            }
                                            link_data.append(link_info)

                                    if link_data:
                                        row_data.append(link_data)
                                        print(
                                            f"✅ Orders: Found {len(link_data)} download link(s) in TR {tr_index + 1}"
                                        )
                                    else:
                                        row_data.append(cell_text)
                                else:
                                    row_data.append(cell_text)
                            except Exception as link_error:
                                print(
                                    f"⚠️ Error extracting VIEW column links: {link_error}"
                                )
                                row_data.append(cell_text)
                        else:
                            row_data.append(cell_text)

                    print(
                        f"🔍 Orders: TR {tr_index + 1} has {len(cells)} cells: {row_data}"
                    )

                    # Include row if it has any data (not just empty cells)
                    if row_data and any(
                        cell_text
                        for cell_text in row_data
                        if isinstance(cell_text, str)
                    ):
                        # Skip rows that contain "No data available"
                        if not any(
                            "No data available" in str(cell_text)
                            for cell_text in row_data
                        ):
                            # Check if this row is already added
                            if row_data not in rows:
                                rows.append(row_data)
                                print(f"✅ Orders: Added TR {tr_index + 1}: {row_data}")
                        else:
                            print(
                                f"⚠️ Orders: Skipping 'No data available' TR {tr_index + 1}: {row_data}"
                            )
                    else:
                        print(f"⚠️ Orders: Skipping empty TR {tr_index + 1}: {row_data}")

                # Method 2: Also check tbody specifically
                if len(rows) < self.max_history_rows:
                    tbody_elements = table.find_elements(By.TAG_NAME, "tbody")
                    if tbody_elements:
                        print(f"🔍 Orders: Found {len(tbody_elements)} tbody elements")
                        for tbody_index, tbody in enumerate(tbody_elements):
                            if len(rows) >= self.max_history_rows:
                                print(
                                    f"⏹️ Orders: Reached max history rows ({self.max_history_rows}) during tbody scanning"
                                )
                                break

                            tbody_rows = tbody.find_elements(By.TAG_NAME, "tr")
                            print(
                                f"🔍 Orders: Tbody {tbody_index + 1} has {len(tbody_rows)} rows"
                            )

                            for row_index, row in enumerate(tbody_rows):
                                if len(rows) >= self.max_history_rows:
                                    print(
                                        f"⏹️ Orders: Reached max history rows ({self.max_history_rows}) inside tbody loop"
                                    )
                                    break

                                cells = row.find_elements(By.TAG_NAME, "td")
                                row_data = []

                                for cell_index, cell in enumerate(cells):
                                    cell_text = cell.text.strip()

                                    # Special handling for VIEW column (last column)
                                    if (
                                        cell_index == len(cells) - 1
                                        and "VIEW" in headers[-1]
                                    ):
                                        # Look for download links in the VIEW column
                                        try:
                                            # Find download links within this cell
                                            download_links = cell.find_elements(
                                                By.TAG_NAME, "a"
                                            )
                                            if download_links:
                                                # Extract href attributes from download links
                                                link_data = []
                                                for link in download_links:
                                                    href = link.get_attribute("href")
                                                    title = (
                                                        link.get_attribute("title") or ""
                                                    )
                                                    link_text = link.text.strip()

                                                    if href:
                                                        link_info = {
                                                            "href": href,
                                                            "title": title,
                                                            "text": link_text,
                                                        }
                                                        link_data.append(link_info)

                                                if link_data:
                                                    row_data.append(link_data)
                                                    print(
                                                        f"✅ Orders: Found {len(link_data)} download link(s) in tbody {tbody_index + 1}, row {row_index + 1}"
                                                    )
                                                else:
                                                    row_data.append(cell_text)
                                            else:
                                                row_data.append(cell_text)
                                        except Exception as link_error:
                                            print(
                                                f"⚠️ Error extracting VIEW column links: {link_error}"
                                            )
                                            row_data.append(cell_text)
                                    else:
                                        row_data.append(cell_text)

                                print(
                                    f"🔍 Orders: Tbody {tbody_index + 1}, Row {row_index + 1} has {len(cells)} cells: {row_data}"
                                )

                                # Include row if it has any data (not just empty cells)
                                if row_data and any(
                                    cell_text
                                    for cell_text in row_data
                                    if isinstance(cell_text, str)
                                ):
                                    # Skip rows that contain "No data available"
                                    if not any(
                                        "No data available" in str(cell_text)
                                        for cell_text in row_data
                                    ):
                                        # Check if this row is already added
                                        if row_data not in rows:
                                            rows.append(row_data)
                                            print(
                                                f"✅ Orders: Added tbody {tbody_index + 1}, row {row_index + 1}: {row_data}"
                                            )
                                    else:
                                        print(
                                            f"⚠️ Orders: Skipping 'No data available' tbody row: {row_data}"
                                        )
                                else:
                                    print(f"⚠️ Orders: Skipping empty tbody row: {row_data}")

                            if len(rows) >= self.max_history_rows:
                                break

                        # Safety check after completing tbody loop
                        if len(rows) >= self.max_history_rows:
                            print(
                                f"⏹️ Orders: Finished tbody scanning at max history rows ({self.max_history_rows})"
                            )

                if rows:
                    history_content["content"]["rows"] = rows[: self.max_history_rows]
                    print(
                        f"✅ Orders: Found {len(rows)} data rows with VIEW column links"
                    )
                else:
                    print("⚠️ Orders: No data rows found")

                return history_content

        except Exception as e:
            print(f"❌ Error extracting Orders data: {e}")
            return None

    def _extract_comments_data(self, history_content):
        """Extract data from Comments modal (Doc History)"""
        try:
            # Look for the specific table with id="tblCmntsHstry"
            table = self.driver.find_element(By.ID, "tblCmntsHstry")
            if table:
                # Extract headers
                headers = []
                header_elements = table.find_elements(By.TAG_NAME, "th")
                for header in header_elements:
                    headers.append(header.text.strip())

                if headers:
                    history_content["content"]["headers"] = headers
                    print(f"✅ Comments: Found {len(headers)} headers: {headers}")

                # Extract limited rows including first entry
                rows = []
                row_elements = table.find_elements(By.TAG_NAME, "tr")[
                    1:
                ]  # Skip header row
                print(f"🔍 Comments: Found {len(row_elements)} total row elements")

                for row_index, row in enumerate(row_elements):
                    if len(rows) >= self.max_history_rows:
                        print(
                            f"⏹️ Comments: Reached max history rows ({self.max_history_rows})"
                        )
                        break
                    cells = row.find_elements(By.TAG_NAME, "td")
                    row_data = []

                    # Check if this is a "No data available" row
                    if len(cells) == 1:
                        cell_text = cells[0].text.strip()
                        if "No data available" in cell_text:
                            print(
                                f"⚠️ Comments: Row {row_index + 1} contains 'No data available'"
                            )
                            continue

                    for cell in cells:
                        row_data.append(cell.text.strip())

                    # Include ALL rows that have data (don't skip first entry)
                    if row_data and len(row_data) > 0:
                        rows.append(row_data)
                        print(
                            f"✅ Comments: Added row {row_index + 1} with {len(row_data)} cells: {row_data[0] if row_data else 'N/A'}"
                        )
                    else:
                        print(f"⚠️ Comments: Skipped empty row {row_index + 1}")

                if rows:
                    history_content["content"]["rows"] = rows[: self.max_history_rows]
                    print(
                        f"✅ Comments: Found {len(rows)} data rows (including first entry)"
                    )
                else:
                    print("⚠️ Comments: No data rows found")

                return history_content

        except Exception as e:
            print(f"❌ Error extracting Comments data: {e}")
            return None

    def _extract_case_cms_data(self, history_content):
        """Extract data from Case CMs modal (CMs of Case)"""
        try:
            # Look for the specific table with id="tblCmsHstry"
            table = self.driver.find_element(By.ID, "tblCmsHstry")
            if table:
                # Extract headers
                headers = []
                header_elements = table.find_elements(By.TAG_NAME, "th")
                for header in header_elements:
                    headers.append(header.text.strip())

                if headers:
                    history_content["content"]["headers"] = headers
                    print(f"✅ Case CMs: Found {len(headers)} headers: {headers}")

                # Extract limited rows including first entry
                rows = []
                row_elements = table.find_elements(By.TAG_NAME, "tr")[
                    1:
                ]  # Skip header row
                print(f"🔍 Case CMs: Found {len(row_elements)} total row elements")

                for row_index, row in enumerate(row_elements):
                    if len(rows) >= self.max_history_rows:
                        print(
                            f"⏹️ Case CMs: Reached max history rows ({self.max_history_rows})"
                        )
                        break
                    cells = row.find_elements(By.TAG_NAME, "td")
                    row_data = []

                    # Check if this is a "No data available" row
                    if len(cells) == 1:
                        cell_text = cells[0].text.strip()
                        if "No data available" in cell_text:
                            print(
                                f"⚠️ Case CMs: Row {row_index + 1} contains 'No data available'"
                            )
                            continue

                    for cell in cells:
                        row_data.append(cell.text.strip())

                    # Include ALL rows that have data (don't skip first entry)
                    if row_data and len(row_data) > 0:
                        rows.append(row_data)
                        print(
                            f"✅ Case CMs: Added row {row_index + 1} with {len(row_data)} cells: {row_data[0] if row_data else 'N/A'}"
                        )
                    else:
                        print(f"⚠️ Case CMs: Skipped empty row {row_index + 1}")

                if rows:
                    history_content["content"]["rows"] = rows[: self.max_history_rows]
                    print(
                        f"✅ Case CMs: Found {len(rows)} data rows (including first entry)"
                    )
                else:
                    print("⚠️ Case CMs: No data rows found")

                return history_content

        except Exception as e:
            print(f"❌ Error extracting Case CMs data: {e}")
            return None

    def _extract_judgement_data(self, history_content):
        """Extract data from Judgement (PDF link)"""
        try:
            # For Judgement, we need to get the PDF URL and download info
            current_url = self.driver.current_url

            # Check if we're on a PDF page
            if current_url.endswith(".pdf") or "judgements" in current_url:
                history_content["content"]["pdf_url"] = current_url
                history_content["content"]["pdf_filename"] = (
                    current_url.split("/")[-1] if "/" in current_url else "unknown.pdf"
                )

                # Try to get the page title or any text content
                try:
                    page_title = self.driver.title
                    history_content["content"]["page_title"] = page_title
                    print(f"✅ Judgement: Found PDF at {current_url}")
                except:
                    pass

                return history_content
            else:
                print("⚠️ Judgement: Not on a PDF page")
                return None

        except Exception as e:
            print(f"❌ Error extracting Judgement data: {e}")
            return None

    def close_history_modal(self):
        """Close a history modal/popup"""
        try:
            print("🔍 Attempting to close history modal...")

            # First, try to find the modal dialog itself
            modal_selectors = [
                "//div[contains(@class, 'modal')]",
                "//div[contains(@class, 'modal-dialog')]",
                "//div[contains(@class, 'modal-content')]",
                "//div[contains(@id, 'myModal')]",
            ]

            modal_found = False
            for modal_selector in modal_selectors:
                try:
                    modals = self.driver.find_elements(By.XPATH, modal_selector)
                    for modal in modals:
                        if modal.is_displayed():
                            modal_found = True
                            print(
                                f"✅ Found active modal: {modal.get_attribute('class')}"
                            )
                            break
                    if modal_found:
                        break
                except:
                    continue

            if not modal_found:
                print("⚠️ No active modal found")
                return True  # Assume it's already closed

            # Try multiple close button selectors with more specific targeting
            close_selectors = [
                # Most specific - button with close class in modal header
                "//div[contains(@class, 'modal-header')]//button[contains(@class, 'close')]",
                "//div[contains(@class, 'modal-header')]//button[@data-dismiss='modal']",
                "//div[contains(@class, 'modal-header')]//button[@aria-hidden='true']",
                # X button with span
                "//div[contains(@class, 'modal-header')]//button//span[contains(text(), '×')]",
                "//div[contains(@class, 'modal-header')]//button//span[@aria-hidden='true']",
                # General close buttons
                "//button[contains(@class, 'close')]",
                "//button[@data-dismiss='modal']",
                "//button[@aria-hidden='true']",
                # X text
                "//*[text()='×']",
                "//*[text()='✕']",
                # Any button with close in class or title
                "//button[contains(@class, 'close') or contains(@title, 'Close')]",
                # Fallback - any clickable element that might be a close button
                "//*[contains(@class, 'close') and (self::button or self::a or self::span)]",
            ]

            for selector in close_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            element_text = element.text.strip()
                            element_tag = element.tag_name
                            element_class = element.get_attribute("class") or ""

                            print(
                                f"🔍 Found potential close element: {element_tag} with text='{element_text}', class='{element_class}'"
                            )

                            # Try multiple click methods
                            click_success = False

                            # Method 1: Direct click
                            try:
                                element.click()
                                print("✅ Clicked close button (direct)")
                                click_success = True
                            except Exception as e1:
                                print(f"⚠️ Direct click failed: {e1}")

                                # Method 2: JavaScript click
                                try:
                                    self.driver.execute_script(
                                        "arguments[0].click();", element
                                    )
                                    print("✅ Clicked close button (JavaScript)")
                                    click_success = True
                                except Exception as e2:
                                    print(f"⚠️ JavaScript click failed: {e2}")

                                    # Method 3: Scroll into view and click
                                    try:
                                        self.driver.execute_script(
                                            "arguments[0].scrollIntoView(true);",
                                            element,
                                        )
                                        time.sleep(0.5)
                                        element.click()
                                        print(
                                            "✅ Clicked close button (scroll + click)"
                                        )
                                        click_success = True
                                    except Exception as e3:
                                        print(f"⚠️ Scroll + click failed: {e3}")

                            if click_success:
                                time.sleep(2)  # Wait for modal to close

                                # Verify modal is actually closed
                                try:
                                    # Check if modal is still visible
                                    modals = self.driver.find_elements(
                                        By.XPATH, "//div[contains(@class, 'modal')]"
                                    )
                                    modal_still_open = False
                                    for modal in modals:
                                        if modal.is_displayed():
                                            modal_still_open = True
                                            break

                                    if not modal_still_open:
                                        print("✅ Modal successfully closed")
                                        return True
                                    else:
                                        print(
                                            "⚠️ Modal still appears to be open after click"
                                        )
                                except:
                                    print("✅ Modal close verification completed")
                                    return True

                except Exception as e:
                    continue

            # Try Escape key as final fallback
            try:
                print("🔄 Trying Escape key as fallback...")
                from selenium.webdriver.common.keys import Keys

                self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                print("✅ Pressed Escape key")
                time.sleep(2)

                # Verify modal is closed after Escape
                try:
                    modals = self.driver.find_elements(
                        By.XPATH, "//div[contains(@class, 'modal')]"
                    )
                    modal_still_open = False
                    for modal in modals:
                        if modal.is_displayed():
                            modal_still_open = True
                            break

                    if not modal_still_open:
                        print("✅ Modal successfully closed with Escape key")
                        return True
                    else:
                        print("⚠️ Modal still open after Escape key")
                except:
                    print("✅ Escape key modal close verification completed")
                    return True

            except Exception as e:
                print(f"⚠️ Escape key failed: {e}")

            print("❌ Could not close modal with any method")
            return False

        except Exception as e:
            print(f"❌ Error in close_history_modal: {e}")
            return False

    def fetch_case_detail_options(self):
        """
        Fetch data from the 4 additional options in the case details modal:
        Parties, Comments, Case CMs, and Hearing Details

        Returns:
            dict: Additional details data or empty dict if failed
        """
        try:
            print(
                "🔍 Looking for case detail options (Parties, Comments, Case CMs, Hearing Details)..."
            )

            # Store current window handle
            original_window = self.driver.current_window_handle

            additional_details = {}

            # Define the four options we want to fetch
            detail_options = ["Parties", "Comments", "Case CMs", "Hearing Details"]

            for option_type in detail_options:
                print(f"🔍 Looking for '{option_type}' button...")

                # Find the button for this option type
                target_element = None

                # Look for buttons with specific text
                try:
                    buttons = self.driver.find_elements(By.TAG_NAME, "button")
                    for button in buttons:
                        button_text = button.text.strip()
                        if option_type.lower() in button_text.lower():
                            target_element = button
                            print(f"✅ Found '{option_type}' button")
                            break
                except:
                    pass

                # If not found as button, look for other elements
                if not target_element:
                    try:
                        all_elements = self.driver.find_elements(
                            By.XPATH, f"//*[contains(text(), '{option_type}')]"
                        )
                        for element in all_elements:
                            if element.is_displayed() and element.is_enabled():
                                target_element = element
                                print(f"✅ Found '{option_type}' element")
                                break
                    except:
                        pass

                if not target_element:
                    print(f"⚠️ Could not find '{option_type}' button")
                    continue

                # Click the option button
                try:
                    print(f"🖱️ Clicking '{option_type}' button...")
                    target_element.click()
                    time.sleep(3)  # Wait for modal/popup to load

                    # Extract data from the opened modal/popup
                    option_content = self.extract_case_detail_option_content(
                        option_type
                    )
                    if option_content and "content" in option_content:
                        additional_details[
                            f"{option_type.upper().replace(' ', '_')}_DETAIL_DATA"
                        ] = option_content["content"]
                        print(f"✅ Extracted '{option_type}' data")
                    else:
                        print(f"⚠️ No data extracted for '{option_type}'")

                    # Close the option modal/popup
                    print(f"🔍 Closing '{option_type}' modal...")
                    close_success = False
                    try:
                        close_success = self.close_case_detail_option_modal()
                        if close_success:
                            print(f"✅ Successfully closed '{option_type}' modal")
                        else:
                            print(
                                f"⚠️ Failed to close '{option_type}' modal, trying alternative methods..."
                            )
                    except Exception as close_error:
                        print(f"⚠️ Error closing '{option_type}' modal: {close_error}")

                    # Try alternative closing methods if needed
                    if not close_success:
                        try:
                            from selenium.webdriver.common.keys import Keys

                            self.driver.find_element(By.TAG_NAME, "body").send_keys(
                                Keys.ESCAPE
                            )
                            print(f"✅ Used Escape key to close '{option_type}' modal")
                            time.sleep(1)
                        except Exception as escape_error:
                            print(
                                f"⚠️ Escape key also failed for '{option_type}' modal: {escape_error}"
                            )

                    # Wait a moment to ensure modal is fully closed
                    time.sleep(2)

                except Exception as e:
                    print(f"⚠️ Error processing '{option_type}': {e}")
                    # Try to close any open modal to prevent blocking
                    try:
                        from selenium.webdriver.common.keys import Keys

                        self.driver.find_element(By.TAG_NAME, "body").send_keys(
                            Keys.ESCAPE
                        )
                        print(f"✅ Used Escape key to close modal after error")
                        time.sleep(1)
                    except:
                        pass
                    continue

            print(
                f"✅ Successfully extracted data for {len(additional_details)} detail options"
            )
            return additional_details

        except Exception as e:
            print(f"❌ Error fetching case detail options: {e}")
            return {}

    def extract_case_detail_option_content(self, option_type):
        """
        Extract content from a case detail option modal/popup

        Args:
            option_type: Type of option (Parties, Comments, Case CMs, Hearing Details)

        Returns:
            dict: Extracted option content
        """
        try:
            option_content = {"content": {}}

            # Wait for content to load
            time.sleep(2)

            # Handle different option types based on the modal titles
            if option_type == "Parties":
                # Parties opens "Case Parties" modal
                return self._extract_parties_data(option_content)

            elif option_type == "Comments":
                # Comments opens "Doc History" modal
                return self._extract_comments_detail_data(option_content)
            elif option_type == "Case CMs":
                # Case CMs opens "CMs of Case" modal
                return self._extract_case_cms_detail_data(option_content)
            elif option_type == "Hearing Details":
                # Hearing Details opens hearing information modal
                return self._extract_hearing_details_data(option_content)
            else:
                print(f"⚠️ Unknown option type: {option_type}")
                return None

        except Exception as e:
            print(f"❌ Error extracting {option_type} content: {e}")
            return None

    def _extract_parties_data(self, option_content):
        """Extract data from Parties modal (Case Parties)"""
        try:
            # Look for the specific table with id="tblPrty"
            table = self.driver.find_element(By.ID, "tblPrty")
            if table:
                # Extract headers
                headers = []
                header_elements = table.find_elements(By.TAG_NAME, "th")
                for header in header_elements:
                    headers.append(header.text.strip())

                if headers:
                    option_content["content"]["headers"] = headers
                    print(f"✅ Parties: Found {len(headers)} headers: {headers}")

                # Comprehensive row extraction - try multiple approaches
                rows = []

                # Method 1: Get ALL tr elements in the table (including nested ones)
                all_tr_elements = table.find_elements(By.XPATH, ".//tr")
                print(
                    f"🔍 Parties: Found {len(all_tr_elements)} total tr elements in table"
                )

                # Skip the first tr if it's a header
                data_tr_elements = all_tr_elements[1:] if all_tr_elements else []

                for tr_index, tr in enumerate(data_tr_elements):
                    cells = tr.find_elements(By.TAG_NAME, "td")
                    row_data = []
                    for cell in cells:
                        cell_text = cell.text.strip()
                        row_data.append(cell_text)

                    print(
                        f"🔍 Parties: TR {tr_index + 1} has {len(cells)} cells: {row_data}"
                    )

                    # Include row if it has any data (not just empty cells)
                    if row_data and any(cell_text for cell_text in row_data):
                        # Skip rows that contain "No data available"
                        if not any(
                            "No data available" in cell_text for cell_text in row_data
                        ):
                            # Check if this row is already added
                            if row_data not in rows:
                                rows.append(row_data)
                                print(
                                    f"✅ Parties: Added TR {tr_index + 1}: {row_data}"
                                )
                        else:
                            print(
                                f"⚠️ Parties: Skipping 'No data available' TR {tr_index + 1}: {row_data}"
                            )
                    else:
                        print(
                            f"⚠️ Parties: Skipping empty TR {tr_index + 1}: {row_data}"
                        )

                # Method 2: Also check tbody specifically
                tbody_elements = table.find_elements(By.TAG_NAME, "tbody")
                if tbody_elements:
                    print(f"🔍 Parties: Found {len(tbody_elements)} tbody elements")
                    for tbody_index, tbody in enumerate(tbody_elements):
                        tbody_rows = tbody.find_elements(By.TAG_NAME, "tr")
                        print(
                            f"🔍 Parties: Tbody {tbody_index + 1} has {len(tbody_rows)} rows"
                        )

                        for row_index, row in enumerate(tbody_rows):
                            cells = row.find_elements(By.TAG_NAME, "td")
                            row_data = []
                            for cell in cells:
                                cell_text = cell.text.strip()
                                row_data.append(cell_text)

                            print(
                                f"🔍 Parties: Tbody {tbody_index + 1}, Row {row_index + 1} has {len(cells)} cells: {row_data}"
                            )

                            # Include row if it has any data (not just empty cells)
                            if row_data and any(cell_text for cell_text in row_data):
                                # Skip rows that contain "No data available"
                                if not any(
                                    "No data available" in cell_text
                                    for cell_text in row_data
                                ):
                                    # Check if this row is already added
                                    if row_data not in rows:
                                        rows.append(row_data)
                                        print(
                                            f"✅ Parties: Added tbody {tbody_index + 1}, row {row_index + 1}: {row_data}"
                                        )
                                else:
                                    print(
                                        f"⚠️ Parties: Skipping 'No data available' tbody row: {row_data}"
                                    )
                            else:
                                print(
                                    f"⚠️ Parties: Skipping empty tbody row: {row_data}"
                                )

                if rows:
                    option_content["content"]["rows"] = rows
                    print(f"✅ Parties: Found {len(rows)} data rows")
                else:
                    print("⚠️ Parties: No data rows found")

                return option_content

        except Exception as e:
            print(f"❌ Error extracting Parties data: {e}")
            return None

    def _extract_comments_detail_data(self, option_content):
        """Extract data from Comments modal (Doc History)"""
        try:
            # Look for the specific table with id="tblCmntsHstry"
            table = self.driver.find_element(By.ID, "tblCmntsHstry")
            if table:
                # Extract headers
                headers = []
                header_elements = table.find_elements(By.TAG_NAME, "th")
                for header in header_elements:
                    headers.append(header.text.strip())

                if headers:
                    option_content["content"]["headers"] = headers
                    print(
                        f"✅ Comments Detail: Found {len(headers)} headers: {headers}"
                    )

                # Comprehensive row extraction - try multiple approaches
                rows = []

                # Method 1: Get ALL tr elements in the table (including nested ones)
                all_tr_elements = table.find_elements(By.XPATH, ".//tr")
                print(
                    f"🔍 Comments Detail: Found {len(all_tr_elements)} total tr elements in table"
                )

                # Skip the first tr if it's a header
                data_tr_elements = all_tr_elements[1:] if all_tr_elements else []

                for tr_index, tr in enumerate(data_tr_elements):
                    cells = tr.find_elements(By.TAG_NAME, "td")
                    row_data = []
                    for cell in cells:
                        cell_text = cell.text.strip()
                        row_data.append(cell_text)

                    print(
                        f"🔍 Comments Detail: TR {tr_index + 1} has {len(cells)} cells: {row_data}"
                    )

                    # Include row if it has any data (not just empty cells)
                    if row_data and any(cell_text for cell_text in row_data):
                        # Skip rows that contain "No data available"
                        if not any(
                            "No data available" in cell_text for cell_text in row_data
                        ):
                            # Check if this row is already added
                            if row_data not in rows:
                                rows.append(row_data)
                                print(
                                    f"✅ Comments Detail: Added TR {tr_index + 1}: {row_data}"
                                )
                        else:
                            print(
                                f"⚠️ Comments Detail: Skipping 'No data available' TR {tr_index + 1}: {row_data}"
                            )
                    else:
                        print(
                            f"⚠️ Comments Detail: Skipping empty TR {tr_index + 1}: {row_data}"
                        )

                # Method 2: Also check tbody specifically
                tbody_elements = table.find_elements(By.TAG_NAME, "tbody")
                if tbody_elements:
                    print(
                        f"🔍 Comments Detail: Found {len(tbody_elements)} tbody elements"
                    )
                    for tbody_index, tbody in enumerate(tbody_elements):
                        tbody_rows = tbody.find_elements(By.TAG_NAME, "tr")
                        print(
                            f"🔍 Comments Detail: Tbody {tbody_index + 1} has {len(tbody_rows)} rows"
                        )

                        for row_index, row in enumerate(tbody_rows):
                            cells = row.find_elements(By.TAG_NAME, "td")
                            row_data = []
                            for cell in cells:
                                cell_text = cell.text.strip()
                                row_data.append(cell_text)

                            print(
                                f"🔍 Comments Detail: Tbody {tbody_index + 1}, Row {row_index + 1} has {len(cells)} cells: {row_data}"
                            )

                            # Include row if it has any data (not just empty cells)
                            if row_data and any(cell_text for cell_text in row_data):
                                # Skip rows that contain "No data available"
                                if not any(
                                    "No data available" in cell_text
                                    for cell_text in row_data
                                ):
                                    # Check if this row is already added
                                    if row_data not in rows:
                                        rows.append(row_data)
                                        print(
                                            f"✅ Comments Detail: Added tbody {tbody_index + 1}, row {row_index + 1}: {row_data}"
                                        )
                                else:
                                    print(
                                        f"⚠️ Comments Detail: Skipping 'No data available' tbody row: {row_data}"
                                    )
                            else:
                                print(
                                    f"⚠️ Comments Detail: Skipping empty tbody row: {row_data}"
                                )

                if rows:
                    option_content["content"]["rows"] = rows
                    print(f"✅ Comments Detail: Found {len(rows)} data rows")
                else:
                    print("⚠️ Comments Detail: No data rows found")

                return option_content

        except Exception as e:
            print(f"❌ Error extracting Comments Detail data: {e}")
            return None

    def _extract_case_cms_detail_data(self, option_content):
        """Extract data from Case CMs modal (CMs of Case)"""
        try:
            # Look for the specific table with id="tblCmsHstry"
            table = self.driver.find_element(By.ID, "tblCmsHstry")
            if table:
                # Extract headers
                headers = []
                header_elements = table.find_elements(By.TAG_NAME, "th")
                for header in header_elements:
                    headers.append(header.text.strip())

                if headers:
                    option_content["content"]["headers"] = headers
                    print(
                        f"✅ Case CMs Detail: Found {len(headers)} headers: {headers}"
                    )

                # Comprehensive row extraction - try multiple approaches
                rows = []

                # Method 1: Get ALL tr elements in the table (including nested ones)
                all_tr_elements = table.find_elements(By.XPATH, ".//tr")
                print(
                    f"🔍 Case CMs Detail: Found {len(all_tr_elements)} total tr elements in table"
                )

                # Skip the first tr if it's a header
                data_tr_elements = all_tr_elements[1:] if all_tr_elements else []

                for tr_index, tr in enumerate(data_tr_elements):
                    cells = tr.find_elements(By.TAG_NAME, "td")
                    row_data = []
                    for cell in cells:
                        cell_text = cell.text.strip()
                        row_data.append(cell_text)

                    print(
                        f"🔍 Case CMs Detail: TR {tr_index + 1} has {len(cells)} cells: {row_data}"
                    )

                    # Include row if it has any data (not just empty cells)
                    if row_data and any(cell_text for cell_text in row_data):
                        # Skip rows that contain "No data available"
                        if not any(
                            "No data available" in cell_text for cell_text in row_data
                        ):
                            # Check if this row is already added
                            if row_data not in rows:
                                rows.append(row_data)
                                print(
                                    f"✅ Case CMs Detail: Added TR {tr_index + 1}: {row_data}"
                                )
                        else:
                            print(
                                f"⚠️ Case CMs Detail: Skipping 'No data available' TR {tr_index + 1}: {row_data}"
                            )
                    else:
                        print(
                            f"⚠️ Case CMs Detail: Skipping empty TR {tr_index + 1}: {row_data}"
                        )

                # Method 2: Also check tbody specifically
                tbody_elements = table.find_elements(By.TAG_NAME, "tbody")
                if tbody_elements:
                    print(
                        f"🔍 Case CMs Detail: Found {len(tbody_elements)} tbody elements"
                    )
                    for tbody_index, tbody in enumerate(tbody_elements):
                        tbody_rows = tbody.find_elements(By.TAG_NAME, "tr")
                        print(
                            f"🔍 Case CMs Detail: Tbody {tbody_index + 1} has {len(tbody_rows)} rows"
                        )

                        for row_index, row in enumerate(tbody_rows):
                            cells = row.find_elements(By.TAG_NAME, "td")
                            row_data = []
                            for cell in cells:
                                cell_text = cell.text.strip()
                                row_data.append(cell_text)

                            print(
                                f"🔍 Case CMs Detail: Tbody {tbody_index + 1}, Row {row_index + 1} has {len(cells)} cells: {row_data}"
                            )

                            # Include row if it has any data (not just empty cells)
                            if row_data and any(cell_text for cell_text in row_data):
                                # Skip rows that contain "No data available"
                                if not any(
                                    "No data available" in cell_text
                                    for cell_text in row_data
                                ):
                                    # Check if this row is already added
                                    if row_data not in rows:
                                        rows.append(row_data)
                                        print(
                                            f"✅ Case CMs Detail: Added tbody {tbody_index + 1}, row {row_index + 1}: {row_data}"
                                        )
                                else:
                                    print(
                                        f"⚠️ Case CMs Detail: Skipping 'No data available' tbody row: {row_data}"
                                    )
                            else:
                                print(
                                    f"⚠️ Case CMs Detail: Skipping empty tbody row: {row_data}"
                                )

                if rows:
                    option_content["content"]["rows"] = rows
                    print(f"✅ Case CMs Detail: Found {len(rows)} data rows")
                else:
                    print("⚠️ Case CMs Detail: No data rows found")

                return option_content

        except Exception as e:
            print(f"❌ Error extracting Case CMs Detail data: {e}")
            return None

    def _extract_hearing_details_data(self, option_content):
        """Extract data from Hearing Details modal (Case History) with robust stale element handling"""
        
        def extract_hearing_details():
            """Inner function for extraction with retry logic"""
            try:
                # Update activity time before extraction
                self._update_activity_time()
                
                # Look for the specific table with id="tblCseHstry" (same as Orders)
                table = self._safe_find_element(self.driver, By.ID, "tblCseHstry")
                if not table:
                    print("⚠️ Hearing Details: Table not found")
                    return None
                
                # Extract headers with retry
                headers = []
                header_elements = self._safe_find_elements_with_retry(self.driver, By.TAG_NAME, "th", timeout=5)
                
                for header in header_elements:
                    header_text = self._safe_get_text_with_retry(header)
                    if header_text:
                        headers.append(header_text)

                if headers:
                    option_content["content"]["headers"] = headers
                    print(f"✅ Hearing Details: Found {len(headers)} headers: {headers}")

                # Single comprehensive row extraction approach (avoiding duplicate DOM traversals)
                rows = []
                
                # Get all tbody elements first
                tbody_elements = self._safe_find_elements_with_retry(self.driver, By.TAG_NAME, "tbody", timeout=5)
                
                if tbody_elements:
                    print(f"🔍 Hearing Details: Found {len(tbody_elements)} tbody elements")
                    
                    for tbody_index, tbody in enumerate(tbody_elements):
                        # Update activity time for each tbody
                        self._update_activity_time()
                        
                        tbody_rows = self._safe_find_elements_with_retry(tbody, By.TAG_NAME, "tr", timeout=5)
                        print(f"🔍 Hearing Details: Tbody {tbody_index + 1} has {len(tbody_rows)} rows")

                        # Early exit: Skip tbody with many rows if first 3 are empty (likely empty tbody)
                        if len(tbody_rows) > 10:
                            first_row_cells = self._safe_find_elements_with_retry(tbody_rows[0], By.TAG_NAME, "td", timeout=1)
                            if first_row_cells:
                                first_row_text = " ".join([self._safe_get_text_with_retry(cell) for cell in first_row_cells[:3]])
                                if not first_row_text.strip():
                                    print(f"⚠️ Hearing Details: Tbody {tbody_index + 1} appears empty (first row has no text), skipping all {len(tbody_rows)} rows")
                                    continue

                        consecutive_empty = 0
                        max_consecutive_empty = 5  # Stop after 5 consecutive empty rows
                        
                        for row_index, row in enumerate(tbody_rows):
                            # Update activity time for each row
                            self._update_activity_time()
                            
                            cells = self._safe_find_elements_with_retry(row, By.TAG_NAME, "td", timeout=5)
                            row_data = []

                            for cell_index, cell in enumerate(cells):
                                cell_text = self._safe_get_text_with_retry(cell)

                                # Special handling for VIEW column (last column)
                                if cell_index == len(cells) - 1 and headers and "VIEW" in headers[-1]:
                                    # Look for download links in the VIEW column with retry
                                    try:
                                        download_links = self._safe_find_elements_with_retry(cell, By.TAG_NAME, "a", timeout=3)
                                        if download_links:
                                            link_data = []
                                            for link in download_links:
                                                try:
                                                    href = link.get_attribute("href")
                                                    title = link.get_attribute("title") or ""
                                                    link_text = self._safe_get_text_with_retry(link)

                                                    if href:
                                                        link_info = {
                                                            "href": href,
                                                            "title": title,
                                                            "text": link_text,
                                                        }
                                                        link_data.append(link_info)
                                                except StaleElementReferenceException:
                                                    print(f"⚠️ Stale link element, skipping...")
                                                    continue

                                            if link_data:
                                                row_data.append(link_data)
                                                print(f"✅ Hearing Details: Found {len(link_data)} download link(s) in tbody {tbody_index + 1}, row {row_index + 1}")
                                            else:
                                                row_data.append(cell_text)
                                        else:
                                            row_data.append(cell_text)
                                    except Exception as link_error:
                                        print(f"⚠️ Error extracting VIEW column links: {link_error}")
                                        row_data.append(cell_text)
                                else:
                                    row_data.append(cell_text)

                            print(f"🔍 Hearing Details: Tbody {tbody_index + 1}, Row {row_index + 1} has {len(cells)} cells: {row_data}")

                            # Include row if it has any data (not just empty cells)
                            if row_data and any(
                                cell_text
                                for cell_text in row_data
                                if isinstance(cell_text, str) and cell_text.strip()
                            ):
                                # Skip rows that contain "No data available"
                                if not any(
                                    "No data available" in str(cell_text)
                                    for cell_text in row_data
                                ):
                                    # Check if this row is already added
                                    if row_data not in rows:
                                        rows.append(row_data)
                                        print(f"✅ Hearing Details: Added tbody {tbody_index + 1}, row {row_index + 1}: {row_data}")
                                        consecutive_empty = 0  # Reset counter on valid row
                                else:
                                    print(f"⚠️ Hearing Details: Skipping 'No data available' tbody row: {row_data}")
                                    consecutive_empty += 1
                            else:
                                print(f"⚠️ Hearing Details: Skipping empty tbody row: {row_data}")
                                consecutive_empty += 1
                            
                            # Break early if too many consecutive empty rows
                            if consecutive_empty >= max_consecutive_empty:
                                print(f"⚠️ Hearing Details: Found {consecutive_empty} consecutive empty rows, skipping remaining {len(tbody_rows) - row_index - 1} rows in tbody {tbody_index + 1}")
                                break

                if rows:
                    option_content["content"]["rows"] = rows
                    print(f"✅ Hearing Details: Found {len(rows)} data rows with VIEW column links")
                else:
                    print("⚠️ Hearing Details: No data rows found")

                return option_content

            except StaleElementReferenceException as e:
                print(f"⚠️ Stale element during Hearing Details extraction: {e}")
                raise  # Re-raise to be caught by retry logic
            except Exception as e:
                print(f"❌ Unexpected error during Hearing Details extraction: {e}")
                return None
        
        # Use the retry wrapper for the entire extraction
        return self._safe_extract_with_retry(extract_hearing_details, max_retries=3, retry_delay=3)

    def close_case_detail_option_modal(self):
        """Close a case detail option modal/popup"""
        try:
            # Try to find close button
            close_selectors = [
                "//button[contains(@class, 'close')]",
                "//button[@data-dismiss='modal']",
                "//*[contains(@class, 'close')]",
                "//img[contains(@src, 'close')]",
                "//*[text()='×']",
                "//*[text()='✕']",
            ]

            for selector in close_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            element.click()
                            print(
                                "✅ Clicked close button for case detail option modal"
                            )
                            time.sleep(1)
                            return True
                except:
                    continue

            # Try Escape key as fallback
            try:
                from selenium.webdriver.common.keys import Keys

                self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                print("✅ Pressed Escape to close case detail option modal")
                time.sleep(1)
                return True
            except:
                pass

            print("⚠️ Could not close case detail option modal")
            return False

        except Exception as e:
            print(f"❌ Error closing case detail option modal: {e}")
            return False

    def restart_driver(self):
        """Restart the WebDriver if it gets disconnected"""
        try:
            print("🔄 Restarting WebDriver due to session timeout...")
            self.stop_driver()
            time.sleep(2)
            return self.start_driver()
        except Exception as e:
            print(f"❌ Error restarting WebDriver: {e}")
            return False

    def search_case(
        self, case_no=None, year=None, case_type=None, search_by_case_number=True
    ):
        """Search for cases with the given parameters"""
        try:
            # Navigate to case status page
            if not self.navigate_to_case_status():
                return None

            # Validate we're on the correct page
            if not self.validate_current_page():
                print(f"❌ Failed to validate current page")
                return None
            
            # Check for unexpected redirects
            if not self.check_for_unexpected_redirects():
                print(f"❌ Detected unexpected redirect")
                return None

            # Fill and submit the search form
            if not self.fill_search_form_simple(case_no):
                return None

            # Determine if case type is empty for bulk data handling
            case_type_empty = case_type is None

            # Scrape the results
            all_cases_data = self.scrape_results_table(
                case_type_empty=case_type_empty, case_no=case_no
            )

            if all_cases_data:
                print(f"📊 Found {len(all_cases_data)} cases for search criteria")
                # Show first few cases for verification
                for i, case in enumerate(all_cases_data[:3]):  # Show first 3 cases
                    print(
                        f"  Case {i+1}: {case.get('CASE_NO', 'N/A')} - {case.get('CASE_TITLE', 'N/A')[:50]}..."
                    )
                if len(all_cases_data) > 3:
                    print(f"  ... and {len(all_cases_data) - 3} more cases")

            return all_cases_data

        except Exception as e:
            print(f"❌ Error searching case: {e}")
            # Check if it's a session timeout error
            if "invalid session id" in str(e).lower():
                print("🔄 Detected session timeout, attempting to restart driver...")
                if self.restart_driver():
                    print("✅ Driver restarted successfully, retrying search...")
                    return self.search_case(
                        case_no, year, case_type, search_by_case_number
                    )
                else:
                    print("❌ Failed to restart driver")
            # Check if it's a connection reset error
            elif "connection aborted" in str(e).lower() or "connectionreseterror" in str(e).lower():
                print("🔄 Detected connection reset, attempting to restart driver...")
                if self.restart_driver():
                    print("✅ Driver restarted successfully, retrying search...")
                    return self.search_case(
                        case_no, year, case_type, search_by_case_number
                    )
                else:
                    print("❌ Failed to restart driver")
            return None

    def comprehensive_search(self, max_cases_per_filter=50):
        """Perform comprehensive search using all filter combinations"""
        print("🚀 Starting comprehensive search with all filter combinations...")

        all_cases = []
        total_searches = 0
        successful_searches = 0

        # Strategy 1: Search by case number ONLY (no case type) for maximum results
        print(
            "\n📋 Strategy 1: Searching by case number ONLY (no case type) for maximum coverage..."
        )
        print(
            "💡 Discovery: Searching without case type gives 500+ results vs 16-21 with case type"
        )

        for year in self.years:
            for case_no in range(1, 101):  # Search first 100 case numbers per year
                total_searches += 1
                print(
                    f"\n🔍 Search {total_searches}: Case Number: {case_no}, Year: {year} (NO CASE TYPE)"
                )

                # Check if driver is still valid
                try:
                    self.driver.current_url
                except:
                    print("🔄 Driver session expired, restarting...")
                    if not self.restart_driver():
                        print("❌ Failed to restart driver, stopping search")
                        break

                try:
                    # Search WITHOUT case type for maximum results
                    cases = self.search_case(
                        case_no=case_no,
                        year=year,
                        case_type=None,
                        search_by_case_number=True,
                    )
                    if cases:
                        successful_searches += 1
                        all_cases.extend(cases)
                        print(
                            f"✅ Found {len(cases)} cases for case {case_no}/{year} (no case type)"
                        )

                        # Save intermediate results
                        self.save_cases_to_file(
                            all_cases,
                            f"cases_metadata/Islamabad_High_Court/comprehensive_search.json",
                        )

                        # Limit cases per filter to avoid overwhelming
                        if len(cases) > max_cases_per_filter:
                            print(
                                f"⚠️ Limiting to {max_cases_per_filter} cases per filter"
                            )
                            all_cases = (
                                all_cases[: -len(cases)] + cases[:max_cases_per_filter]
                            )
                    else:
                        print(f"❌ No cases found for case {case_no}/{year}")

                except Exception as e:
                    print(f"❌ Error in search {total_searches}: {e}")
                    # If it's a session timeout, restart driver and continue
                    if "invalid session id" in str(e).lower():
                        if self.restart_driver():
                            print("✅ Driver restarted, continuing with next search...")
                        else:
                            print("❌ Failed to restart driver, stopping search")
                            break

                # Random delay between searches
                time.sleep(random.uniform(1, 3))

                # Reset to main page for next search
                try:
                    self.driver.switch_to.default_content()
                    self.navigate_to_case_status()
                except:
                    pass

        # Strategy 2: Search by case type with case numbers for recent years (for specific filtering)
        print(
            "\n📋 Strategy 2: Searching by case type with case numbers for recent years (specific filtering)..."
        )
        recent_years = [2023, 2024, 2025]
        for case_type in self.case_types:
            for year in recent_years:
                for case_no in range(
                    1, 51
                ):  # Search first 50 case numbers per case type/year
                    total_searches += 1
                    print(
                        f"\n🔍 Search {total_searches}: Case Type: {case_type}, Case Number: {case_no}, Year: {year}"
                    )

                    # Check if driver is still valid
                    try:
                        self.driver.current_url
                    except:
                        print("🔄 Driver session expired, restarting...")
                        if not self.restart_driver():
                            print("❌ Failed to restart driver, stopping search")
                            break

                    try:
                        cases = self.search_case(
                            case_no=case_no,
                            year=year,
                            case_type=case_type,
                            search_by_case_number=True,
                        )
                        if cases:
                            successful_searches += 1
                            all_cases.extend(cases)
                            print(
                                f"✅ Found {len(cases)} cases for {case_type} case {case_no}/{year}"
                            )

                            # Save intermediate results
                            self.save_cases_to_file(
                                all_cases,
                                f"cases_metadata/Islamabad_High_Court/comprehensive_search.json",
                            )
                        else:
                            print(
                                f"❌ No cases found for {case_type} case {case_no}/{year}"
                            )

                    except Exception as e:
                        print(f"❌ Error in search {total_searches}: {e}")
                        # If it's a session timeout, restart driver and continue
                        if "invalid session id" in str(e).lower():
                            if self.restart_driver():
                                print(
                                    "✅ Driver restarted, continuing with next search..."
                                )
                            else:
                                print("❌ Failed to restart driver, stopping search")
                                break

                    # Random delay between searches
                    time.sleep(random.uniform(1, 2))

                    # Reset to main page for next search
                    try:
                        self.driver.switch_to.default_content()
                        self.navigate_to_case_status()
                    except:
                        pass

        print(f"\n📊 Comprehensive search completed!")
        print(f"📈 Total searches attempted: {total_searches}")
        print(f"✅ Successful searches: {successful_searches}")
        print(f"📋 Total cases collected: {len(all_cases)}")

        return all_cases

    def save_cases_to_file(self, cases, filename):
        """Save cases to a JSON file"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(filename), exist_ok=True)

            # Load existing data if file exists and is not empty
            existing_data = []
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                try:
                    with open(filename, "r", encoding="utf-8") as f:
                        existing_data = json.load(f)
                except json.JSONDecodeError:
                    print(
                        f"⚠️ Warning: {filename} contains invalid JSON, starting fresh"
                    )
                    existing_data = []

            # Add new cases to existing data
            all_cases = existing_data + cases

            # Save to JSON file
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(all_cases, f, indent=2, ensure_ascii=False)

            print(f"💾 Saved {len(cases)} cases to {filename}")

        except Exception as e:
            print(f"❌ Error saving to {filename}: {e}")

    def save_single_row_realtime(self, case_data, case_no, page_number, row_index):
        """Save a single row immediately to database to prevent data loss during scraping"""
        try:
            # Save to database in real-time
            result = self.db_saver.save_case(case_data)

            if result["status"] == "success":
                sr_number = case_data.get("SR", "N/A")
                print(
                    f"💾 REAL-TIME SAVE: Row {row_index} (SR={sr_number}) saved to database"
                )
                return True
            else:
                print(
                    f"❌ Error in real-time saving for row {row_index}: {result['error']}"
                )
                return False

        except Exception as e:
            print(f"❌ Error in real-time saving for row {row_index}: {e}")
            return False

    def test_case_type_vs_no_case_type(self, case_no=1, year=2025):
        """Test the difference between searching with and without case type"""
        print(f"🧪 Testing case type vs no case type for case {case_no}/{year}")

        # Test 1: Search WITH case type
        print(f"\n📋 Test 1: Searching WITH case type 'Writ Petition'")
        try:
            cases_with_type = self.search_case(
                case_no=case_no,
                year=year,
                case_type="Writ Petition",
                search_by_case_number=True,
            )
            if cases_with_type:
                print(f"✅ WITH case type: Found {len(cases_with_type)} cases")
            else:
                print(f"❌ WITH case type: No cases found")
        except Exception as e:
            print(f"❌ Error in test with case type: {e}")

        # Reset for next test
        try:
            self.driver.switch_to.default_content()
            self.navigate_to_case_status()
        except:
            pass

        # Test 2: Search WITHOUT case type
        print(f"\n📋 Test 2: Searching WITHOUT case type (empty/default)")
        try:
            cases_without_type = self.search_case(
                case_no=case_no, year=year, case_type=None, search_by_case_number=True
            )
            if cases_without_type:
                print(f"✅ WITHOUT case type: Found {len(cases_without_type)} cases")
            else:
                print(f"❌ WITHOUT case type: No cases found")
        except Exception as e:
            print(f"❌ Error in test without case type: {e}")

        # Compare results
        if cases_with_type and cases_without_type:
            ratio = len(cases_without_type) / len(cases_with_type)
            print(f"\n📊 Comparison:")
            print(f"   With case type: {len(cases_with_type)} cases")
            print(f"   Without case type: {len(cases_without_type)} cases")
            print(f"   Ratio: {ratio:.1f}x more results without case type")

            if ratio > 10:
                print(
                    f"🎯 CONFIRMED: Leaving case type empty gives {ratio:.1f}x more results!"
                )
            else:
                print(f"⚠️ Unexpected: Only {ratio:.1f}x difference")

        return cases_with_type, cases_without_type

    def test_bulk_data_loading(self, case_no=1, year=2025):
        """Test bulk data loading with empty case type"""
        print(
            f"🧪 Testing bulk data loading for case {case_no}/{year} with empty case type"
        )
        print("⏳ This will take longer as it loads 500+ results...")

        try:
            # Search WITHOUT case type for bulk data
            cases = self.search_case(
                case_no=case_no, year=year, case_type=None, search_by_case_number=True
            )
            if cases:
                print(f"🎯 SUCCESS! Found {len(cases)} cases with bulk data loading")
                print(f"📊 This confirms the longer wait times work for 500+ results")

                # Show sample of results
                print(f"\n📋 Sample results:")
                for i, case in enumerate(cases[:5]):
                    print(
                        f"  {i+1}. {case.get('CASE_NO', 'N/A')} - {case.get('CASE_TITLE', 'N/A')[:60]}..."
                    )
                if len(cases) > 5:
                    print(f"  ... and {len(cases) - 5} more cases")

                return cases
            else:
                print(f"❌ No cases found with bulk data loading")
                return None

        except Exception as e:
            print(f"❌ Error in bulk data test: {e}")
            return None

    def parallel_scrape_cases(
        self, batch_number=1, cases_per_batch=5, max_workers=3, custom_case_numbers=None
    ):
        """
        Scrape cases in parallel with individual file saving

        Args:
            batch_number: Which batch to process (1 = cases 1-5, 2 = cases 6-10, etc.)
            cases_per_batch: Number of cases per batch (default: 5)
            max_workers: Number of parallel browser windows (default: 3 - reduced to avoid conflicts)
            custom_case_numbers: Override batch calculation with specific case numbers
        """
        import concurrent.futures
        import threading
        import os
        import json
        from datetime import datetime

        # Calculate case numbers for this batch
        if custom_case_numbers:
            # Use custom case numbers if provided
            case_numbers = custom_case_numbers
            print(f"🚀 Starting CUSTOM CASES: {case_numbers}")
            print(
                f"📊 Configuration: {max_workers} parallel windows, {len(case_numbers)} custom cases"
            )
        else:
            # Use batch calculation
            start_case = ((batch_number - 1) * cases_per_batch) + 1
            end_case = batch_number * cases_per_batch
            case_numbers = list(range(start_case, end_case + 1))
            print(f"🚀 Starting BATCH {batch_number}: Cases {start_case}-{end_case}")
            print(
                f"📊 Configuration: {max_workers} parallel windows, {cases_per_batch} cases per batch"
            )

        # Create directory for individual case files
        cases_dir = "cases_metadata/Islamabad_High_Court/individual_cases"
        os.makedirs(cases_dir, exist_ok=True)

        # PROGRESS TRACKING COMPLETELY REMOVED - NO PROGRESS FILE

        # Import progress tracker for granular tracking
        # PROGRESS TRACKING COMPLETELY REMOVED - NO IMPORTS

        # PROGRESS TRACKING COMPLETELY REMOVED - NO PROGRESS FILE LOADING
        completed_cases = set()

        # Show progress summary before starting
        self.print_progress_summary()
        
        # Check for shutdown request before starting
        if SHUTDOWN_REQUESTED:
            print("🛑 Shutdown requested before starting parallel scraping")
            return []
        
        # Filter cases to process (skip completed ones)
        cases_to_process = []
        for case_no in case_numbers:
            if not self.should_skip_case(case_no):
                cases_to_process.append(case_no)
            else:
                print(f"⏭️ Skipping case {case_no} (already completed)")
        
        print(f"📦 Processing {len(cases_to_process)} cases: {cases_to_process}")
        print(f"⏭️ Skipped {len(case_numbers) - len(cases_to_process)} completed cases")

        # Thread-safe counters
        lock = threading.Lock()
        total_cases_found = 0
        total_cases_processed = 0

        def scrape_single_case(case_no, worker_id):
            """Scrape a single case number using a dedicated WebDriver instance with complete isolation"""
            nonlocal total_cases_found, total_cases_processed

            # Check for shutdown request
            if SHUTDOWN_REQUESTED:
                print(f"🛑 Worker {worker_id}: Shutdown requested, skipping case {case_no}")
                return None

            # Check if case should be skipped (already completed)
            if self.should_skip_case(case_no):
                print(f"⏭️ Worker {worker_id}: Case {case_no} already completed, skipping")
                return None

            # Get resume point for this case
            resume_row = self.get_case_resume_point(case_no)
            if resume_row > 0:
                print(f"🔄 Worker {worker_id}: Resuming case {case_no} from row {resume_row}")
            else:
                print(f"🆕 Worker {worker_id}: Starting case {case_no} from beginning")

            # Skip if already completed in this session
            with lock:
                if case_no in completed_cases:
                    print(
                        f"⏭️ Worker {worker_id}: Case {case_no} already completed in this session, skipping"
                    )
                    return None

            # Create dedicated scraper for this worker with retry mechanism
            worker_scraper = None
            max_retries = 3
            
            for attempt in range(max_retries):
                try:
                    # Create a completely isolated scraper instance with unique worker ID
                    worker_scraper = IHCSeleniumScraper(
                        headless=True, fetch_details=True
                    )
                    # Set unique identifier for this worker to prevent interference
                    worker_scraper.worker_id = worker_id
                    
                    if worker_scraper.start_driver():
                        print(
                            f"✅ Worker {worker_id}: WebDriver started successfully on attempt {attempt + 1}"
                        )
                        break
                    else:
                        print(
                            f"⚠️ Worker {worker_id}: WebDriver start failed on attempt {attempt + 1}"
                        )
                        if worker_scraper:
                            worker_scraper.stop_driver()
                        if attempt < max_retries - 1:
                            time.sleep(2)  # Wait before retry
                        continue
                except Exception as e:
                    print(
                        f"⚠️ Worker {worker_id}: WebDriver error on attempt {attempt + 1}: {e}"
                    )
                    if worker_scraper:
                        worker_scraper.stop_driver()
                    if attempt < max_retries - 1:
                        time.sleep(2)  # Wait before retry
                    continue
            else:
                print(
                    f"❌ Worker {worker_id}: Failed to start WebDriver after {max_retries} attempts for case {case_no}"
                )
                return None

            case_results = []
            case_start_time = datetime.now()

            try:
                print(f"🔍 Worker {worker_id}: Starting case {case_no}")

                # Navigate and search
                if not worker_scraper.navigate_to_case_status():
                    print(
                        f"❌ Worker {worker_id}: Failed to navigate for case {case_no}"
                    )
                    return None

                # Validate navigation and check for redirects
                if not worker_scraper.validate_current_page():
                    print(f"⚠️ Worker {worker_id}: Navigation validation failed, attempting recovery...")
                    if not worker_scraper.recover_navigation():
                        print(f"❌ Worker {worker_id}: Navigation recovery failed for case {case_no}")
                        return None
                
                if not worker_scraper.check_for_unexpected_redirects():
                    print(f"⚠️ Worker {worker_id}: Unexpected redirect detected, attempting recovery...")
                    if not worker_scraper.recover_navigation():
                        print(f"❌ Worker {worker_id}: Navigation recovery failed for case {case_no}")
                    return None

                if not worker_scraper.fill_search_form_simple(case_no):
                    print(
                        f"❌ Worker {worker_id}: Failed to fill form for case {case_no}"
                    )
                    return None

                # Scrape results with retry mechanism
                max_scrape_retries = 3
                cases = None

                for scrape_attempt in range(max_scrape_retries):
                    try:
                        print(
                            f"🔍 Worker {worker_id}: Scraping attempt {scrape_attempt + 1}/{max_scrape_retries}"
                        )
                        cases = worker_scraper.scrape_results_table(
                            case_type_empty=True, case_no=case_no
                        )

                        if cases is None:  # None indicates failure or session timeout
                            print(f"❌ Worker {worker_id}: Scraping failed on attempt {scrape_attempt + 1}")
                            if scrape_attempt < max_scrape_retries - 1:
                                print(f"🔄 Worker {worker_id}: Retrying in 5 seconds...")
                                time.sleep(5)
                            else:
                                print(f"❌ Worker {worker_id}: All attempts failed for case {case_no}")
                            continue
                        elif cases:  # Non-empty list means we got results
                            print(f"✅ Worker {worker_id}: Scraping successful on attempt {scrape_attempt + 1}")
                            break
                        else:  # Empty list means no results found
                            print(f"⚠️ Worker {worker_id}: No results found on attempt {scrape_attempt + 1}")
                            # Don't retry if no results found (case might be empty)
                            break

                    except Exception as e:
                        print(
                            f"❌ Worker {worker_id}: Scraping error on attempt {scrape_attempt + 1}: {e}"
                        )
                        if scrape_attempt < max_scrape_retries - 1:
                            print(f"🔄 Worker {worker_id}: Retrying in 10 seconds...")
                            time.sleep(10)
                        else:
                            print(
                                f"❌ Worker {worker_id}: All scraping attempts failed for case {case_no}"
                            )
                            cases = None

                if cases:
                    # Add metadata
                    for case in cases:
                        case["SEARCH_CASE_NO"] = case_no
                        case["WORKER_ID"] = worker_id
                        case["SCRAPE_TIMESTAMP"] = datetime.now().isoformat()
                        case["BATCH_NUMBER"] = batch_number

                    case_results.extend(cases)

                    with lock:
                        total_cases_found += len(cases)
                        total_cases_processed += 1
                        completed_cases.add(case_no)

                    print(
                        f"✅ Worker {worker_id}: Case {case_no} → {len(cases)} results"
                    )

                    # Save to database in real-time
                    for case_data in cases:
                        result = worker_scraper.db_saver.save_case(case_data)
                        if result["status"] == "success":
                            print(
                                f"💾 Worker {worker_id}: ✅ Case {case_data.get('CASE_NO')} saved to database"
                            )
                        else:
                            print(
                                f"❌ Worker {worker_id}: Failed to save case {case_data.get('CASE_NO')}: {result['error']}"
                            )

                else:
                    if cases is None:  # Scraping failed
                        print(f"❌ Worker {worker_id}: Case {case_no} → Scraping failed, will retry later")
                        # Don't mark as completed if scraping failed
                        # Check if case is truly completed based on progress
                        if case_no in self.progress_data:
                            progress = self.progress_data[str(case_no)]
                            current_row = progress.get('current_row', 0)
                            total_rows = progress.get('total_rows')
                            if total_rows and total_rows > 0 and current_row >= total_rows:
                                print(f"✅ Worker {worker_id}: Case {case_no} → All rows processed, marking as completed")
                                with lock:
                                    completed_cases.add(case_no)
                            elif total_rows is None:
                                print(f"⚠️ Worker {worker_id}: Case {case_no} → Total rows not determined yet, will retry")
                    else:  # cases is empty list
                        print(f"⚠️ Worker {worker_id}: Case {case_no} → No results found")
                        with lock:
                            completed_cases.add(case_no)

                # PROGRESS TRACKING COMPLETELY REMOVED - NO PROGRESS SAVING

                case_duration = datetime.now() - case_start_time
                print(
                    f"✅ Worker {worker_id}: Case {case_no} completed in {case_duration.total_seconds():.1f}s"
                )

            except Exception as e:
                print(f"❌ Worker {worker_id}: Error processing case {case_no}: {e}")
                # Mark as completed to avoid infinite retry
                with lock:
                    completed_cases.add(case_no)
            finally:
                worker_scraper.stop_driver()

            return case_results

        # Process cases with ThreadPoolExecutor - IMPROVED DISTRIBUTION
        all_results = []
        start_time = datetime.now()

        # Create a queue of cases to process (use filtered cases)
        case_queue = cases_to_process.copy()
        completed_futures = []

        print(f"📋 Case distribution strategy:")
        print(f"   - Total cases in batch: {len(case_numbers)}")
        print(f"   - Max workers: {max_workers}")
        print(f"   - Cases to process: {cases_to_process}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit initial batch of cases (one per worker) - IMPROVED ISOLATION
            active_futures = {}
            worker_assignments = {}  # Track which worker is assigned to which case
            
            for worker_id in range(min(max_workers, len(case_queue))):
                if case_queue:
                    case_no = case_queue.pop(0)
                    future = executor.submit(scrape_single_case, case_no, worker_id)
                    active_futures[future] = case_no
                    worker_assignments[case_no] = worker_id
                    print(f"🚀 Worker {worker_id} assigned case {case_no}")
                    # Small delay to prevent WebDriver interference
                    time.sleep(1)

            # Process cases as they complete and assign new ones - IMPROVED TRACKING
            while active_futures:
                # Check for shutdown request - IMMEDIATE STOP
                if SHUTDOWN_REQUESTED:
                    print("🛑 Shutdown requested during parallel processing - STOPPING IMMEDIATELY")
                    # Cancel all pending futures
                    for future in active_futures:
                        future.cancel()
                    # Save progress before exiting
                    self.save_progress()
                    return all_results
                
                # Wait for any future to complete with timeout to allow checking shutdown flag
                try:
                    done, not_done = concurrent.futures.wait(
                        active_futures.keys(),
                        return_when=concurrent.futures.FIRST_COMPLETED,
                        timeout=1.0  # Check every second for shutdown request
                    )
                except concurrent.futures.TimeoutError:
                    # Timeout occurred, check shutdown flag again
                    if SHUTDOWN_REQUESTED:
                        print("🛑 Shutdown requested during parallel processing - STOPPING IMMEDIATELY")
                        # Cancel all pending futures
                        for future in active_futures:
                            future.cancel()
                        # Save progress before exiting
                        self.save_progress()
                        return all_results
                    continue

                # Process completed futures
                for future in done:
                    case_no = active_futures[future]
                    worker_id = worker_assignments.get(case_no, "unknown")

                    try:
                        case_results = future.result()
                        if case_results:
                            all_results.extend(case_results)
                            print(
                                f"✅ Worker {worker_id}: Case {case_no} completed with {len(case_results)} results"
                            )
                        else:
                            print(
                                f"⚠️ Worker {worker_id}: Case {case_no} completed with no results"
                            )

                    except Exception as e:
                        print(f"❌ Worker {worker_id}: Case {case_no} failed: {e}")

                    # Remove completed future and update tracking
                    del active_futures[future]
                    if case_no in worker_assignments:
                        del worker_assignments[case_no]
                    completed_futures.append(future)

                    # Assign next case to this worker if available - MAINTAIN ISOLATION
                    if case_queue:
                        next_case = case_queue.pop(0)
                        new_future = executor.submit(
                            scrape_single_case, next_case, worker_id
                        )
                        active_futures[new_future] = next_case
                        worker_assignments[next_case] = worker_id
                        print(f"🔄 Worker {worker_id} assigned next case {next_case}")
                        # Small delay to prevent WebDriver interference
                        time.sleep(1)
                    else:
                        print(
                            f"🏁 Worker {worker_id} finished - no more cases in queue"
                        )

        # Verify all cases were processed
        missing_cases = set(cases_to_process) - completed_cases
        if missing_cases:
            print(f"⚠️ WARNING: Missing cases in batch {batch_number}: {missing_cases}")
            print(f"   Expected: {cases_to_process}")
            print(f"   Completed: {sorted(completed_cases)}")
            print(f"   Missing: {sorted(missing_cases)}")
        else:
            print(
                f"✅ SUCCESS: All {len(cases_to_process)} cases in batch {batch_number} were processed!"
            )

        # Final progress save (after retries)
        final_missing_cases = set(cases_to_process) - completed_cases
        # PROGRESS TRACKING COMPLETELY REMOVED - NO PROGRESS FILE SAVING

        # Retry missing cases if any
        if missing_cases:
            print(
                f"🔄 Retrying {len(missing_cases)} missing cases: {sorted(missing_cases)}"
            )
            retry_results = []
            for case_no in sorted(missing_cases):
                try:
                    print(f"🔄 Retrying case {case_no}...")
                    retry_scraper = IHCSeleniumScraper(
                        headless=True, fetch_details=True
                    )
                    if retry_scraper.start_driver():
                        if (
                            retry_scraper.navigate_to_case_status()
                            and retry_scraper.fill_search_form_simple(case_no)
                        ):
                            retry_cases = retry_scraper.scrape_results_table(
                                case_type_empty=True, case_no=case_no
                            )
                            if retry_cases:
                                # Add metadata
                                for case in retry_cases:
                                    case["SEARCH_CASE_NO"] = case_no
                                    case["WORKER_ID"] = "RETRY"
                                    case["SCRAPE_TIMESTAMP"] = (
                                        datetime.now().isoformat()
                                    )
                                    case["BATCH_NUMBER"] = batch_number
                                    case["RETRY_ATTEMPT"] = True

                                retry_results.extend(retry_cases)
                                completed_cases.add(case_no)
                                print(
                                    f"✅ Retry successful for case {case_no}: {len(retry_cases)} results"
                                )

                                # Save to database in real-time
                                for case_data in retry_cases:
                                    result = retry_scraper.db_saver.save_case(case_data)
                                    if result["status"] == "success":
                                        print(
                                            f"💾 RETRY: ✅ Case {case_data.get('CASE_NO')} saved to database"
                                        )
                                    else:
                                        print(
                                            f"❌ RETRY: Failed to save case {case_data.get('CASE_NO')}: {result['error']}"
                                        )
                            else:
                                print(f"⚠️ Retry failed for case {case_no}: No results")
                        else:
                            print(
                                f"❌ Retry failed for case {case_no}: Navigation/form filling failed"
                            )
                    else:
                        print(
                            f"❌ Retry failed for case {case_no}: WebDriver failed to start"
                        )
                    retry_scraper.stop_driver()
                except Exception as e:
                    print(f"❌ Retry error for case {case_no}: {e}")

            # Add retry results to total
            all_results.extend(retry_results)
            print(f"📊 Retry completed: {len(retry_results)} additional cases found")

        # All cases already saved to database in real-time
        total_duration = datetime.now() - start_time
        print(f"\n🎉 BATCH {batch_number} COMPLETED!")
        print(f"📊 Cases processed: {total_cases_processed}/{len(case_numbers)}")
        print(f"📋 Total cases found: {total_cases_found}")
        print(f"⏱️ Total duration: {total_duration.total_seconds() / 60:.1f} minutes")
        print(f"💾 All cases saved to database in real-time")
        
        # Show final progress summary
        print(f"\n📊 Final Progress Summary:")
        self.print_progress_summary()

        return all_results

    def run_multiple_batches(
        self, start_batch=1, end_batch=200, cases_per_batch=5, max_workers=3, 
        fetch_details=True, description="", resume=True
    ):
        """
        Run multiple batches sequentially with progress tracking and resume capability

        Args:
            start_batch: Starting batch number (default: 1)
            end_batch: Ending batch number (default: 200 for 1000 cases)
            cases_per_batch: Number of cases per batch (default: 5)
            max_workers: Number of parallel windows per batch (default: 3)
            fetch_details: Whether to fetch detailed case information (default: True)
            description: Description of the scraping session (default: "")
            resume: Whether to resume from previous session (default: True)
        """
        from datetime import datetime
        try:
            from .progress_tracker import progress_tracker
        except ImportError:
            import sys
            import os
            # PROGRESS TRACKING COMPLETELY REMOVED - NO IMPORTS

        print(f"🚀 Starting MULTIPLE BATCHES: {start_batch} to {end_batch}")
        print(f"📊 Configuration: {max_workers} workers, {cases_per_batch} cases per batch")
        print(f"🔍 Detailed fetching: {'Enabled' if fetch_details else 'Disabled'}")
        print(f"🔄 Resume capability: {'Enabled' if resume else 'Disabled'}")

        # Show initial progress summary
        if resume:
            self.print_progress_summary()

        all_batch_results = []
        start_time = datetime.now()

        # Process all batches
        remaining_batches = list(range(start_batch, end_batch + 1))
        print(f"📋 Processing {len(remaining_batches)} batches...")

        for batch_num in remaining_batches:
            # Check for shutdown request before processing each batch - IMMEDIATE STOP
            if SHUTDOWN_REQUESTED:
                print(f"\n🛑 Shutdown requested, stopping at batch {batch_num}")
                if resume:
                    print("💾 Progress saved - you can resume from this point later")
                return all_batch_results
                
            print(f"\n{'='*60}")
            print(f"🔄 Processing BATCH {batch_num}/{end_batch}")
            print(f"{'='*60}")

            try:
                batch_results = self.parallel_scrape_cases(
                    batch_number=batch_num,
                    cases_per_batch=cases_per_batch,
                    max_workers=max_workers,
                )

                if batch_results:
                    all_batch_results.extend(batch_results)
                    print(f"✅ Batch {batch_num} completed successfully - {len(batch_results)} cases")
                else:
                    print(f"⚠️ Batch {batch_num} completed with no results")

                # Small delay between batches
                time.sleep(2)

            except KeyboardInterrupt:
                print(f"\n⚠️ Scraping interrupted by user at batch {batch_num}")
                if resume:
                    print("💾 Progress saved - you can resume from this point later")
                break
                
            except Exception as e:
                print(f"❌ Batch {batch_num} failed: {e}")
                print(f"🔄 Continuing with next batch...")
                continue

        # Final completion summary
        print(f"\n🎉 ALL BATCHES COMPLETED!")

        # All results already saved to database in real-time
        total_duration = datetime.now() - start_time
        print(f"📊 Total cases found: {len(all_batch_results)}")
        print(f"⏱️ Total duration: {total_duration.total_seconds() / 60:.1f} minutes")
        
        # Show final progress summary
        if resume:
            print(f"\n📊 Final Progress Summary:")
            self.print_progress_summary()

        return all_batch_results

    def validate_current_page(self):
        """Validate that we're on the correct page and recover if not"""
        try:
            current_url = self.driver.current_url
            page_title = self.driver.title
            
            print(f"🔍 Validating current page: {page_title}")
            print(f"📍 Current URL: {current_url}")
            
            # Check if we're on the expected IHC case status page
            expected_indicators = [
                "Case Status",
                "Islamabad High Court", 
                "IHC",
                "case status",
                "txtCaseno",  # Case number input field
                "btnSearch",  # Search button
                "frmcsesrch"  # Case status form URL
            ]
            
            page_source = self.driver.page_source.lower()
            is_valid_page = any(indicator.lower() in page_source for indicator in expected_indicators)
            
            if not is_valid_page:
                # Check if we're actually on the case status page despite validation failure
                if "frmcsesrch" in current_url.lower():
                    print(f"✅ On case status page (URL check), validation passed")
                    return True
                
                print(f"⚠️ WARNING: Worker appears to be on wrong page!")
                print(f"   Title: {page_title}")
                print(f"   URL: {current_url}")
                print(f"   Attempting navigation recovery...")
                
                # Try to recover by navigating back to case status
                return self.recover_navigation()
            
            print(f"✅ Page validation passed - on correct IHC case status page")
            return True
            
        except Exception as e:
            print(f"❌ Error validating current page: {e}")
            return self.recover_navigation()

    def recover_navigation(self):
        """Recover from navigation issues by returning to case status page"""
        try:
            print(f"🔄 Attempting navigation recovery...")
            
            # Simple recovery: just refresh the page
            try:
                print(f"🔄 Attempting page refresh...")
                self.driver.refresh()
                time.sleep(5)
                
                if self.validate_current_page():
                    print(f"✅ Successfully recovered via page refresh")
                    return True
            except Exception as e:
                print(f"⚠️ Page refresh failed: {e}")
            
            print(f"❌ Navigation recovery failed")
            return False

        except Exception as e:
            print(f"❌ Error in navigation recovery: {e}")
            return False

    def check_for_unexpected_redirects(self):
        """Check for unexpected redirects and handle them"""
        try:
            current_url = self.driver.current_url
            page_title = self.driver.title
            
            # Check for common redirect scenarios (more specific to avoid false positives)
            redirect_indicators = [
                "login",
                "404",
                "not found",
                "access denied",
                "session expired",
                "timeout",
                "maintenance",
                "error page",
                "page not found",
                "server error"
            ]
            
            page_source_lower = self.driver.page_source.lower()
            title_lower = page_title.lower()
            url_lower = current_url.lower()
            
            # Check if we've been redirected to an unexpected page
            # But first, check if we're actually on the correct case status page
            if "frmcsesrch" in url_lower or "case status" in page_source_lower:
                # We're on the case status page, don't treat as redirect
                return True
            
            for indicator in redirect_indicators:
                if (indicator in title_lower or 
                    indicator in url_lower or 
                    indicator in page_source_lower):
                    
                    print(f"⚠️ DETECTED UNEXPECTED REDIRECT: {indicator}")
                    print(f"   Title: {page_title}")
                    print(f"   URL: {current_url}")
                    
                    # Attempt recovery
                    if self.recover_navigation():
                        return True
                    else:
                        print(f"❌ Failed to recover from redirect to {indicator}")
                        return False
            
            return True

        except Exception as e:
            print(f"❌ Error checking for redirects: {e}")
            return False

    def schedule_case_retry(self, case_no, delay_minutes=30):
        """
        Schedule a case for automatic retry after a specified delay
        
        Args:
            case_no: The case number to retry
            delay_minutes: Minutes to wait before retry (default: 30)
        """
        import threading
        import time
        
        def retry_case():
            print(f"⏰ Scheduled retry for case {case_no} in {delay_minutes} minutes...")
            time.sleep(delay_minutes * 60)  # Convert minutes to seconds
            print(f"🔄 Executing scheduled retry for case {case_no}")
            
            # Create a new scraper instance for the retry
            retry_scraper = IHCSeleniumScraper(headless=True, fetch_details=True)
            if retry_scraper.start_driver():
                try:
                    if (retry_scraper.navigate_to_case_status() and 
                        retry_scraper.fill_search_form_simple(case_no)):
                        cases = retry_scraper.scrape_results_table(
                            case_type_empty=True, case_no=case_no
                        )
                        if cases:
                            print(f"✅ Scheduled retry successful for case {case_no}: {len(cases)} results")
                            # Save results to database
                            for case_data in cases:
                                retry_scraper.db_saver.save_case(case_data)
                        else:
                            print(f"⚠️ Scheduled retry for case {case_no}: No results found")
                    else:
                        print(f"❌ Scheduled retry for case {case_no}: Navigation failed")
                except Exception as e:
                    print(f"❌ Scheduled retry for case {case_no} failed: {e}")
                finally:
                    retry_scraper.stop_driver()
            else:
                print(f"❌ Scheduled retry for case {case_no}: Failed to start driver")
        
        # Start retry thread
        retry_thread = threading.Thread(target=retry_case, daemon=True)
        retry_thread.start()
        print(f"📅 Case {case_no} scheduled for retry in {delay_minutes} minutes")

    def validate_case_completion(self, case_no):
        """
        Validate if a case is truly completed based on progress data
        
        Args:
            case_no: The case number to validate
            
        Returns:
            bool: True if case is completed, False if incomplete
        """
        if case_no not in self.progress_data:
            print(f"⚠️ Case {case_no}: No progress data available")
            return False
        
        progress = self.progress_data[str(case_no)]
        current_row = progress.get('current_row', 0)
        total_rows = progress.get('total_rows')
        
        if total_rows is None:
            print(f"⚠️ Case {case_no}: Total rows not determined yet")
            return False
        
        if total_rows > 0 and current_row < total_rows:
            print(f"⚠️ Case {case_no}: Incomplete ({current_row}/{total_rows} rows)")
            return False
        
        print(f"✅ Case {case_no}: Completed ({current_row}/{total_rows} rows)")
        return True

    def get_incomplete_cases(self):
        """
        Get list of cases that are incomplete and need retry
        
        Returns:
            list: List of case numbers that are incomplete
        """
        incomplete_cases = []
        
        for case_no, progress in self.progress_data.items():
            current_row = progress.get('current_row', 0)
            total_rows = progress.get('total_rows')
            
            if total_rows and total_rows > 0 and current_row < total_rows:
                incomplete_cases.append(int(case_no))
        
        return incomplete_cases

    def auto_retry_incomplete_cases(self, max_retries=3, delay_minutes=30):
        """
        Automatically retry all incomplete cases
        
        Args:
            max_retries: Maximum number of retry attempts per case
            delay_minutes: Minutes to wait between retries
        """
        incomplete_cases = self.get_incomplete_cases()
        
        if not incomplete_cases:
            print("✅ No incomplete cases found")
            return
        
        print(f"🔄 Found {len(incomplete_cases)} incomplete cases: {incomplete_cases}")
        
        for case_no in incomplete_cases:
            print(f"📅 Scheduling retry for case {case_no}")
            self.schedule_case_retry(case_no, delay_minutes)

    def schedule_case_retry(self, case_no, delay_minutes=30):
        """
        Schedule a case for automatic retry after a specified delay
        
        Args:
            case_no: The case number to retry
            delay_minutes: Minutes to wait before retry (default: 30)
        """
        import threading
        import time
        
        def retry_case():
            print(f"⏰ Scheduled retry for case {case_no} in {delay_minutes} minutes...")
            time.sleep(delay_minutes * 60)  # Convert minutes to seconds
            print(f"🔄 Executing scheduled retry for case {case_no}")
            
            # Create a new scraper instance for the retry
            retry_scraper = IHCSeleniumScraper(headless=True, fetch_details=True)
            if retry_scraper.start_driver():
                try:
                    if (retry_scraper.navigate_to_case_status() and 
                        retry_scraper.fill_search_form_simple(case_no)):
                        cases = retry_scraper.scrape_results_table(
                            case_type_empty=True, case_no=case_no
                        )
                        if cases:
                            print(f"✅ Scheduled retry successful for case {case_no}: {len(cases)} results")
                            # Save results to database
                            for case_data in cases:
                                retry_scraper.db_saver.save_case(case_data)
                        else:
                            print(f"⚠️ Scheduled retry for case {case_no}: No results found")
                    else:
                        print(f"❌ Scheduled retry for case {case_no}: Navigation failed")
                except Exception as e:
                    print(f"❌ Scheduled retry for case {case_no} failed: {e}")
                finally:
                    retry_scraper.stop_driver()
            else:
                print(f"❌ Scheduled retry for case {case_no}: Failed to start driver")
        
        # Start retry thread
        retry_thread = threading.Thread(target=retry_case, daemon=True)
        retry_thread.start()
        print(f"📅 Case {case_no} scheduled for retry in {delay_minutes} minutes")

    def validate_case_completion(self, case_no):
        """
        Validate if a case is truly completed based on progress data
        
        Args:
            case_no: The case number to validate
            
        Returns:
            bool: True if case is completed, False if incomplete
        """
        if case_no not in self.progress_data:
            print(f"⚠️ Case {case_no}: No progress data available")
            return False
        
        progress = self.progress_data[str(case_no)]
        current_row = progress.get('current_row', 0)
        total_rows = progress.get('total_rows')
        
        if total_rows is None:
            print(f"⚠️ Case {case_no}: Total rows not determined yet")
            return False
        
        if total_rows > 0 and current_row < total_rows:
            print(f"⚠️ Case {case_no}: Incomplete ({current_row}/{total_rows} rows)")
            return False
        
        print(f"✅ Case {case_no}: Completed ({current_row}/{total_rows} rows)")
        return True

    def get_incomplete_cases(self):
        """
        Get list of cases that are incomplete and need retry
        
        Returns:
            list: List of case numbers that are incomplete
        """
        incomplete_cases = []
        
        for case_no, progress in self.progress_data.items():
            current_row = progress.get('current_row', 0)
            total_rows = progress.get('total_rows')
            
            if total_rows and total_rows > 0 and current_row < total_rows:
                incomplete_cases.append(int(case_no))
        
        return incomplete_cases

    def auto_retry_incomplete_cases(self, max_retries=3, delay_minutes=30):
        """
        Automatically retry all incomplete cases
        
        Args:
            max_retries: Maximum number of retry attempts per case
            delay_minutes: Minutes to wait between retries
        """
        incomplete_cases = self.get_incomplete_cases()
        
        if not incomplete_cases:
            print("✅ No incomplete cases found")
            return
        
        print(f"🔄 Found {len(incomplete_cases)} incomplete cases: {incomplete_cases}")
        
        for case_no in incomplete_cases:
            print(f"📅 Scheduling retry for case {case_no}")
            self.schedule_case_retry(case_no, delay_minutes)

    def _safe_extract_with_retry(self, extraction_func, max_retries=3, retry_delay=2):
        """Safely execute extraction function with retry logic for stale elements"""
        for attempt in range(max_retries):
            try:
                # Update activity time before each attempt
                self._update_activity_time()
                
                result = extraction_func()
                if result is not None:
                    return result
                    
            except StaleElementReferenceException as e:
                print(f"⚠️ Stale element on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    print(f"⏳ Waiting {retry_delay}s before retry...")
                    time.sleep(retry_delay)
                    # Try to refresh the modal content
                    self._refresh_modal_content()
                else:
                    print(f"❌ Max retries reached for extraction")
                    return None
            except Exception as e:
                print(f"❌ Unexpected error during extraction: {e}")
                return None
        
        return None

    def _refresh_modal_content(self):
        """Refresh modal content to handle stale elements"""
        try:
            # Try to close and reopen the modal
            print("🔄 Attempting to refresh modal content...")
            
            # Close current modal
            self.close_case_detail_option_modal()
            time.sleep(1)
            
            # Try to reopen the modal (this would need to be called from the parent method)
            print("✅ Modal content refreshed")
            
        except Exception as e:
            print(f"⚠️ Error refreshing modal content: {e}")

    def _safe_find_elements_with_retry(self, driver, by, value, timeout=10, max_retries=3):
        """Safely find elements with retry logic for stale elements"""
        for attempt in range(max_retries):
            try:
                self._update_activity_time()
                elements = WebDriverWait(driver, timeout).until(
                    EC.presence_of_all_elements_located((by, value))
                )
                return elements
            except StaleElementReferenceException as e:
                print(f"⚠️ Stale element when finding {by}={value}, attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                else:
                    print(f"❌ Max retries reached for finding {by}={value}")
                    return []
            except TimeoutException as e:
                print(f"⚠️ Timeout finding {by}={value}")
                return []
        
        return []

    def _safe_get_text_with_retry(self, element, max_retries=3):
        """Safely get text from element with retry logic"""
        for attempt in range(max_retries):
            try:
                return element.text.strip()
            except StaleElementReferenceException as e:
                print(f"⚠️ Stale element when getting text, attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                else:
                    return ""
        
        return ""

    def _safe_click_with_retry(self, element, max_retries=3):
        """Safely click element with retry logic"""
        for attempt in range(max_retries):
            try:
                element.click()
                return True
            except StaleElementReferenceException as e:
                print(f"⚠️ Stale element when clicking, attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                else:
                    return False
        
        return False
