# Islamabad High Court (IHC) Case Scraper

## Overview
This scraper successfully fetches case data from the Islamabad High Court website (`https://mis.ihc.gov.pk/`) using Selenium WebDriver.

## Files
- `ihc_selenium_scraper.py` - Main scraper script
- `ihc_cases_2023.json` - Output file containing scraped case data
- `README.md` - This documentation

## Features
✅ **Complete Data Extraction**: Captures all rows from search results (not just first row)  
✅ **JSON Data Storage**: Saves data to `ihc_cases_2023.json`  
✅ **Incremental Saving**: Appends new data to existing file  
✅ **Robust Error Handling**: Handles timeouts, missing elements, and connection issues  
✅ **Detailed Logging**: Comprehensive debugging output  

## Usage

### Run the scraper:
```bash
python ihc_selenium_scraper.py --visible
```

### Options:
- `--visible`: Run in visible mode (not headless)
- `--year 2025`: Specify year to search (default: 2025)
- `--case-type "Writ Petition"`: Specify case type (default: "Writ Petition")

### Example:
```bash
python ihc_selenium_scraper.py --visible --year 2025 --case-type "Writ Petition"
```

## Data Structure
Each case in the JSON file contains:
- `SR`: Serial Number
- `INSTITUTION`: Institution date
- `CASE_NO`: Case number and type
- `CASE_TITLE`: Case title with parties involved
- `BENCH`: Judge(s) name
- `HEARING_DATE`: Next hearing date and type
- `STATUS`: Case status (Decided, Pending, etc.)
- `HISTORY`: Available actions (Orders, Comments, Case CMs, Judgement)
- `DETAILS`: Additional details

## Requirements
- Python 3.7+
- Selenium
- webdriver-manager
- Chrome browser

## Installation
```bash
pip install selenium webdriver-manager
```

## Output
Data is saved to `ihc_cases_2023.json` in the same directory as the scraper.

## Status
✅ **WORKING**: Successfully fetches and saves all case data from the IHC website. 