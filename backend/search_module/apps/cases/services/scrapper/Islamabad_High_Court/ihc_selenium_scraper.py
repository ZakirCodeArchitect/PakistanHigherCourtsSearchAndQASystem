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

    def fill_search_form(self, case_no=None, year=None, case_type=None, search_by_case_number=True):
        """Fill the search form with the given parameters"""
        try:
            print("📝 Filling search form...")
            
            # First, select the institution to populate other dropdowns
            print("🏛️ Selecting institution...")
            try:
                inst_select = Select(self.driver.find_element(By.ID, "ddlInst"))
                inst_select.select_by_value("1")  # Islamabad High Court
                print("✅ Selected Islamabad High Court")
                time.sleep(3)  # Wait longer for dropdowns to populate
            except Exception as e:
                print(f"⚠️ Could not select institution: {e}")

            # Fill Case Type first to populate year dropdown
            if case_type:
                print("📋 Selecting case type...")
                try:
                    # Try to find case type dropdown
                    case_type_select = None
                    try:
                        case_type_select = Select(self.driver.find_element(By.ID, "ddlCategory"))
                    except:
                        try:
                            case_type_select = Select(self.driver.find_element(By.NAME, "ctl00$ContentPlaceHolder1$ddlCaseType"))
                        except:
                            print("⚠️ Could not find case type dropdown")
                    
                    if case_type_select:
                        # Print available options for debugging
                        options = [option.text for option in case_type_select.options]
                        print(f"📋 Available case type options:")
                        for opt in options:
                            print(f"  - {opt}")
                        
                        # Try to select the case type
                        try:
                            case_type_select.select_by_visible_text(case_type)
                            print(f"✅ Selected: {case_type}")
                            time.sleep(2)  # Wait for year dropdown to populate
                        except:
                            # Try partial match
                            for option in case_type_select.options:
                                if case_type.lower() in option.text.lower():
                                    case_type_select.select_by_visible_text(option.text)
                                    print(f"✅ Selected by partial match: {option.text}")
                                    time.sleep(2)  # Wait for year dropdown to populate
                                    break
                            else:
                                print(f"⚠️ Could not select case type: {case_type}")
                except Exception as e:
                    print(f"⚠️ Error selecting case type: {e}")

            # Fill Case Number (MANDATORY - cannot be left empty)
            if search_by_case_number and case_no:
                print("🔢 Entering case number...")
                try:
                    # Find all input elements for debugging
                    inputs = self.driver.find_elements(By.TAG_NAME, "input")
                    print("🔍 Available input elements:")
                    for i, inp in enumerate(inputs):
                        print(f"  Input {i+1}: id='{inp.get_attribute('id')}', name='{inp.get_attribute('name')}', type='{inp.get_attribute('type')}'")
                    
                    # Try to find case number input
                    case_input = None
                    try:
                        case_input = self.driver.find_element(By.ID, "txtCaseno")
                    except:
                        try:
                            case_input = self.driver.find_element(By.NAME, "txtCaseno")
                        except:
                            # Try to find any input with 'case' in the name
                            for inp in inputs:
                                if 'case' in inp.get_attribute('name', '').lower():
                                    case_input = inp
                                    break
                    
                    if case_input:
                        case_input.clear()
                        case_input.send_keys(str(case_no))
                        print(f"✅ Entered case number: {case_no}")
                    else:
                        print("⚠️ Could not find case number input")
                        return False  # Case number is mandatory
                except Exception as e:
                    print(f"⚠️ Error entering case number: {e}")
                    return False  # Case number is mandatory
            else:
                print("❌ Case number is mandatory but not provided")
                return False

            # Fill Year (after case type selection to ensure dropdown is populated)
            if year:
                print("📅 Selecting case year...")
                try:
                    # Wait a bit more for year dropdown to populate after case type selection
                    time.sleep(2)
                    
                    # Find all select elements for debugging
                    selects = self.driver.find_elements(By.TAG_NAME, "select")
                    print("🔍 All select elements:")
                    for i, sel in enumerate(selects):
                        print(f"  Select {i+1}: id='{sel.get_attribute('id')}', name='{sel.get_attribute('name')}'")
                        options = [f"{j}: '{opt.text}' (value: '{opt.get_attribute('value')}')" for j, opt in enumerate(Select(sel).options)]
                        for opt in options:
                            print(f"    Options: {opt}")
                    
                    # Try to find year dropdown
                    year_select = None
                    try:
                        year_select = Select(self.driver.find_element(By.ID, "ddlCaseyear"))
                    except:
                        try:
                            year_select = Select(self.driver.find_element(By.NAME, "ctl00$ContentPlaceHolder1$ddlCaseYear"))
                        except:
                            # Try to find any select with 'year' in the name
                            for sel in selects:
                                if 'year' in sel.get_attribute('name', '').lower():
                                    year_select = Select(sel)
                                    break
                    
                    if year_select:
                        # Check if dropdown has options
                        options = year_select.options
                        if len(options) > 1 or (len(options) == 1 and options[0].text.strip()):
                            # Try to select year with fallbacks
                            try:
                                year_select.select_by_visible_text(str(year))
                                print(f"✅ Selected year: {year}")
                            except:
                                try:
                                    year_select.select_by_value(str(year))
                                    print(f"✅ Selected year by value: {year}")
                                except:
                                    # Try to find a year that contains our target year
                                    for option in options:
                                        if str(year) in option.text:
                                            year_select.select_by_visible_text(option.text)
                                            print(f"✅ Selected year by partial match: {option.text}")
                                            break
                                    else:
                                        print(f"⚠️ Year {year} not found in dropdown, using first available year")
                                        if len(options) > 1:
                                            year_select.select_by_index(1)  # Select first non-empty option
                                            print(f"✅ Selected first available year: {options[1].text}")
                        else:
                            print("ℹ️ Year dropdown is empty - proceeding without year selection")
                            print("ℹ️ This is normal for case number searches")
                    else:
                        print("⚠️ Could not find year dropdown")
                except Exception as e:
                    print(f"⚠️ Error selecting year: {e}")

            # Click Search Button
            print("🔍 Clicking search button...")
            try:
                search_button = None
                try:
                    search_button = self.driver.find_element(By.ID, "btnSearch")
                except:
                    try:
                        search_button = self.driver.find_element(By.NAME, "btnSearch")
                    except:
                        # Try to find any button with 'search' in the text or ID
                        buttons = self.driver.find_elements(By.TAG_NAME, "button")
                        for btn in buttons:
                            if 'search' in btn.text.lower() or 'search' in btn.get_attribute('id', '').lower():
                                search_button = btn
                                break
                
                if search_button:
                    print("✅ Found search button by ID")
                    search_button.click()
                    print("✅ Clicked search button")
                    print("✅ Form submitted successfully")
                else:
                    print("⚠️ Could not find search button")
                    return False
            except Exception as e:
                print(f"⚠️ Error clicking search button: {e}")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Error filling search form: {e}")
            return False

    def scrape_results_table(self):
        """Scrape the results table and return case data"""
        try:
            print("🔍 Looking for results...")
            time.sleep(5)  # Wait for results to load
            
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
            
            table = None
            used_selector = None
            
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
            
            if not table:
                print("❌ No results table found")
                return []
            
            # Get all rows from the table
            rows = table.find_elements(By.TAG_NAME, "tr")
            print(f"📊 Found {len(rows)} table rows")
            
            cases = []
            
            # Skip header row and process data rows
            for i, row in enumerate(rows[1:], 1):  # Skip first row (header)
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    print(f"📋 Row {i}: Found {len(cells)} cells")
                    
                    if len(cells) >= 8:  # Ensure we have enough cells
                        case_data = {
                            'CASE_NO': cells[0].text.strip() if len(cells) > 0 else '',
                            'CASE_TITLE': cells[1].text.strip() if len(cells) > 1 else '',
                            'PETITIONER': cells[2].text.strip() if len(cells) > 2 else '',
                            'RESPONDENT': cells[3].text.strip() if len(cells) > 3 else '',
                            'FILING_DATE': cells[4].text.strip() if len(cells) > 4 else '',
                            'STATUS': cells[5].text.strip() if len(cells) > 5 else '',
                            'COURT': cells[6].text.strip() if len(cells) > 6 else '',
                            'JUDGE': cells[7].text.strip() if len(cells) > 7 else '',
                            'REMARKS': cells[8].text.strip() if len(cells) > 8 else ''
                        }
                        
                        # Only add if we have meaningful data
                        if case_data['CASE_NO'] and case_data['CASE_TITLE']:
                            cases.append(case_data)
                            print(f"✅ Row {i}: Added case data")
                        else:
                            print(f"⚠️ Row {i}: Skipped (no meaningful data)")
                    else:
                        print(f"⚠️ Row {i}: Not enough cells ({len(cells)})")
                        
                except Exception as e:
                    print(f"⚠️ Error processing row {i}: {e}")
                    continue
            
            print(f"📊 Total cases found: {len(cases)}")
            return cases
            
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
            
            # Scrape the results
            all_cases_data = self.scrape_results_table()
            
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
        
        # Strategy 1: Search by case number ranges for all years
        print("\n📋 Strategy 1: Searching by case number ranges for all years...")
        for year in self.years:
            for case_no in range(1, 101):  # Search first 100 case numbers per year
                total_searches += 1
                print(f"\n🔍 Search {total_searches}: Case Number: {case_no}, Year: {year}")
                
                # Check if driver is still valid
                try:
                    self.driver.current_url
                except:
                    print("🔄 Driver session expired, restarting...")
                    if not self.restart_driver():
                        print("❌ Failed to restart driver, stopping search")
                        break
                
                try:
                    cases = self.search_case(case_no=case_no, year=year, search_by_case_number=True)
                    if cases:
                        successful_searches += 1
                        all_cases.extend(cases)
                        print(f"✅ Found {len(cases)} cases for case {case_no}/{year}")
                        
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
        
        # Strategy 2: Search by case type with case numbers for recent years
        print("\n📋 Strategy 2: Searching by case type with case numbers for recent years...")
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

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scrape case data from IHC website")
    parser.add_argument("--comprehensive", action="store_true", help="Run comprehensive search with all filter combinations")
    parser.add_argument("--year", type=int, default=2025, help="Year to search for")
    parser.add_argument("--case-type", type=str, default="Writ Petition", help="Type of case")
    parser.add_argument("--visible", action="store_true", help="Run in visible mode (not headless)")
    args = parser.parse_args()
    
    if args.comprehensive:
        print("🌐 Starting Comprehensive IHC Selenium Scraper")
        print(f"👻 Headless: {not args.visible}")
        run_comprehensive_scraper(headless=not args.visible)
    else:
        print("🌐 Starting IHC Selenium Scraper")
        print(f"📅 Year: {args.year}")
        print(f"📋 Case Type: {args.case_type}")
        print(f"👻 Headless: {not args.visible}")
        run_selenium_scraper(1, 10, args.year, args.case_type, headless=not args.visible)