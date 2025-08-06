#!/usr/bin/env python3
"""
Islamabad High Court Web Scraper
Designed to scrape actual case data from the website interface
"""

import requests
import json
import time
import random
import os
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import urllib3

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class IHCWebScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False
        self.ua = UserAgent()
        self.base_url = "https://ihc.gov.pk"
        self.search_url = "https://ihc.gov.pk/casestatus/srchCseIhc_ByInst"
        
        # Set headers to mimic a real browser more aggressively
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/x-www-form-urlencoded",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        })
        
        # Configure session for better connection handling
        self.session.mount('https://', requests.adapters.HTTPAdapter(
            max_retries=requests.adapters.Retry(
                total=5,
                backoff_factor=0.5,
                status_forcelist=[500, 502, 503, 504]
            )
        ))
        
        # Disable SSL warnings
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Try to get initial session by visiting the main page first
        try:
            print("🌐 Initializing session by visiting main page...")
            response = self.session.get("https://ihc.gov.pk/casestatus/", timeout=30, verify=False)
            if response.status_code == 200:
                print("✅ Successfully initialized session")
            else:
                print(f"⚠️  Session initialization returned HTTP {response.status_code}")
        except Exception as e:
            print(f"⚠️  Session initialization failed: {e}")
    
    def get_search_page(self):
        """Get the initial search page to understand the form structure"""
        try:
            response = self.session.get(f"{self.base_url}/casestatus", timeout=30)
            if response.status_code == 200:
                return response.text
            else:
                print(f"⚠️  Failed to get search page: HTTP {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Error getting search page: {e}")
            return None
    
    def search_case(self, case_no, year, case_type="Case Number"):
        """Search for a specific case using the correct API endpoint"""
        # Try multiple approaches to access the API
        api_endpoints = [
            "https://ihc.gov.pk/casestatus/srchCselhc_ByInst",
            "http://ihc.gov.pk/casestatus/srchCselhc_ByInst",
            "https://www.ihc.gov.pk/casestatus/srchCselhc_ByInst",
            "http://www.ihc.gov.pk/casestatus/srchCselhc_ByInst"
        ]
        
        for api_endpoint in api_endpoints:
            try:
                # Prepare the payload exactly as the website expects
                payload = {
                    'pCaseno': str(case_no),
                    'pYear': str(year),
                    'pCat': '0',  # All categories
                    'pAdvct': '0',
                    'pPrty': '',
                    'pDt': '',
                    'pDesc': '',
                    'PCIRCUITCODE': '1'
                }
                
                print(f"🔍 Searching for case {case_no}/{year} via {api_endpoint}...")
                
                # Set headers to match the AJAX request
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "X-Requested-With": "XMLHttpRequest",
                    "Origin": "https://ihc.gov.pk",
                    "Referer": "https://ihc.gov.pk/casestatus/",
                    "Connection": "keep-alive",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-origin"
                }
                
                # Make the API request
                response = self.session.post(
                    api_endpoint,
                    data=payload,
                    headers=headers,
                    timeout=60,
                    verify=False
                )
                
                if response.status_code == 200:
                    print(f"✅ Successfully connected to {api_endpoint}")
                    print(f"📄 Response length: {len(response.text)} characters")
                    
                    # Parse the JSON response
                    try:
                        data = response.json()
                        if 'd' in data:
                            # The response contains a 'd' field with the actual data
                            cases_data = json.loads(data['d'])
                            return self.parse_api_results(cases_data)
                        else:
                            print(f"⚠️  Unexpected response format: {data}")
                            continue
                    except json.JSONDecodeError as e:
                        print(f"❌ Error parsing JSON response: {e}")
                        print(f"Response text: {response.text[:200]}...")
                        continue
                else:
                    print(f"⚠️  {api_endpoint} returned HTTP {response.status_code}")
                    continue
                    
            except Exception as e:
                print(f"❌ {api_endpoint} failed: {e}")
                continue
        
        print(f"❌ All endpoints failed for case {case_no}/{year}")
        return []
    
    def parse_api_results(self, cases_data):
        """Parse the API response data"""
        cases = []
        
        for case in cases_data:
            try:
                # Extract hearing date from HTML if present
                hearing_date = case.get('NHDATE', 'N/A')
                if hearing_date and hearing_date != 'N/A':
                    # Remove HTML tags and extract the date
                    import re
                    hearing_date = re.sub(r'<[^>]+>', '', hearing_date)
                    hearing_date = hearing_date.replace('\\u003c', '<').replace('\\u003e', '>')
                    hearing_date = re.sub(r'<[^>]+>', '', hearing_date)
                
                case_data = {
                    "SR": case.get('CASECODE', 'N/A'),
                    "Institution": case.get('INSTITUTIONDATE', 'N/A'),
                    "CaseNo": case.get('CASENO', 'N/A'),
                    "CaseTitle": case.get('PARTY', 'N/A'),
                    "Bench": case.get('BENCHNAME', 'N/A'),
                    "HearingDate": hearing_date,
                    "Status": case.get('STATUS', 'N/A'),
                    "CaseDescription": case.get('CASE_DESCRIPTION', 'N/A'),
                    "DisposalDate": case.get('DISPOSALDATE', 'N/A'),
                    "Attachments": case.get('O_ATTACHMENTS', 'N/A'),
                    "History": {
                        "Orders": "Available" if case.get('O_ATTACHMENTS') else "Not Available",
                        "Comments": "Available",
                        "CaseCMs": "Available",
                        "Judgement": "Available" if case.get('O_ATTACHMENTS') else "Not Available"
                    },
                    "Details": "Available",
                    "ScrapedCaseNo": case.get('CASENO', '').split()[0] if case.get('CASENO') else '',
                    "ScrapedYear": case.get('CASEYEAR', ''),
                    "ScrapedTimestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                    "IsRealData": True
                }
                cases.append(case_data)
                
            except Exception as e:
                print(f"⚠️  Error parsing case: {e}")
                continue
        
        return cases
    
    def generate_realistic_mock_data(self, case_no, year):
        """Generate realistic mock data based on the actual website structure"""
        case_types = ["C.S.", "R.S.A.", "C.M.", "W.P.", "C.R."]
        case_categories = ["Cancellation (SB)", "Against Judgement & Decree (SB)", "Civil Miscellaneous", "Writ Petition", "Criminal Revision"]
        
        petitioners = [
            "M/s Pakistan Telecommunication Co. Ltd.",
            "Moladad",
            "Federal Government",
            "Province of Punjab",
            "City District Government"
        ]
        
        respondents = [
            "PTA",
            "Shehzad and others",
            "Federation of Pakistan",
            "Provincial Government",
            "Local Government"
        ]
        
        judges = [
            "Honourable Mr. Justice Sardar Ejaz Ishaq Khan",
            "The Honorable Chief Justice",
            "Honourable Mr. Justice Aamer Farooq",
            "Honourable Mr. Justice Mohsin Akhtar Kayani",
            "Honourable Mr. Justice Tariq Mehmood Jahangiri"
        ]
        
        statuses = ["Pending", "Disposed", "Admitted", "Dismissed"]
        
        # Generate realistic case data
        case_type = random.choice(case_types)
        category = random.choice(case_categories)
        petitioner = random.choice(petitioners)
        respondent = random.choice(respondents)
        judge = random.choice(judges)
        status = random.choice(statuses)
        
        # Generate realistic dates
        institution_date = f"{random.randint(1, 28):02d}-{random.randint(1, 12):02d}-{year}"
        hearing_date = f"{random.choice(['MON', 'TUE', 'WED', 'THU', 'FRI'])} {random.randint(1, 28):02d}-{random.randint(1, 12):02d}-{year + 1} ({random.choice(['FC', 'A', 'B', 'C'])}) {'CANCELLED - BY THE ORDER' if random.random() > 0.5 else 'CONFIRMED'}"
        
        return [{
            "SR": str(case_no),
            "Institution": institution_date,
            "CaseNo": f"{case_type} {case_no}/{year} {category}",
            "CaseTitle": f"{petitioner} - VS - {respondent}",
            "Bench": judge,
            "HearingDate": hearing_date,
            "Status": status,
            "History": {
                "Orders": "Available" if random.random() > 0.3 else "Not Available",
                "Comments": "Available" if random.random() > 0.3 else "Not Available",
                "CaseCMs": "Available" if random.random() > 0.3 else "Not Available",
                "Judgement": "Available" if random.random() > 0.3 else "Not Available"
            },
            "Details": "Available",
            "ScrapedCaseNo": case_no,
            "ScrapedYear": year,
            "ScrapedTimestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "IsMockData": True
        }]

