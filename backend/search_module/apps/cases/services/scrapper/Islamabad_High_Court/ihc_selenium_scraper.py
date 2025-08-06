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
            print("✅ Found Case Status button")
            
            # Scroll into view and click
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", case_status_button)
            time.sleep(1)
            
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
            
        except TimeoutException:
            print("❌ Timeout waiting for page to load")
            # Print current page source for debugging
            print("📄 Current page source:")
            print(self.driver.page_source[:1000])  # Print first 1000 chars
            return False
        except Exception as e:
            print(f"❌ Error navigating to Case Status: {e}")
            return False
            
    def fill_search_form(self, case_no, year, case_type):
        """Fill out the case search form""" 
        try:
            print("📝 Filling search form...")
            
            # Based on debugging, we found these actual element names:
            # Form: casesearch
            # Selects: ddlInst, ddlCategory, ddlCaseyear, etc.
            
            # Fill Case Type (try different possible names)
            print("📋 Selecting case type...")
            try:
                case_type_select = Select(self.driver.find_element(By.NAME, "ctl00$ContentPlaceHolder1$ddlCaseType"))
            except:
                try:
                    case_type_select = Select(self.driver.find_element(By.ID, "ddlCategory"))
                except:
                    case_type_select = Select(self.driver.find_element(By.NAME, "ddlCategory"))
            
            # Debug: Print available options
            print("📋 Available case type options:")
            for option in case_type_select.options:
                print(f"  - {option.text}")
            
            # Try to select by visible text, with fallbacks
            case_types_to_try = [case_type, "Writ Petition", "Writ", "Civil", "Criminal", "Constitutional Petition"]
            selected = False
            
            for case_type_option in case_types_to_try:
                try:
                    case_type_select.select_by_visible_text(case_type_option)
                    print(f"✅ Selected: {case_type_option}")
                    selected = True
                    break
                except:
                    continue
            
            if not selected:
                # Select first option if exact match not found
                try:
                    case_type_select.select_by_index(1)
                    print("✅ Selected first available option")
                except:
                    print("⚠️ Could not select any case type")
                    return False
            
            time.sleep(random.uniform(1, 2))
            
            # Fill Case Number
            print("🔢 Entering case number...")
            
            # Debug: Find all input elements
            print("🔍 Available input elements:")
            inputs = self.driver.find_elements(By.TAG_NAME, "input")
            for i, input_elem in enumerate(inputs):
                input_id = input_elem.get_attribute('id')
                input_name = input_elem.get_attribute('name')
                input_type = input_elem.get_attribute('type')
                if input_id or input_name:
                    print(f"  Input {i+1}: id='{input_id}', name='{input_name}', type='{input_type}'")
            
            # Try to find case number input
            case_no_input = None
            for input_elem in inputs:
                input_id = input_elem.get_attribute('id')
                input_name = input_elem.get_attribute('name')
                if input_id and 'case' in input_id.lower():
                    case_no_input = input_elem
                    print(f"✅ Found case input by ID: {input_id}")
                    break
                elif input_name and 'case' in input_name.lower():
                    case_no_input = input_elem
                    print(f"✅ Found case input by name: {input_name}")
                    break
            
            if not case_no_input:
                # Try the original names
                try:
                    case_no_input = self.driver.find_element(By.NAME, "ctl00$ContentPlaceHolder1$txtCaseNo")
                    print("✅ Found case input by original name")
                except:
                    try:
                        case_no_input = self.driver.find_element(By.NAME, "txtCaseNo")
                        print("✅ Found case input by simple name")
                    except:
                        print("❌ No case number input found")
                        return False
            
            case_no_input.clear()
            case_no_input.send_keys(str(case_no))
            print(f"✅ Entered case number: {case_no}")
            time.sleep(random.uniform(1, 2))
            
            # First, select the institution to populate other dropdowns
            print("🏛️ Selecting institution...")
            try:
                inst_select = Select(self.driver.find_element(By.ID, "ddlInst"))
                inst_select.select_by_value("1")  # Islamabad High Court
                print("✅ Selected Islamabad High Court")
                time.sleep(2)  # Wait for dropdowns to populate
            except Exception as e:
                print(f"⚠️ Could not select institution: {e}")
            
            # Fill Year
            print("📅 Selecting case year...")
            
            # Debug: Show all select elements
            print("🔍 All select elements:")
            selects = self.driver.find_elements(By.TAG_NAME, "select")
            for i, select in enumerate(selects):
                select_id = select.get_attribute('id')
                select_name = select.get_attribute('name')
                print(f"  Select {i+1}: id='{select_id}', name='{select_name}'")
                
                # Show options for each select
                select_obj = Select(select)
                print(f"    Options:")
                for j, option in enumerate(select_obj.options):
                    print(f"      {j}: '{option.text}' (value: '{option.get_attribute('value')}')")
            
            # Try to find year dropdown
            year_select = None
            for select in selects:
                select_id = select.get_attribute('id')
                select_name = select.get_attribute('name')
                if select_id and 'year' in select_id.lower():
                    year_select = Select(select)
                    print(f"✅ Found year select by ID: {select_id}")
                    break
                elif select_name and 'year' in select_name.lower():
                    year_select = Select(select)
                    print(f"✅ Found year select by name: {select_name}")
                    break
            
            if not year_select:
                # Try original names
                try:
                    year_select = Select(self.driver.find_element(By.NAME, "ctl00$ContentPlaceHolder1$ddlCaseYear"))
                    print("✅ Found year select by original name")
                except:
                    try:
                        year_select = Select(self.driver.find_element(By.ID, "ddlCaseyear"))
                        print("✅ Found year select by original ID")
                    except:
                        print("❌ No year dropdown found")
                        return False
            
            # Try to select year with fallbacks
            try:
                year_select.select_by_visible_text(str(year))
                print(f"✅ Selected year: {year}")
            except:
                try:
                    year_select.select_by_visible_text(str(year))
                    print(f"✅ Selected year by text: {year}")
                except:
                    # Skip year selection if no valid options - this is OK for case number searches
                    print("ℹ️ Year dropdown is empty - proceeding without year selection")
                    print("ℹ️ This is normal for case number searches")
            
            time.sleep(random.uniform(1, 2))
            
            # Click Search
            print("🔍 Clicking search button...")
            try:
                search_button = self.driver.find_element(By.NAME, "ctl00$ContentPlaceHolder1$btnSearch")
                print("✅ Found search button by original name")
            except:
                try:
                    search_button = self.driver.find_element(By.NAME, "btnSearch")
                    print("✅ Found search button by simple name")
                except:
                    try:
                        search_button = self.driver.find_element(By.ID, "btnSearch")
                        print("✅ Found search button by ID")
                    except:
                        # Try to find any button with search functionality
                        buttons = self.driver.find_elements(By.TAG_NAME, "button")
                        search_button = None
                        for button in buttons:
                            button_text = button.text.lower()
                            button_id = button.get_attribute('id')
                            if 'search' in button_text or 'search' in button_id.lower():
                                search_button = button
                                print(f"✅ Found search button by text/ID: {button_text}/{button_id}")
                                break
                        
                        if not search_button:
                            print("❌ No search button found")
                            return False
            
            search_button.click()
            print("✅ Clicked search button")
            
            # Wait for results
            time.sleep(3)
            print("✅ Form submitted successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error filling search form: {e}")
            return False
            
    def scrape_results_table(self):
        """Scrape data from the results table"""
        try:
            print("🔍 Looking for results...")
            
            # Wait longer for dynamic content to load
            time.sleep(5)
            
            # Check for various result elements
            try:
                # Try multiple table selectors based on the image
                table_selectors = [
                    (By.ID, "grdCases"),
                    (By.TAG_NAME, "table"),
                    (By.XPATH, "//table[contains(@class, 'table')]"),
                    (By.XPATH, "//div[contains(@class, 'table')]//table"),
                    (By.XPATH, "//table[.//th[contains(text(), 'CASE_NO')]]"),
                    (By.XPATH, "//table[.//th[contains(text(), 'SR')]]")
                ]
                
                table = None
                for selector in table_selectors:
                    try:
                        table = WebDriverWait(self.driver, 3).until(
                            EC.presence_of_element_located(selector)
                        )
                        print(f"✅ Found results table with selector: {selector}")
                        break
                    except TimeoutException:
                        continue
                
                if not table:
                    print("❌ No results table found with any selector")
                    return None
                
                # Look for table rows with data (skip header)
                rows = table.find_elements(By.TAG_NAME, "tr")
                print(f"📊 Found {len(rows)} table rows")
                
                if len(rows) <= 1:  # Only header row
                    print("ℹ️ No data rows found in table")
                    return None
                
                # Extract data from ALL data rows (skip header)
                all_cases_data = []
                
                for i in range(1, len(rows)):  # Skip header row (index 0)
                    data_row = rows[i]
                    cells = data_row.find_elements(By.TAG_NAME, "td")
                    print(f"📋 Row {i}: Found {len(cells)} cells")
                    
                    if len(cells) < 3:
                        print(f"⚠️ Row {i}: Not enough cells, skipping")
                        continue
                    
                    # Extract data based on the table structure from the image
                    case_data = {
                        "SR": cells[0].text.strip() if len(cells) > 0 else "",
                        "INSTITUTION": cells[1].text.strip() if len(cells) > 1 else "",
                        "CASE_NO": cells[2].text.strip() if len(cells) > 2 else "",
                        "CASE_TITLE": cells[3].text.strip() if len(cells) > 3 else "",
                        "BENCH": cells[4].text.strip() if len(cells) > 4 else "",
                        "HEARING_DATE": cells[5].text.strip() if len(cells) > 5 else "",
                        "STATUS": cells[6].text.strip() if len(cells) > 6 else "",
                        "HISTORY": cells[7].text.strip() if len(cells) > 7 else "",
                        "DETAILS": cells[8].text.strip() if len(cells) > 8 else ""
                    }
                    
                    all_cases_data.append(case_data)
                    print(f"✅ Row {i}: Added case data")
                
                print(f"📊 Total cases found: {len(all_cases_data)}")
                
                if all_cases_data:
                    # Return all cases as a list
                    return all_cases_data
                else:
                    print("❌ No valid case data found")
                    return None
                
            except TimeoutException:
                print("ℹ️ No results table found, checking for other result elements...")
                
                # Check for any text indicating no results
                page_text = self.driver.page_source.lower()
                if "no results" in page_text or "no data" in page_text or "not found" in page_text:
                    print("ℹ️ No results found message detected")
                    return None
                
                # Check for any table or list elements
                tables = self.driver.find_elements(By.TAG_NAME, "table")
                if tables:
                    print(f"ℹ️ Found {len(tables)} table(s), but couldn't parse results")
                    # Print table details for debugging
                    for i, table in enumerate(tables):
                        print(f"  Table {i+1}: {table.get_attribute('id') or table.get_attribute('class') or 'no-id'}")
                
                # Print current page title and URL for debugging
                print(f"📍 Current URL: {self.driver.current_url}")
                print(f"📄 Page title: {self.driver.title}")
                
                return None
            
        except Exception as e:
            print(f"❌ Error scraping results: {e}")
            return None
            
    def search_case(self, case_no, year, case_type):
        """Search for a specific case and return its data"""
        try:
            if not self.navigate_to_case_status():
                return None
                
            if not self.fill_search_form(case_no, year, case_type):
                return None
                
            # Scrape all results (returns a list of cases)
            all_cases = self.scrape_results_table()
            
            if all_cases:
                print(f"📊 Found {len(all_cases)} cases for search criteria")
                # Print first few cases for debugging
                for i, case in enumerate(all_cases[:3]):  # Show first 3 cases
                    print(f"  Case {i+1}: {case.get('CASE_NO', 'N/A')} - {case.get('CASE_TITLE', 'N/A')[:50]}...")
                if len(all_cases) > 3:
                    print(f"  ... and {len(all_cases) - 3} more cases")
            
            return all_cases
            
        except Exception as e:
            print(f"❌ Error searching case: {e}")
            return None

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
    parser.add_argument("--year", type=int, default=2025, help="Year to search for")
    parser.add_argument("--case-type", type=str, default="Writ Petition", help="Type of case")
    parser.add_argument("--visible", action="store_true", help="Run in visible mode (not headless)")
    args = parser.parse_args()
    
    print("🌐 Starting IHC Selenium Scraper")
    print(f"📅 Year: {args.year}")
    print(f"📋 Case Type: {args.case_type}")
    print(f"👻 Headless: {not args.visible}")
    
    run_selenium_scraper(1, 5, args.year, args.case_type, headless=not args.visible)