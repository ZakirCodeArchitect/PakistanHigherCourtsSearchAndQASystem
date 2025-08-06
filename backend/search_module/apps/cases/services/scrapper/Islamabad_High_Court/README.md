# Islamabad High Court Scraper

This scraper is specifically designed to fetch case data from the Islamabad High Court website. It includes robust error handling and fallback mechanisms to handle SSL connection issues.

## Features

### 1. **Realistic Data Structure**
- Matches actual website format
- Proper case titles: "M/s Pakistan Telecommunication Co. Ltd. - VS -PTA"
- Real judge names: "Honourable Mr. Justice Sardar Ejaz Ishaq Khan"
- Accurate case numbers: "C.S. 1/2023 Cancellation (SB)"
- Proper hearing dates: "TUE 02-04-2024 (FC) CANCELLED - BY THE ORDER"

### 2. **SSL Issue Resolution**
- Multiple SSL configurations and fallback strategies
- Disabled SSL verification for problematic servers
- Retry mechanisms with exponential backoff
- Alternative endpoints (HTTP, HTTPS, www subdomain)

### 3. **Mock Data Mode**
- Realistic mock data generation for testing
- Command-line flag support (`--mock`, `--test`)
- Allows development to continue when server is unreachable

### 4. **Robust Error Handling**
- Multiple retry attempts with different delays
- Graceful degradation to mock data
- Comprehensive error reporting and logging
- Connection pooling and session management

## Usage

### Basic Usage

```bash
# Run from the Islamabad_High_Court directory
cd apps/cases/services/scrapper/Islamabad_High_Court

# Normal mode (tries to connect to server)
python ihc_web_scraper.py

# Mock mode (uses simulated data)
python ihc_web_scraper.py --mock
```

### Data Management

```bash
# View cases
python manage_cases.py view

# View first 5 cases
python manage_cases.py view 5

# Analyze data
python manage_cases.py analyze

# Export to CSV
python manage_cases.py export csv

# Clear all data
python manage_cases.py clear
```

## Data Structure

Each case includes:

```json
{
  "SR": "1",
  "Institution": "11-12-2023",
  "CaseNo": "C.S. 1/2023 Cancellation (SB)",
  "CaseTitle": "M/s Pakistan Telecommunication Co. Ltd. - VS -PTA",
  "Bench": "Honourable Mr. Justice Sardar Ejaz Ishaq Khan",
  "HearingDate": "TUE 02-04-2024 (FC) CANCELLED - BY THE ORDER",
  "Status": "Pending",
  "History": {
    "Orders": "Available",
    "Comments": "Available",
    "CaseCMs": "Available",
    "Judgement": "Available"
  },
  "Details": "Available",
  "ScrapedCaseNo": 1,
  "ScrapedYear": 2023,
  "ScrapedTimestamp": "2025-08-06 15:00:00",
  "IsMockData": false
}
```

## Configuration

The scraper uses `config.py` for easy customization:

```python
from config import *

# Modify settings as needed
SERVER_CONFIG["timeout"] = 60
SCRAPING_CONFIG["batch_size"] = 10
MOCK_CONFIG["enabled"] = True
```

## Error Handling

The scraper handles various types of errors:

1. **SSL Errors**: Retry with different configurations
2. **Connection Errors**: Try alternative endpoints
3. **Timeout Errors**: Exponential backoff retry
4. **Server Errors**: Fallback to mock data
5. **JSON Parse Errors**: Graceful handling with logging

## Troubleshooting

### Common Issues

1. **SSL Connection Errors**
   - The server has known SSL issues
   - Use mock mode for development: `--mock`
   - Check if server is accessible: `curl -k https://ihc.gov.pk`

2. **Timeout Errors**
   - Increase timeout in config: `SERVER_CONFIG["timeout"] = 60`
   - Check network connectivity

3. **No Data Returned**
   - Server might be down or blocking requests
   - Try different time periods
   - Use mock mode for testing

## Files

- `ihc_web_scraper.py` - Main scraper script
- `manage_cases.py` - Data management utility
- `config.py` - Configuration settings
- `README.md` - This documentation file

## Data Location

All scraped data is saved to:
```
cases_metadata/Islamabad_High_Court/ihc_cases_2023.json
```

## Future Extensions

This structure allows for easy addition of other courts:
- Lahore High Court
- Karachi High Court  
- Peshawar High Court

Each court will have its own folder with similar structure. 