# config.py

# LinkedIn Jobs Search URL
BASE_URL = "https://www.linkedin.com/jobs/search/?keywords=intern&location=&geoId=&f_TPR=&position=1&pageNum=0"

# CSS selectors for LinkedIn job listings (try multiple in case one doesn't work)
CSS_SELECTORS = [
    ".jobs-search__results-list",  # Main results container
    ".jobs-search-results-list",   # Alternative container
    ".job-card-container",         # Individual job cards
    ".jobs-search-results",        # Another alternative
    ".scaffold-layout__list-detail-inner",  # New LinkedIn layout
]

# Use the first selector as primary, others as fallbacks
CSS_SELECTOR = CSS_SELECTORS[0]

# Required keys for job data
REQUIRED_KEYS = [
    "name", 
    "company", 
    "location_type", 
    "job_type",
    "posting_date", 
    "application_link", 
    "location", 
    "description"
]

# Optional: LinkedIn-specific settings
LINKEDIN_SETTINGS = {
    "jobs_per_page": 25,  # LinkedIn shows 25 jobs per page
    "max_pages": 10,      # Limit to avoid being blocked
    "delay_between_pages": 3,  # Seconds to wait between pages
    "timeout": 120,       # Page timeout in seconds
}

# Alternative URLs for testing
TEST_URLS = [
    "https://www.linkedin.com/jobs/search/?keywords=intern",
    "https://www.linkedin.com/jobs/search/?keywords=software%20engineer",
    "https://www.linkedin.com/jobs/search/?keywords=data%20scientist",
]