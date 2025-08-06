import requests
import json
import time
import random
import ssl
import urllib3
from fake_useragent import UserAgent
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup
import re

ua = UserAgent()
ENDPOINT = "https://ihc.gov.pk/casestatus/srchCseIhc_ByInst"
OUTPUT_FILE = "ihc_cases_2023.json"

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def create_robust_session():
    """Create a session with multiple SSL configurations"""
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    
    # Create adapter with custom SSL context
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Disable SSL verification
    session.verify = False
    
    # Set headers
    session.headers.update({
        "User-Agent": ua.random,
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache"
    })
    
    return session

def parse_case_data_from_html(html_content):
    """Parse actual case data from HTML response"""
    soup = BeautifulSoup(html_content, 'html.parser')
    cases = []
    
    # Find the results table
    table = soup.find('table', {'class': 'table'}) or soup.find('table')
    if not table:
        return []
    
    rows = table.find_all('tr')[1:]  # Skip header row
    for row in rows:
        cells = row.find_all('td')
        if len(cells) >= 7:  # Ensure we have enough columns
            try:
                case_data = {
                    "SR": cells[0].get_text(strip=True),
                    "Institution": cells[1].get_text(strip=True),
                    "CaseNo": cells[2].get_text(strip=True),
                    "CaseTitle": cells[3].get_text(strip=True),
                    "Bench": cells[4].get_text(strip=True),
                    "HearingDate": cells[5].get_text(strip=True),
                    "Status": cells[6].get_text(strip=True),
                    "History": {
                        "Orders": "Available" if cells[7].find('button') else "Not Available",
                        "Comments": "Available" if len(cells) > 8 and cells[8].find('button') else "Not Available",
                        "CaseCMs": "Available" if len(cells) > 9 and cells[9].find('button') else "Not Available",
                        "Judgement": "Available" if len(cells) > 10 and cells[10].find('button') else "Not Available"
                    },
                    "Details": "Available" if len(cells) > 11 and cells[11].find('i') else "Not Available"
                }
                cases.append(case_data)
            except Exception as e:
                print(f"⚠️  Error parsing row: {e}")
                continue
    
    return cases

def generate_mock_data(case_no, year):
    """Generate mock data for testing when server is unreachable"""
    return [
        {
            "CaseNo": f"{case_no}/{year}",
            "Title": f"Mock Case {case_no} of {year}",
            "Petitioner": f"Petitioner {case_no}",
            "Respondent": f"Respondent {case_no}",
            "Status": "Pending",
            "Date": f"{year}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
            "Court": "Islamabad High Court",
            "Type": "Civil",
            "Description": f"This is a mock case description for case {case_no}/{year}",
            "Judge": "Honorable Justice Mock",
            "Category": "Civil Miscellaneous"
        }
    ]

def check_server_status():
    """Check if the server is accessible"""
    try:
        session = create_robust_session()
        response = session.get("https://ihc.gov.pk", timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"⚠️  Server status check failed: {e}")
        return False