def save_cases_to_file(cases, filename="../../../../../cases_metadata/Islamabad_High_Court/ihc_cases_2023.json"):
    
    """Save cases to JSON file in the correct directory"""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Load existing data
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            existing_data = []
        
        # Add new cases
        existing_data.extend(cases)
        
        # Save to file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved {len(cases)} new cases to {filename} (Total: {len(existing_data)})")
        return True
    except Exception as e:
        print(f"❌ Error saving to {filename}: {e}")
        return False

def run_scraper(start=1, end=5, year=2025, use_mock=False):
    """Run the scraper for a range of cases"""
    scraper = IHCWebScraper()
    all_cases = []
    
    print(f"🚀 Starting IHC Web Scraper for cases {start}-{end} from year {year}")
    
    if use_mock:
        print("🎭 Running in MOCK MODE - generating realistic mock data")
        for case_no in range(start, end + 1):
            print(f"\n🔍 Processing case {case_no}/{year}...")
            cases = scraper.generate_realistic_mock_data(case_no, year)
            if cases:
                print(f"✅ Found {len(cases)} results for case {case_no}/{year}")
                all_cases.extend(cases)
                save_cases_to_file(cases)
            else:
                print(f"❌ No data found for case {case_no}/{year}")
            time.sleep(random.uniform(1, 3))
    else:
        print("🌐 Running in REAL MODE - attempting to fetch from website")
        print("⚠️  WARNING: This will only save REAL data from the website")
        print("❌ If website is unreachable, NO data will be saved")
        
        for case_no in range(start, end + 1):
            print(f"\n🔍 Processing case {case_no}/{year}...")
            
            # Only try to get real data
            cases = scraper.search_case(case_no, year)
            
            if cases:
                print(f"✅ Found {len(cases)} REAL results for case {case_no}/{year}")
                all_cases.extend(cases)
                save_cases_to_file(cases)
            else:
                print(f"❌ NO REAL DATA found for case {case_no}/{year} - SKIPPING")
                print(f"   Website is unreachable. Try again later when website is working.")
            
            # Random delay between requests
            time.sleep(random.uniform(2, 5))
    
    if not all_cases:
        print(f"\n❌ NO DATA COLLECTED!")
        print(f"   The Islamabad High Court website is currently unreachable.")
        print(f"   Try again later when the website is working.")
        print(f"   Or use --mock flag for testing with mock data.")
    else:
        print(f"\n📊 Summary: Processed {end - start + 1} cases, found {len(all_cases)} REAL results")
    
    return all_cases

if __name__ == "__main__":
    import sys
    
    # Check command line arguments
    use_mock = "--mock" in sys.argv or "--test" in sys.argv
    
    if use_mock:
        print("🎭 Running in MOCK MODE")
        run_scraper(1, 5, 2023, use_mock=True)
    else:
        print("🌐 Running in REAL MODE")
        run_scraper(1, 5, 2023, use_mock=False) 