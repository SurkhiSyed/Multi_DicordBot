# config.py

BASE_URL = "https://www.indeed.com/jobs?q=software+engineer&l=United+States"
CSS_SELECTOR = ".jobsearch-ResultsList"  # This is the main job list container; adjust as needed
REQUIRED_KEYS = [
    "title",         # Job title
    "company",       # Company name
    "location",      # Job location
    "summary",       # Short job summary/description
    "date",          # Posting date
    "job_url"        # Direct link to the job posting
]