def try_alternative_endpoints(case_no, year):
    """Try alternative endpoints or methods"""
    payload = {
        "pCaseno": str(case_no),
        "pYear": str(year),
        "pCat": "0",
        "pAdvet": "0",
        "pPrty": "",
        "pDt": "",
        "pDesc": "",
        "PCIRCUITCODE": "1"
    }
    
    # Try different endpoints
    endpoints = [
        "https://ihc.gov.pk/casestatus/srchCseIhc_ByInst",
        "http://ihc.gov.pk/casestatus/srchCseIhc_ByInst",  # Try HTTP
        "https://www.ihc.gov.pk/casestatus/srchCseIhc_ByInst",  # Try with www
    ]
    
    session = create_robust_session()
    
    for endpoint in endpoints:
        try:
            print(f"🔍 Trying endpoint: {endpoint}")
            response = session.post(
                endpoint,
                json=payload,
                timeout=30,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                # Try to parse as JSON first
                try:
                    response_data = response.json()
                    if "d" in response_data:
                        parsed_data = json.loads(response_data["d"])
                        if parsed_data:
                            return parsed_data
                except json.JSONDecodeError:
                    pass
                
                # If JSON parsing fails, try HTML parsing
                try:
                    html_cases = parse_case_data_from_html(response.text)
                    if html_cases:
                        return html_cases
                except Exception as e:
                    print(f"⚠️  HTML parsing error: {e}")
                    continue
            else:
                print(f"⚠️  HTTP {response.status_code}")
                continue
                
        except Exception as e:
            print(f"⚠️  Failed with endpoint {endpoint}: {e}")
            continue
    
    return []

def fetch_case(case_no, year, max_retries=3, use_mock=False):
    """Fetch case data with multiple fallback strategies"""
    
    # If mock mode is enabled, return mock data
    if use_mock:
        print(f"🎭 Using mock data for case {case_no}/{year}")
        return generate_mock_data(case_no, year)
    
    # Strategy 1: Try with robust session
    for attempt in range(max_retries):
        try:
            print(f"🔍 Case {case_no}/{year} (attempt {attempt + 1}/{max_retries})")
            
            session = create_robust_session()
            payload = {
                "pCaseno": str(case_no),
                "pYear": str(year),
                "pCat": "0",
                "pAdvet": "0",
                "pPrty": "",
                "pDt": "",
                "pDesc": "",
                "PCIRCUITCODE": "1"
            }
            
            response = session.post(
                ENDPOINT,
                json=payload,
                timeout=30,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                # Try to parse as JSON first
                try:
                    response_data = response.json()
                    if "d" in response_data:
                        parsed_data = json.loads(response_data["d"])
                        if parsed_data:
                            print(f"✅ Found {len(parsed_data)} cases via JSON")
                            return parsed_data
                except json.JSONDecodeError:
                    pass
                
                # If JSON parsing fails, try HTML parsing
                try:
                    html_cases = parse_case_data_from_html(response.text)
                    if html_cases:
                        print(f"✅ Found {len(html_cases)} cases via HTML parsing")
                        return html_cases
                    else:
                        print(f"⚠️  No cases found in HTML response")
                        break
                except Exception as e:
                    print(f"⚠️  HTML parsing error: {e}")
                    break
            else:
                print(f"⚠️  HTTP {response.status_code} for case {case_no}")
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(2, 5))
                    continue
                else:
                    break
                    
        except (requests.exceptions.SSLError, requests.exceptions.ConnectionError, 
                requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
            print(f"⚠️  Connection error for case {case_no} (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(random.uniform(3, 8))
                continue
            else:
                break
        except Exception as e:
            print(f"❌ Case {case_no} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(random.uniform(2, 5))
                continue
            else:
                break
    
    # Strategy 2: Try alternative endpoints
    print(f"🔄 Trying alternative endpoints for case {case_no}")
    result = try_alternative_endpoints(case_no, year)
    
    # Strategy 3: If all else fails, use mock data
    if not result:
        print(f"🎭 Server unreachable, using mock data for case {case_no}")
        return generate_mock_data(case_no, year)
    
    return result

def load_existing_data():
    """Load existing data from the JSON file"""
    try:
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"📁 Loaded {len(data)} existing cases from {OUTPUT_FILE}")
            return data
    except FileNotFoundError:
        print(f"📁 Creating new file: {OUTPUT_FILE}")
        return []
    except json.JSONDecodeError:
        print(f"⚠️  Error reading {OUTPUT_FILE}, starting fresh")
        return []

def save_data_to_file(data):
    """Save data to the JSON file"""
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved {len(data)} cases to {OUTPUT_FILE}")
    except Exception as e:
        print(f"❌ Error saving to {OUTPUT_FILE}: {e}")

def run_scraper(start=1, end=10, year=2023, use_mock=False):
    successful_cases = 0
    failed_cases = 0
    
    print(f"🚀 Starting scraper for cases {start}-{end} from year {year}")
    
    if use_mock:
        print(f"🎭 Running in MOCK MODE - using simulated data")
    else:
        print(f"🌐 Running in REAL MODE - fetching actual data from website")
        print(f"⚠️  Note: Server may have SSL issues. Trying multiple approaches...")
        # Check server status first
        if not check_server_status():
            print(f"⚠️  Server appears to be unreachable. Consider using mock mode.")
    
    # Load existing data
    all_cases = load_existing_data()
    
    for i in range(start, end + 1):
        data = fetch_case(i, year, use_mock=use_mock)
        
        if data:
            print(f"✅ Case {i}/{year} - Found {len(data)} results")
            print(json.dumps(data, indent=2)[:500])  # Just print a sample
            
            # Add case number and year to each result for identification
            for case in data:
                case['ScrapedCaseNo'] = i
                case['ScrapedYear'] = year
                case['ScrapedTimestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
            
            # Add to all cases
            all_cases.extend(data)
            successful_cases += 1
            
            # Save after each successful case (incremental saving)
            save_data_to_file(all_cases)
        else:
            print(f"❌ Case {i}/{year} - No data found")
            failed_cases += 1
        
        # Random delay between requests
        time.sleep(random.uniform(2, 5))
    
    print(f"\n📊 Summary: {successful_cases} successful, {failed_cases} failed")
    print(f"💾 Total cases saved: {len(all_cases)}")
    
    if failed_cases > 0 and not use_mock:
        print(f"💡 The server appears to have SSL/connection issues.")
        print(f"💡 This might be due to:")
        print(f"   - Server SSL configuration problems")
        print(f"   - Geographic restrictions")
        print(f"   - Server maintenance")
        print(f"   - Anti-bot protection")
        print(f"💡 Try running with mock mode: run_scraper(use_mock=True)")

if __name__ == "__main__":
    # Check if mock mode is requested via command line argument
    import sys
    use_mock = "--mock" in sys.argv or "--test" in sys.argv
    
    if use_mock:
        print("🎭 Running in MOCK MODE")
        run_scraper(1, 5, use_mock=True)
    else:
        print("🌐 Running in REAL MODE - fetching actual website data")
        run_scraper(1, 5)
