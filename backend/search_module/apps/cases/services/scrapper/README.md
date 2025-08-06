# Court Scrapers Directory

This directory contains scrapers for different courts in Pakistan. Each court has its own dedicated folder with all necessary files for scraping and managing case data.

## Directory Structure

```
scrapper/
├── README.md                           # This file
├── Islamabad_High_Court/              # Islamabad High Court scraper
│   ├── ihc_web_scraper.py            # Main scraper script
│   ├── manage_cases.py                # Data management utility
│   ├── config.py                      # Configuration settings
│   ├── README.md                      # Court-specific documentation
│   └── lslamabad_scraper.py          # Legacy scraper (deprecated)
├── Lahore_High_Court/                 # Future: Lahore High Court scraper
├── Karachi_High_Court/                # Future: Karachi High Court scraper
└── Peshawar_High_Court/              # Future: Peshawar High Court scraper
```

## Current Courts

### 1. Islamabad High Court
- **Location**: `Islamabad_High_Court/`
- **Website**: https://ihc.gov.pk
- **Data File**: `cases_metadata/Islamabad_High_Court/ihc_cases_2023.json`
- **Status**: ✅ Implemented

## Usage

### Islamabad High Court

```bash
# Navigate to the court directory
cd apps/cases/services/scrapper/Islamabad_High_Court

# Run the scraper
python ihc_web_scraper.py --mock

# Manage data
python manage_cases.py view
python manage_cases.py analyze
```

## Adding New Courts

To add a new court (e.g., Lahore High Court):

1. **Create Court Directory**:
   ```bash
   mkdir apps/cases/services/scrapper/Lahore_High_Court
   ```

2. **Copy Template Files**:
   ```bash
   cp apps/cases/services/scrapper/Islamabad_High_Court/* apps/cases/services/scrapper/Lahore_High_Court/
   ```

3. **Update Configuration**:
   - Modify `config.py` with court-specific settings
   - Update URLs, endpoints, and court information
   - Adjust data file paths

4. **Customize Scraper**:
   - Modify `ihc_web_scraper.py` for the new court's website structure
   - Update parsing logic for the specific court's HTML format
   - Adjust mock data generation for realistic court data

5. **Update Data Management**:
   - Modify `manage_cases.py` to point to the correct data file
   - Update file paths and court-specific logic

## Data Organization

Each court's data is stored in:
```
cases_metadata/
├── Islamabad_High_Court/
│   └── ihc_cases_2023.json
├── Lahore_High_Court/
│   └── lhc_cases_2023.json
├── Karachi_High_Court/
│   └── khc_cases_2023.json
└── Peshawar_High_Court/
    └── phc_cases_2023.json
```

## Common Features

All court scrapers include:

- ✅ **SSL Issue Resolution**: Multiple fallback strategies
- ✅ **Mock Data Mode**: Realistic testing data
- ✅ **Robust Error Handling**: Graceful degradation
- ✅ **Data Management**: View, analyze, export utilities
- ✅ **Configuration**: Easy customization via config files
- ✅ **Documentation**: Court-specific README files

## Best Practices

1. **Separation of Concerns**: Each court has its own folder
2. **Consistent Structure**: Same file organization across courts
3. **Error Handling**: Robust SSL and connection error handling
4. **Mock Data**: Realistic fallback data for testing
5. **Documentation**: Clear usage instructions for each court

## Future Courts

Planned courts to be added:
- Lahore High Court (LHC)
- Karachi High Court (KHC)
- Peshawar High Court (PHC)
- Supreme Court of Pakistan (SCP)

Each will follow the same structure as Islamabad High Court. 