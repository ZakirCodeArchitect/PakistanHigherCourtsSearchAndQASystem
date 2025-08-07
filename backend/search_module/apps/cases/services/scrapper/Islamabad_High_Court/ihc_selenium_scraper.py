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
            
            # Initialize Chrome WebDriver with ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            
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
        """Simple form filling: reset form, set case number = 1, search"""
        try:
            print("📝 Filling search form (SIMPLE MODE)...")
            
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
            
            # Step 3: Enter case number = 1
            print("🔢 Step 3: Entering case number = 1...")
            try:
                case_input = self.driver.find_element(By.ID, "txtCaseno")
                case_input.clear()
                case_input.send_keys("1")
                print("✅ Entered case number: 1")
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
            
            # Phase 3: Process the fully loaded data
            print("🔍 Phase 3: Processing fully loaded data...")
            try:
                # Get the final rows after data is stable
                final_rows = table.find_elements(By.TAG_NAME, "tr")
                print(f"📊 Processing {len(final_rows)} total rows")
                
                if len(final_rows) > 1:  # More than just header
                    cases = []
                    
                    # Process ALL rows to find the actual data (don't skip any rows)
                    for i, row in enumerate(final_rows, 1):  # Process all rows
                        try:
                            cells = row.find_elements(By.TAG_NAME, "td")
                            print(f"📋 Row {i}: Found {len(cells)} cells")
                            
                            # Debug: Print cell contents for first few rows
                            if i <= 5:  # Show first 5 rows to see what's happening
                                print(f"🔍 Row {i} debug:")
                                for j, cell in enumerate(cells):
                                    print(f"    Cell {j}: '{cell.text.strip()}'")
                            
                            if len(cells) >= 7:  # Ensure we have enough cells (SR, INSTITUTION, CASE_NO, CASE_TITLE, BENCH, HEARING_DATE, STATUS, HISTORY, DETAILS)
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
                                
                                # Only add if we have meaningful data (skip header row and empty rows)
                                if case_data['SR'] and case_data['SR'].isdigit() and case_data['CASE_NO']:
                                    cases.append(case_data)
                                    print(f"✅ Row {i}: Added case with SR={case_data['SR']}")
                                else:
                                    print(f"⚠️ Row {i}: Skipped (SR='{case_data.get('SR', 'N/A')}', CASE_NO='{case_data.get('CASE_NO', 'N/A')}')")
                            else:
                                print(f"⚠️ Row {i}: Not enough cells ({len(cells)})")
                                
                        except Exception as e:
                            print(f"⚠️ Error processing row {i}: {e}")
                            continue
                    
                    print(f"📊 Total cases found: {len(cases)}")
                    
                    # If case type was empty and we got a lot of results, show progress
                    if case_type_empty and len(cases) > 50:
                        print(f"🎯 SUCCESS! Found {len(cases)} cases with empty case type (bulk data)")
                    
                    return cases
                else:
                    print("❌ No data rows found after waiting")
                    return []
                    
            except Exception as e:
                print(f"❌ Error processing final data: {e}")
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
            
            # Load existing data if file exists
            existing_data = []
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            
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

if __name__ == "__main__":
    # Run simple test by default
    run_simple_test(headless=True)