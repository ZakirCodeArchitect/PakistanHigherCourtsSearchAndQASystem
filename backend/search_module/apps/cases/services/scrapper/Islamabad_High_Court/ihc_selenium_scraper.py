import time
import random
import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys

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


class IHCSeleniumScraper:
    def __init__(self, headless=False):  # Changed default to False for testing
        self.base_url = "https://mis.ihc.gov.pk/index.aspx"
        self.driver = None
        self.headless = headless
        
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
            "Insurance Appeal"
        ]
        
        self.years = list(range(2010, 2026))  # From 2010 to 2025
        self.case_numbers = list(range(1, 1001))  # Case numbers 1-1000
        
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
            options.add_experimental_option('useAutomationExtension', False)
            
            # Set a realistic user agent
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
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
            temp_dir = tempfile.mkdtemp()
            options.add_argument(f"--user-data-dir={temp_dir}")
            options.add_argument(f"--data-path={temp_dir}")
            
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
                driver_path = ChromeDriverManager(chrome_type=ChromeType.GOOGLE).install()
                service = Service(driver_path)
                print(f"✅ ChromeDriver installed at: {driver_path}")
            except Exception as e1:
                print(f"⚠️ ChromeDriverManager failed: {e1}")
                
                # Method 2: Try to find existing ChromeDriver
                try:
                    import subprocess
                    result = subprocess.run(['where', 'chromedriver'], capture_output=True, text=True)
                    if result.returncode == 0:
                        driver_path = result.stdout.strip().split('\n')[0]
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
                        raise Exception(f"ChromeDriver installation failed: {e1}, {e2}, {e3}")
            
            # Initialize Chrome WebDriver
            if service:
                self.driver = webdriver.Chrome(service=service, options=options)
            else:
                raise Exception("No valid ChromeDriver service available")
            
            # Set longer timeouts
            self.driver.set_page_load_timeout(60)
            self.driver.implicitly_wait(20)
            
            # Explicitly set window size again after driver initialization
            self.driver.set_window_size(1920, 1080)
            
            # Execute CDP commands to modify navigator.webdriver flag
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                '''
            })
            
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
                EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'GrdB')]//h4[contains(text(), 'Case Status')]"))
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
                    EC.presence_of_element_located((By.XPATH, "//iframe[contains(@src, 'frmCaseStatus.a')]"))
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
                    EC.presence_of_element_located((By.NAME, "ctl00$ContentPlaceHolder1$ddlCaseType"))
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
                clear_button = self.driver.find_element(By.ID, "btnClear")
                clear_button.click()
                time.sleep(3)  # Wait for form to reset
                print("✅ Cleared all form fields")
            except Exception as e:
                print(f"❌ Could not find Clear button: {e}")
                return False
            
            # Step 2: Select institution (required)
            print("🏛️ Step 2: Selecting institution...")
            try:
                institution_select = Select(self.driver.find_element(By.ID, "ddlInst"))
                institution_select.select_by_value("1")  # Islamabad High Court
                time.sleep(3)  # Wait for dropdown to populate
                print("✅ Selected Islamabad High Court")
            except Exception as e:
                print(f"❌ Failed to select institution: {e}")
                return False
            
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

    def scrape_results_table(self, case_type_empty=False):
        """Scrape the results table and return case data"""
        try:
            print("🔍 Looking for results...")
            
            # If case type is empty, we expect 500+ results, so wait much longer
            if case_type_empty:
                print("⏳ Case type is empty - expecting 500+ results, waiting longer...")
                initial_wait = 30  # Wait 30 seconds initially for bulk data
                stability_check_interval = 10  # Check for stability every 10 seconds
                stability_threshold = 60  # Consider stable if no new data for 60 seconds
            else:
                initial_wait = 15   # Normal wait for filtered results
                stability_check_interval = 5   # Check for stability every 5 seconds
                stability_threshold = 30  # Consider stable if no new data for 30 seconds
            
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
                    (By.CSS_SELECTOR, "div.table table")
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
                    print(f"⏳ No table found yet, waiting... ({table_wait_time}/{max_table_wait}s)")
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
                    
                    print(f"📊 Found {current_row_count} table rows (was {last_row_count})")
                    
                    # Check if we have enough rows (50+)
                    if current_row_count >= 50:
                        print(f"🎯 SUCCESS! Found {current_row_count} rows (50+ required)")
                        stable_count += stability_check_interval
                        
                        # If we have 50+ rows and they've been stable, we're done
                        if stable_count >= stability_threshold:
                            print(f"✅ Data loading complete: {current_row_count} rows stable for {stable_count}s")
                            break
                        else:
                            print(f"⏳ Have 50+ rows but waiting for stability ({stable_count}/{stability_threshold}s)")
                    elif current_row_count > last_row_count:
                        print(f"🔄 Data still loading... {current_row_count - last_row_count} new rows detected")
                        last_row_count = current_row_count
                        stable_count = 0  # Reset stability counter
                    elif current_row_count == last_row_count:
                        stable_count += stability_check_interval
                        print(f"⏳ Waiting for more rows... ({stable_count}s without new rows)")
                        
                        # If we've been waiting too long without reaching 50 rows, something is wrong
                        if stable_count > 120:  # 2 minutes without progress
                            print(f"⚠️ Warning: Only {current_row_count} rows found after 2 minutes")
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
            
            # Phase 3: Change rows display to 100 and wait for more data
            print("🔍 Phase 3: Changing rows display to 100...")
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
                    (By.TAG_NAME, "select")
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
                                
                                print(f"📊 Found {current_count} table rows (target: 100+)")
                                
                                if current_count >= 100:
                                    print(f"🎯 SUCCESS! Found {current_count} rows (100+ required)")
                                    stable_count += stability_check_interval
                                    
                                    if stable_count >= stability_threshold:
                                        print(f"✅ 100 rows loading complete: {current_count} rows stable for {stable_count}s")
                                        break
                                    else:
                                        print(f"⏳ Have 100+ rows but waiting for stability ({stable_count}/{stability_threshold}s)")
                                elif current_count > new_row_count:
                                    print(f"🔄 More rows loading... {current_count - new_row_count} new rows detected")
                                    new_row_count = current_count
                                    stable_count = 0
                                else:
                                    stable_count += stability_check_interval
                                    print(f"⏳ Waiting for more rows... ({stable_count}s without new rows)")
                                    
                                    if stable_count > 120:  # 2 minutes without progress
                                        print(f"⚠️ Warning: Only {current_count} rows found after 2 minutes")
                                        print("⏳ Continuing to wait for more rows...")
                                        stable_count = 0
                                
                                time.sleep(stability_check_interval)
                                
                            except Exception as e:
                                print(f"⚠️ Error while monitoring 100 rows loading: {e}")
                                time.sleep(stability_check_interval)
                        
                        # Now process all pages with pagination
                        print("🔍 Phase 5: Processing all pages with pagination...")
                        all_cases = []
                        page_number = 1
                        total_processed = 0
                        
                        while True:  # Continue until no more pages
                            print(f"\n📄 Processing Page {page_number}...")
                            
                            # Get current page rows
                            current_rows = table.find_elements(By.TAG_NAME, "tr")
                            print(f"📊 Found {len(current_rows)} rows on current page")
                            
                            if len(current_rows) > 1:
                                page_cases = []
                                
                                # Process ALL rows on current page
                                for i, row in enumerate(current_rows, 1):
                                    try:
                                        cells = row.find_elements(By.TAG_NAME, "td")
                                        
                                        if len(cells) >= 7:
                                            case_data = {
                                                'SR': cells[0].text.strip() if len(cells) > 0 else '',
                                                'INSTITUTION': cells[1].text.strip() if len(cells) > 1 else '',
                                                'CASE_NO': cells[2].text.strip() if len(cells) > 2 else '',
                                                'CASE_TITLE': cells[3].text.strip() if len(cells) > 3 else '',
                                                'BENCH': cells[4].text.strip() if len(cells) > 4 else '',
                                                'HEARING_DATE': cells[5].text.strip() if len(cells) > 5 else '',
                                                'STATUS': cells[6].text.strip() if len(cells) > 6 else '',
                                                'HISTORY': cells[7].text.strip() if len(cells) > 7 else '',
                                                'DETAILS': cells[8].text.strip() if len(cells) > 8 else ''
                                            }
                                            
                                            # Only add if we have meaningful data
                                            if case_data['SR'] and case_data['SR'].isdigit() and case_data['CASE_NO']:
                                                page_cases.append(case_data)
                                                print(f"✅ Page {page_number}, Row {i}: Added case with SR={case_data['SR']}")
                                            else:
                                                print(f"⚠️ Page {page_number}, Row {i}: Skipped (SR='{case_data.get('SR', 'N/A')}', CASE_NO='{case_data.get('CASE_NO', 'N/A')}')")
                                        else:
                                            print(f"⚠️ Page {page_number}, Row {i}: Not enough cells ({len(cells)})")
                                            
                                    except Exception as e:
                                        print(f"⚠️ Error processing page {page_number}, row {i}: {e}")
                                        continue
                                
                                # Add page cases to total
                                all_cases.extend(page_cases)
                                total_processed += len(page_cases)
                                print(f"📊 Page {page_number}: Added {len(page_cases)} cases (Total: {total_processed})")
                                
                                # Check if this is the last page (less than 100 entries means last page)
                                if len(page_cases) < 100:
                                    print(f"🏁 Last page detected! Only {len(page_cases)} entries found (less than 100)")
                                    print(f"✅ All data fetched successfully. Total: {total_processed} cases")
                                    break
                                
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
                                    (By.CSS_SELECTOR, "input[value='Next']")
                                ]
                                
                                for selector in next_button_selectors:
                                    try:
                                        next_button = WebDriverWait(self.driver, 3).until(
                                            EC.element_to_be_clickable(selector)
                                        )
                                        print(f"✅ Found Next button with selector: {selector}")
                                        break
                                    except TimeoutException:
                                        continue
                                
                                if next_button and next_button.is_enabled():
                                    print(f"⏭️ Clicking Next button to go to page {page_number + 1}...")
                                    try:
                                        # Scroll to the Next button to make it visible
                                        self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                                        time.sleep(2)  # Wait for scroll
                                        
                                        next_button.click()
                                        print(f"✅ Clicked Next button")
                                        
                                        # Wait for new page to load
                                        print("⏳ Waiting for next page to load...")
                                        time.sleep(5)  # Wait for page load
                                        
                                        # Wait for table to reload
                                        table_reload_wait = 0
                                        while table_reload_wait < 60:  # Wait up to 60 seconds for table reload
                                            try:
                                                new_rows = table.find_elements(By.TAG_NAME, "tr")
                                                if len(new_rows) > 1:
                                                    print(f"✅ New page loaded with {len(new_rows)} rows")
                                                    break
                                                else:
                                                    print(f"⏳ Waiting for table to reload... ({table_reload_wait}/60s)")
                                                    time.sleep(2)
                                                    table_reload_wait += 2
                                            except Exception as e:
                                                print(f"⚠️ Error checking table reload: {e}")
                                                time.sleep(2)
                                                table_reload_wait += 2
                                        
                                        page_number += 1
                                        continue  # Process next page
                                        
                                    except Exception as e:
                                        print(f"❌ Error clicking Next button: {e}")
                                        break
                                else:
                                    print("🏁 No Next button found or it's disabled - reached last page")
                                    break
                            else:
                                print("❌ No data rows found on current page")
                                break
                        
                        print(f"📊 Total cases processed: {len(all_cases)}")
                        
                        if case_type_empty and len(all_cases) > 50:
                            print(f"🎯 SUCCESS! Found {len(all_cases)} cases with empty case type (all pages)")
                        
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

    def search_case(self, case_no=None, year=None, case_type=None, search_by_case_number=True):
        """Search for cases with the given parameters"""
        try:
            # Navigate to case status page
            if not self.navigate_to_case_status():
                return None
            
            # Fill and submit the search form
            if not self.fill_search_form(case_no, year, case_type, search_by_case_number):
                return None
            
            # Determine if case type is empty for bulk data handling
            case_type_empty = (case_type is None)
            
            # Scrape the results
            all_cases_data = self.scrape_results_table(case_type_empty=case_type_empty)
            
            if all_cases_data:
                print(f"📊 Found {len(all_cases_data)} cases for search criteria")
                # Show first few cases for verification
                for i, case in enumerate(all_cases_data[:3]):  # Show first 3 cases
                    print(f"  Case {i+1}: {case.get('CASE_NO', 'N/A')} - {case.get('CASE_TITLE', 'N/A')[:50]}...")
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
                    return self.search_case(case_no, year, case_type, search_by_case_number)
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
        print("\n📋 Strategy 1: Searching by case number ONLY (no case type) for maximum coverage...")
        print("💡 Discovery: Searching without case type gives 500+ results vs 16-21 with case type")
        
        for year in self.years:
            for case_no in range(1, 101):  # Search first 100 case numbers per year
                total_searches += 1
                print(f"\n🔍 Search {total_searches}: Case Number: {case_no}, Year: {year} (NO CASE TYPE)")
                
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
                    cases = self.search_case(case_no=case_no, year=year, case_type=None, search_by_case_number=True)
                    if cases:
                        successful_searches += 1
                        all_cases.extend(cases)
                        print(f"✅ Found {len(cases)} cases for case {case_no}/{year} (no case type)")
                        
                        # Save intermediate results
                        self.save_cases_to_file(all_cases, f"cases_metadata/Islamabad_High_Court/comprehensive_search.json")
                        
                        # Limit cases per filter to avoid overwhelming
                        if len(cases) > max_cases_per_filter:
                            print(f"⚠️ Limiting to {max_cases_per_filter} cases per filter")
                            all_cases = all_cases[:-len(cases)] + cases[:max_cases_per_filter]
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
        print("\n📋 Strategy 2: Searching by case type with case numbers for recent years (specific filtering)...")
        recent_years = [2023, 2024, 2025]
        for case_type in self.case_types:
            for year in recent_years:
                for case_no in range(1, 51):  # Search first 50 case numbers per case type/year
                    total_searches += 1
                    print(f"\n🔍 Search {total_searches}: Case Type: {case_type}, Case Number: {case_no}, Year: {year}")
                    
                    # Check if driver is still valid
                    try:
                        self.driver.current_url
                    except:
                        print("🔄 Driver session expired, restarting...")
                        if not self.restart_driver():
                            print("❌ Failed to restart driver, stopping search")
                            break
                    
                    try:
                        cases = self.search_case(case_no=case_no, year=year, case_type=case_type, search_by_case_number=True)
                        if cases:
                            successful_searches += 1
                            all_cases.extend(cases)
                            print(f"✅ Found {len(cases)} cases for {case_type} case {case_no}/{year}")
                            
                            # Save intermediate results
                            self.save_cases_to_file(all_cases, f"cases_metadata/Islamabad_High_Court/comprehensive_search.json")
                        else:
                            print(f"❌ No cases found for {case_type} case {case_no}/{year}")
                            
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
                    with open(filename, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                except json.JSONDecodeError:
                    print(f"⚠️ Warning: {filename} contains invalid JSON, starting fresh")
                    existing_data = []
            
            # Add new cases to existing data
            all_cases = existing_data + cases
            
            # Save to JSON file
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(all_cases, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Saved {len(cases)} cases to {filename}")
            
        except Exception as e:
            print(f"❌ Error saving to {filename}: {e}")

    def test_case_type_vs_no_case_type(self, case_no=1, year=2025):
        """Test the difference between searching with and without case type"""
        print(f"🧪 Testing case type vs no case type for case {case_no}/{year}")
        
        # Test 1: Search WITH case type
        print(f"\n📋 Test 1: Searching WITH case type 'Writ Petition'")
        try:
            cases_with_type = self.search_case(case_no=case_no, year=year, case_type="Writ Petition", search_by_case_number=True)
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
            cases_without_type = self.search_case(case_no=case_no, year=year, case_type=None, search_by_case_number=True)
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
                print(f"🎯 CONFIRMED: Leaving case type empty gives {ratio:.1f}x more results!")
            else:
                print(f"⚠️ Unexpected: Only {ratio:.1f}x difference")
        
        return cases_with_type, cases_without_type

    def test_bulk_data_loading(self, case_no=1, year=2025):
        """Test bulk data loading with empty case type"""
        print(f"🧪 Testing bulk data loading for case {case_no}/{year} with empty case type")
        print("⏳ This will take longer as it loads 500+ results...")
        
        try:
            # Search WITHOUT case type for bulk data
            cases = self.search_case(case_no=case_no, year=year, case_type=None, search_by_case_number=True)
            if cases:
                print(f"🎯 SUCCESS! Found {len(cases)} cases with bulk data loading")
                print(f"📊 This confirms the longer wait times work for 500+ results")
                
                # Show sample of results
                print(f"\n📋 Sample results:")
                for i, case in enumerate(cases[:5]):
                    print(f"  {i+1}. {case.get('CASE_NO', 'N/A')} - {case.get('CASE_TITLE', 'N/A')[:60]}...")
                if len(cases) > 5:
                    print(f"  ... and {len(cases) - 5} more cases")
                
                return cases
            else:
                print(f"❌ No cases found with bulk data loading")
                return None
                
        except Exception as e:
            print(f"❌ Error in bulk data test: {e}")
            return None

    def parallel_scrape_cases(self, batch_number=1, cases_per_batch=5, max_workers=3):
        """
        Scrape cases in parallel with individual file saving
        
        Args:
            batch_number: Which batch to process (1 = cases 1-5, 2 = cases 6-10, etc.)
            cases_per_batch: Number of cases per batch (default: 5)
            max_workers: Number of parallel browser windows (default: 3 - reduced to avoid conflicts)
        """
        import concurrent.futures
        import threading
        from datetime import datetime
        
        # Calculate case numbers for this batch
        start_case = ((batch_number - 1) * cases_per_batch) + 1
        end_case = batch_number * cases_per_batch
        
        print(f"🚀 Starting BATCH {batch_number}: Cases {start_case}-{end_case}")
        print(f"📊 Configuration: {max_workers} parallel windows, {cases_per_batch} cases per batch")
        
        # Create directory for individual case files
        cases_dir = "cases_metadata/Islamabad_High_Court/individual_cases"
        os.makedirs(cases_dir, exist_ok=True)
        
        # Create progress tracking file
        progress_file = f"cases_metadata/Islamabad_High_Court/batch_{batch_number}_progress.json"
        
        # Load existing progress for this batch
        completed_cases = set()
        if os.path.exists(progress_file):
            try:
                with open(progress_file, 'r') as f:
                    progress_data = json.load(f)
                    completed_cases = set(progress_data.get('completed_cases', []))
                    print(f"📋 Found {len(completed_cases)} previously completed cases in batch {batch_number}")
            except:
                pass
        
        # Create case numbers list for this batch
        case_numbers = list(range(start_case, end_case + 1))
        print(f"📦 Processing cases: {case_numbers}")
        
        # Thread-safe counters
        lock = threading.Lock()
        total_cases_found = 0
        total_cases_processed = 0
        
        def scrape_single_case(case_no, worker_id):
            """Scrape a single case number using a dedicated WebDriver instance"""
            nonlocal total_cases_found, total_cases_processed
            
            # Skip if already completed
            with lock:
                if case_no in completed_cases:
                    print(f"⏭️ Worker {worker_id}: Case {case_no} already completed, skipping")
                    return None
            
            # Create dedicated scraper for this worker with retry mechanism
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    worker_scraper = IHCSeleniumScraper(headless=True)
                    if worker_scraper.start_driver():
                        print(f"✅ Worker {worker_id}: WebDriver started successfully on attempt {attempt + 1}")
                        break
                    else:
                        print(f"⚠️ Worker {worker_id}: WebDriver start failed on attempt {attempt + 1}")
                        worker_scraper.stop_driver()
                        if attempt < max_retries - 1:
                            time.sleep(2)  # Wait before retry
                        continue
                except Exception as e:
                    print(f"⚠️ Worker {worker_id}: WebDriver error on attempt {attempt + 1}: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(2)  # Wait before retry
                    continue
            else:
                print(f"❌ Worker {worker_id}: Failed to start WebDriver after {max_retries} attempts for case {case_no}")
                return None
            
            case_results = []
            case_start_time = datetime.now()
            
            try:
                print(f"🔍 Worker {worker_id}: Starting case {case_no}")
                
                # Navigate and search
                if not worker_scraper.navigate_to_case_status():
                    print(f"❌ Worker {worker_id}: Failed to navigate for case {case_no}")
                    return None
                
                if not worker_scraper.fill_search_form_simple(case_no):
                    print(f"❌ Worker {worker_id}: Failed to fill form for case {case_no}")
                    return None
                
                # Scrape results
                cases = worker_scraper.scrape_results_table(case_type_empty=True)
                
                if cases:
                    # Add metadata
                    for case in cases:
                        case['SEARCH_CASE_NO'] = case_no
                        case['WORKER_ID'] = worker_id
                        case['SCRAPE_TIMESTAMP'] = datetime.now().isoformat()
                        case['BATCH_NUMBER'] = batch_number
                    
                    case_results.extend(cases)
                    
                    with lock:
                        total_cases_found += len(cases)
                        total_cases_processed += 1
                        completed_cases.add(case_no)
                    
                    print(f"✅ Worker {worker_id}: Case {case_no} → {len(cases)} results")
                    
                    # Save to individual case file immediately
                    case_filename = f"{cases_dir}/case{case_no}.json"
                    worker_scraper.save_cases_to_file(cases, case_filename)
                    print(f"💾 Worker {worker_id}: Saved case {case_no} to {case_filename}")
                    
                else:
                    print(f"⚠️ Worker {worker_id}: Case {case_no} → No results")
                    with lock:
                        completed_cases.add(case_no)
                
                # Save progress for this case
                with open(progress_file, 'w') as f:
                    json.dump({
                        'batch_number': batch_number,
                        'completed_cases': list(completed_cases),
                        'total_cases_found': total_cases_found,
                        'last_updated': datetime.now().isoformat(),
                        'current_case': case_no
                    }, f, indent=2)
                
                case_duration = datetime.now() - case_start_time
                print(f"✅ Worker {worker_id}: Case {case_no} completed in {case_duration.total_seconds():.1f}s")
                
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
        
        # Create a queue of cases to process
        case_queue = case_numbers.copy()
        completed_futures = []
        
        print(f"📋 Case distribution strategy:")
        print(f"   - Total cases in batch: {len(case_numbers)}")
        print(f"   - Max workers: {max_workers}")
        print(f"   - Cases to process: {case_numbers}")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit initial batch of cases (one per worker)
            active_futures = {}
            for worker_id in range(min(max_workers, len(case_queue))):
                if case_queue:
                    case_no = case_queue.pop(0)
                    future = executor.submit(scrape_single_case, case_no, worker_id)
                    active_futures[future] = case_no
                    print(f"🚀 Worker {worker_id} assigned case {case_no}")
            
            # Process cases as they complete and assign new ones
            while active_futures:
                # Wait for any future to complete
                done, not_done = concurrent.futures.wait(
                    active_futures.keys(), 
                    return_when=concurrent.futures.FIRST_COMPLETED
                )
                
                # Process completed futures
                for future in done:
                    case_no = active_futures[future]
                    worker_id = None
                    
                    # Find which worker completed this case
                    for f, c in active_futures.items():
                        if c == case_no:
                            # Extract worker_id from the future's function call
                            worker_id = list(active_futures.keys()).index(f)
                            break
                    
                    try:
                        case_results = future.result()
                        if case_results:
                            all_results.extend(case_results)
                            print(f"✅ Worker {worker_id}: Case {case_no} completed with {len(case_results)} results")
                        else:
                            print(f"⚠️ Worker {worker_id}: Case {case_no} completed with no results")
                            
                    except Exception as e:
                        print(f"❌ Worker {worker_id}: Case {case_no} failed: {e}")
                    
                    # Remove completed future
                    del active_futures[future]
                    completed_futures.append(future)
                    
                    # Assign next case to this worker if available
                    if case_queue:
                        next_case = case_queue.pop(0)
                        new_future = executor.submit(scrape_single_case, next_case, worker_id)
                        active_futures[new_future] = next_case
                        print(f"🔄 Worker {worker_id} assigned next case {next_case}")
                    else:
                        print(f"🏁 Worker {worker_id} finished - no more cases in queue")
        
        # Verify all cases were processed
        missing_cases = set(case_numbers) - completed_cases
        if missing_cases:
            print(f"⚠️ WARNING: Missing cases in batch {batch_number}: {missing_cases}")
            print(f"   Expected: {case_numbers}")
            print(f"   Completed: {sorted(completed_cases)}")
            print(f"   Missing: {sorted(missing_cases)}")
        else:
            print(f"✅ SUCCESS: All {len(case_numbers)} cases in batch {batch_number} were processed!")
        
        # Final progress save (after retries)
        final_missing_cases = set(case_numbers) - completed_cases
        with open(progress_file, 'w') as f:
            json.dump({
                'batch_number': batch_number,
                'completed_cases': list(completed_cases),
                'total_cases_found': total_cases_found,
                'last_updated': datetime.now().isoformat(),
                'status': 'completed',
                'missing_cases': list(final_missing_cases),
                'expected_cases': case_numbers,
                'retry_attempted': len(missing_cases) > 0 if 'missing_cases' in locals() else False
            }, f, indent=2)
        
        # Retry missing cases if any
        if missing_cases:
            print(f"🔄 Retrying {len(missing_cases)} missing cases: {sorted(missing_cases)}")
            retry_results = []
            for case_no in sorted(missing_cases):
                try:
                    print(f"🔄 Retrying case {case_no}...")
                    retry_scraper = IHCSeleniumScraper(headless=True)
                    if retry_scraper.start_driver():
                        if retry_scraper.navigate_to_case_status() and retry_scraper.fill_search_form_simple(case_no):
                            retry_cases = retry_scraper.scrape_results_table(case_type_empty=True)
                            if retry_cases:
                                # Add metadata
                                for case in retry_cases:
                                    case['SEARCH_CASE_NO'] = case_no
                                    case['WORKER_ID'] = 'RETRY'
                                    case['SCRAPE_TIMESTAMP'] = datetime.now().isoformat()
                                    case['BATCH_NUMBER'] = batch_number
                                    case['RETRY_ATTEMPT'] = True
                                
                                retry_results.extend(retry_cases)
                                completed_cases.add(case_no)
                                print(f"✅ Retry successful for case {case_no}: {len(retry_cases)} results")
                                
                                # Save individual case file
                                case_filename = f"{cases_dir}/case{case_no}.json"
                                retry_scraper.save_cases_to_file(retry_cases, case_filename)
                            else:
                                print(f"⚠️ Retry failed for case {case_no}: No results")
                        else:
                            print(f"❌ Retry failed for case {case_no}: Navigation/form filling failed")
                    else:
                        print(f"❌ Retry failed for case {case_no}: WebDriver failed to start")
                    retry_scraper.stop_driver()
                except Exception as e:
                    print(f"❌ Retry error for case {case_no}: {e}")
            
            # Add retry results to total
            all_results.extend(retry_results)
            print(f"📊 Retry completed: {len(retry_results)} additional cases found")
        
        # Save batch results
        batch_filename = f"cases_metadata/Islamabad_High_Court/batch_{batch_number}_results.json"
        self.save_cases_to_file(all_results, batch_filename)
        
        total_duration = datetime.now() - start_time
        print(f"\n🎉 BATCH {batch_number} COMPLETED!")
        print(f"📊 Cases processed: {total_cases_processed}/{len(case_numbers)}")
        print(f"📋 Total cases found: {total_cases_found}")
        print(f"⏱️ Total duration: {total_duration.total_seconds() / 60:.1f} minutes")
        print(f"💾 Individual files saved in: {cases_dir}/")
        print(f"💾 Batch results saved to: {batch_filename}")
        
        return all_results

    def run_multiple_batches(self, start_batch=1, end_batch=200, cases_per_batch=5, max_workers=3):
        """
        Run multiple batches sequentially
        
        Args:
            start_batch: Starting batch number (default: 1)
            end_batch: Ending batch number (default: 200 for 1000 cases)
            cases_per_batch: Number of cases per batch (default: 5)
            max_workers: Number of parallel windows per batch (default: 5)
        """
        from datetime import datetime
        
        print(f"🚀 Starting MULTIPLE BATCHES: {start_batch} to {end_batch}")
        print(f"📊 Total cases: {(end_batch - start_batch + 1) * cases_per_batch}")
        print(f"⏱️ Estimated time: ~{((end_batch - start_batch + 1) * 10) // 60} minutes")
        
        all_batch_results = []
        start_time = datetime.now()
        
        for batch_num in range(start_batch, end_batch + 1):
            print(f"\n{'='*60}")
            print(f"🔄 Processing BATCH {batch_num}/{end_batch}")
            print(f"{'='*60}")
            
            try:
                batch_results = self.parallel_scrape_cases(
                    batch_number=batch_num,
                    cases_per_batch=cases_per_batch,
                    max_workers=max_workers
                )
                
                if batch_results:
                    all_batch_results.extend(batch_results)
                    print(f"✅ Batch {batch_num} completed successfully")
                else:
                    print(f"⚠️ Batch {batch_num} completed with no results")
                
                # Small delay between batches
                time.sleep(2)
                
            except Exception as e:
                print(f"❌ Batch {batch_num} failed: {e}")
                print(f"🔄 Continuing with next batch...")
                continue
        
        # Save all results
        final_filename = f"cases_metadata/Islamabad_High_Court/all_batches_{start_batch}_{end_batch}.json"
        self.save_cases_to_file(all_batch_results, final_filename)
        
        total_duration = datetime.now() - start_time
        print(f"\n🎉 ALL BATCHES COMPLETED!")
        print(f"📊 Total cases found: {len(all_batch_results)}")
        print(f"⏱️ Total duration: {total_duration.total_seconds() / 60:.1f} minutes")
        print(f"💾 Final results saved to: {final_filename}")
        
        return all_batch_results

def run_test_mode(headless=False):
    """Run a test to verify the case type vs no case type discovery"""
    print("🧪 Starting Test Mode to verify case type discovery...")
    
    scraper = IHCSeleniumScraper(headless=headless)
    if not scraper.start_driver():
        return
        
    print("✅ WebDriver started successfully")
    
    try:
        # Test the discovery
        cases_with_type, cases_without_type = scraper.test_case_type_vs_no_case_type(case_no=1, year=2025)
        
        if cases_with_type and cases_without_type:
            print(f"\n🎯 Test completed successfully!")
            print(f"📊 Results confirm the discovery:")
            print(f"   - With case type: {len(cases_with_type)} cases")
            print(f"   - Without case type: {len(cases_without_type)} cases")
            print(f"   - Improvement: {len(cases_without_type)/len(cases_with_type):.1f}x more results")
        else:
            print(f"\n⚠️ Test completed but results were inconclusive")
        
        # Test bulk data loading
        print(f"\n🧪 Testing bulk data loading...")
        bulk_cases = scraper.test_bulk_data_loading(case_no=1, year=2025)
        
        if bulk_cases and len(bulk_cases) > 50:
            print(f"🎯 Bulk data test successful! Found {len(bulk_cases)} cases")
            print(f"✅ Longer wait times are working correctly for 500+ results")
        else:
            print(f"⚠️ Bulk data test may need adjustment")
            
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
    finally:
        scraper.stop_driver()

def run_comprehensive_scraper(headless=False):
    """Run the comprehensive scraper with all filter combinations"""
    print("🚀 Starting Comprehensive IHC Selenium Scraper")
    print("🔍 This will systematically apply all possible filter combinations")
    print("📋 Case Types:", len(IHCSeleniumScraper().case_types))
    print("📅 Years:", len(IHCSeleniumScraper().years))
    print("🔢 Case Numbers:", len(IHCSeleniumScraper().case_numbers))
    
    scraper = IHCSeleniumScraper(headless=headless)
    if not scraper.start_driver():
        return
        
    print("✅ WebDriver started successfully")
    
    try:
        # Run comprehensive search
        all_cases = scraper.comprehensive_search()
        
        if all_cases:
            print(f"\n✅ SUCCESS! Collected {len(all_cases)} total cases")
            
            # Save final results
            scraper.save_cases_to_file(all_cases, "cases_metadata/Islamabad_High_Court/comprehensive_search_final.json")
            
            # Also save to the original file for compatibility
            scraper.save_cases_to_file(all_cases, "ihc_cases_2023.json")
            
        else:
            print("\n❌ NO DATA COLLECTED!")
            
    except KeyboardInterrupt:
        print("\n⚠️ Scraping interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during comprehensive search: {e}")
    finally:
        scraper.stop_driver()

def run_selenium_scraper(start_case_no, end_case_no, year, case_type, headless=False):  # Changed default to False
    """Run the scraper for a range of case numbers"""
    print(f"🚀 Starting IHC Selenium Scraper for cases {start_case_no}-{end_case_no} from year {year}")
    print(f"🔍 Case Type: {case_type}")
    print(f"👻 Headless Mode: {headless}")
    
    scraper = IHCSeleniumScraper(headless=headless)
    if not scraper.start_driver():
        return
        
    print("✅ WebDriver started successfully")
    
    cases = []
    try:
        for case_no in range(start_case_no, end_case_no + 1):
            print(f"\n🔍 Processing case {case_no}/{year}...")
            all_cases_data = scraper.search_case(case_no, year, case_type)
            
            if all_cases_data:
                print(f"✅ Found {len(all_cases_data)} cases for case number {case_no}")
                # Add all cases to the results
                cases.extend(all_cases_data)
                print(f"📊 Total cases collected so far: {len(cases)}")
            else:
                print(f"❌ NO REAL DATA found for case {case_no}/{year}")
            
            # Close the case status tab and switch back to main window before next iteration
            try:
                if len(scraper.driver.window_handles) > 1:
                    scraper.driver.close()  # Close the case status tab
                    scraper.driver.switch_to.window(scraper.driver.window_handles[0])  # Switch back to main window
                else:
                    # If no new window was opened, switch back to default content (in case we're in an iframe)
                    scraper.driver.switch_to.default_content()
            except:
                pass
            
            # Random delay between requests to appear more human-like
            time.sleep(random.uniform(3, 5))
            
    except KeyboardInterrupt:
        print("\n⚠️ Scraping interrupted by user")
    finally:
        scraper.stop_driver()
        
    if not cases:
        print("\n❌ NO DATA COLLECTED!")
        print("   The website might be down or the search returned no results.")
    else:
        print(f"\n✅ SUCCESS! Collected {len(cases)} cases")
        
        # Save data to JSON file
        output_file = "ihc_cases_2023.json"
        try:
            # Load existing data if file exists
            existing_data = []
            if os.path.exists(output_file):
                with open(output_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                print(f"📁 Loaded {len(existing_data)} existing cases from {output_file}")
            
            # Add new cases to existing data
            all_cases = existing_data + cases
            print(f"📊 Total cases to save: {len(all_cases)}")
            
            # Save to JSON file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_cases, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Successfully saved {len(cases)} new cases to {output_file}")
            print(f"📁 Total cases in file: {len(all_cases)}")
            
        except Exception as e:
            print(f"❌ Error saving data to {output_file}: {e}")
    
    return cases

def run_simple_test(headless=False):
    """Run the scraper in simple test mode - just case number = 1"""
    try:
        print("🧪 Starting IHC Selenium Scraper in SIMPLE TEST MODE")
        print("📋 Simple approach: Reset form → Set case number = 1 → Search → Wait for data → Fetch")
        
        scraper = IHCSeleniumScraper(headless=headless)
        
        if not scraper.start_driver():
            print("❌ Failed to start WebDriver")
            return
        
        # Step 1: Navigate to case status page
        print("\n🔍 Step 1: Navigating to case status page...")
        if not scraper.navigate_to_case_status():
            print("❌ Failed to navigate to case status")
            scraper.stop_driver()
            return
        
        # Step 2: Fill form with simple approach
        print("\n📝 Step 2: Filling search form (simple mode)...")
        if not scraper.fill_search_form_simple():
            print("❌ Failed to fill search form")
            scraper.stop_driver()
            return
        
        # Step 3: Wait for data to load completely
        print("\n⏳ Step 3: Waiting for complete data to load...")
        cases = scraper.scrape_results_table(case_type_empty=True)
        
        # Step 4: Process results
        if cases:
            print(f"\n✅ SUCCESS! Found {len(cases)} cases")
            print("📊 First 3 cases:")
            for i, case in enumerate(cases[:3]):
                print(f"  {i+1}. {case.get('CASE_NO', 'N/A')} - {case.get('CASE_TITLE', 'N/A')[:50]}...")
            
            # Save results
            scraper.save_cases_to_file(cases, "cases_metadata/Islamabad_High_Court/ihc_caseno_1.json")
            print(f"💾 Saved {len(cases)} cases to ihc_caseno_1.json")
        else:
            print("❌ No cases found")
        
        scraper.stop_driver()
        
    except Exception as e:
        print(f"❌ Simple test error: {e}")
        if 'scraper' in locals():
            scraper.stop_driver()

def run_single_batch(batch_number=1, cases_per_batch=5, max_workers=3):
    """Run a single batch of cases"""
    try:
        print(f"🚀 Starting SINGLE BATCH {batch_number}")
        print(f"📊 Configuration: {max_workers} workers, {cases_per_batch} cases per batch")
        
        scraper = IHCSeleniumScraper(headless=True)
        results = scraper.parallel_scrape_cases(
            batch_number=batch_number,
            cases_per_batch=cases_per_batch,
            max_workers=max_workers
        )
        
        print(f"✅ Batch {batch_number} completed! Found {len(results)} total cases")
        return results
        
    except Exception as e:
        print(f"❌ Batch {batch_number} error: {e}")
        return None

def run_multiple_batches(start_batch=1, end_batch=200, cases_per_batch=5, max_workers=3):
    """Run multiple batches sequentially"""
    try:
        print(f"🚀 Starting MULTIPLE BATCHES: {start_batch} to {end_batch}")
        print(f"📊 Configuration: {max_workers} workers, {cases_per_batch} cases per batch")
        
        scraper = IHCSeleniumScraper(headless=True)
        results = scraper.run_multiple_batches(
            start_batch=start_batch,
            end_batch=end_batch,
            cases_per_batch=cases_per_batch,
            max_workers=max_workers
        )
        
        print(f"✅ All batches completed! Found {len(results)} total cases")
        return results
        
    except Exception as e:
        print(f"❌ Multiple batches error: {e}")
        return None

if __name__ == "__main__":
    # ========================================
    # 🚀 BATCH-BASED SCRAPING SYSTEM
    # ========================================
    
    # Option 1: Run a single batch (recommended for testing)
    # Batch 1 = Cases 1-5, Batch 2 = Cases 6-10, etc.
    run_single_batch(batch_number=2, cases_per_batch=5, max_workers=3)
    
    # Option 2: Run multiple batches
    # run_multiple_batches(start_batch=1, end_batch=10, cases_per_batch=5, max_workers=3)
    
    # Option 3: Run all 1000 cases (200 batches of 5 cases each)
    # run_multiple_batches(start_batch=1, end_batch=200, cases_per_batch=5, max_workers=3)
    
    # Option 4: Simple test (single case)
    # run_simple_test(headless=True)