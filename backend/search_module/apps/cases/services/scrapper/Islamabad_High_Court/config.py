"""
Configuration file for the Islamabad High Court scraper
"""

# Server Configuration
SERVER_CONFIG = {
    "base_url": "https://ihc.gov.pk",
    "endpoint": "/casestatus/srchCseIhc_ByInst",
    "timeout": 30,
    "max_retries": 3,
    "retry_delay": (2, 5),  # Random delay range in seconds
    "connection_delay": (3, 8),  # Longer delay for connection issues
}

# Request Headers
HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

# SSL Configuration
SSL_CONFIG = {
    "verify": False,  # Disable SSL verification
    "allow_insecure": True,  # Allow insecure connections
}

# Scraping Configuration
SCRAPING_CONFIG = {
    "default_start": 1,
    "default_end": 10,
    "default_year": 2023,
    "batch_size": 5,  # Number of cases to process in one batch
    "delay_between_requests": (2, 5),  # Random delay between requests
}

# Mock Data Configuration
MOCK_CONFIG = {
    "enabled": False,  # Set to True to use mock data
    "generate_realistic_data": True,  # Generate more realistic mock data
    "include_all_fields": True,  # Include all possible fields in mock data
}

# Alternative Endpoints (fallback URLs)
ALTERNATIVE_ENDPOINTS = [
    "https://ihc.gov.pk/casestatus/srchCseIhc_ByInst",
    "http://ihc.gov.pk/casestatus/srchCseIhc_ByInst",
    "https://www.ihc.gov.pk/casestatus/srchCseIhc_ByInst",
]

# Logging Configuration
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(levelname)s - %(message)s",
    "file": "ihc_scraper.log",
    "console": True,
}

# Error Handling Configuration
ERROR_CONFIG = {
    "max_consecutive_failures": 5,
    "fallback_to_mock": True,  # Use mock data if server is unreachable
    "continue_on_error": True,  # Continue scraping even if some cases fail
    "log_errors": True,
}

# Development/Testing Configuration
DEV_CONFIG = {
    "debug_mode": False,
    "verbose_output": True,
    "save_responses": False,  # Save raw responses for debugging
    "response_dir": "responses",  # Directory to save responses
}

# Court-specific data
COURT_INFO = {
    "name": "Islamabad High Court",
    "abbreviation": "IHC",
    "website": "https://ihc.gov.pk",
    "data_file": "cases_metadata/Islamabad_High_Court/ihc_cases_2023.json",
    "case_types": ["C.S.", "R.S.A.", "C.M.", "W.P.", "C.R."],
    "judges": [
        "Honourable Mr. Justice Sardar Ejaz Ishaq Khan",
        "The Honorable Chief Justice",
        "Honourable Mr. Justice Aamer Farooq",
        "Honourable Mr. Justice Mohsin Akhtar Kayani",
        "Honourable Mr. Justice Tariq Mehmood Jahangiri"
    ]
} 