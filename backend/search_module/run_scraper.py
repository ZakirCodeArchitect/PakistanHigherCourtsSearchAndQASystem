#!/usr/bin/env python3
"""
Simple script to run the IHC scraper from project root
"""

import sys
import os

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import and run the scraper
from apps.cases.services.scrapers.islamabad_high_court.ihc_selenium_scraper import IHCSeleniumScraper

if __name__ == "__main__":
    print("🚀 Starting IHC Scraper...")
    
    # Create scraper instance
    scraper = IHCSeleniumScraper(headless=False, fetch_details=True)
    
    # Start the scraper
    scraper.start_driver()
    
    # Run a simple test search
    print("🔍 Running test search...")
    scraper.search_case(
        case_no=1,
        year=2024,
        case_type="Writ Petition",
        search_by_case_number=True
    )
    
    print("✅ Scraper test completed!")
