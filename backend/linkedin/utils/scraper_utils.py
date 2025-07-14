import json
import os
from typing import List, Set, Tuple

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CacheMode,
    CrawlerRunConfig,
    LLMExtractionStrategy,
    LLMConfig,
)

from models.jobs import Jobs
from utils.data_utils import is_complete_job, is_duplicate_job


def get_browser_config(storage_state=None) -> BrowserConfig:
    """
    Returns the browser configuration for the crawler.

    Returns:
        BrowserConfig: The configuration settings for the browser.
    """
    return BrowserConfig(
        browser_type="chromium",
        headless=False,  # Keep false for debugging LinkedIn
        verbose=True,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        storage_state=storage_state,
        # Additional anti-detection measures for LinkedIn
        extra_args=[
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
            "--disable-dev-shm-usage",
            "--no-first-run",
            "--disable-extensions",
        ]
    )


def get_llm_strategy() -> LLMExtractionStrategy:
    """
    Returns the configuration for the language model extraction strategy.

    Returns:
        LLMExtractionStrategy: The settings for how to extract data using LLM.
    """
    return LLMExtractionStrategy(
        llm_config=LLMConfig(
            provider="groq/llama3-70b-8192",
            api_token=os.getenv("GROQ_API_KEY"),
        ),
        schema=Jobs.model_json_schema(),
        extraction_type="schema",
        instruction=(
            "Extract all job postings from the provided content. "
            "Look for job cards, job listings, or job entries and extract the following information for each job:\n"
            "- name: The job title\n"
            "- company: The company name\n"
            "- location_type: 'Remote', 'On-site', 'Hybrid', or 'N/A' if not specified\n"
            "- job_type: 'Full-time', 'Part-time', 'Contract', 'Internship', 'Temporary', or 'N/A' if not specified\n"
            "- posting_date: When the job was posted (e.g., '2 days ago', 'Yesterday', etc.)\n"
            "- application_link: The URL to apply for the job\n"
            "- location: The job location (city, state, country)\n"
            "- description: A brief description of the job\n\n"
            "If any field is not available, use 'N/A' as the value. "
            "Return the results as a JSON array of job objects."
        ),
        input_format="markdown",
        verbose=True,
    )


async def check_no_results(
    crawler: AsyncWebCrawler,
    url: str,
    session_id: str,
) -> bool:
    """
    Checks if the "No Results Found" message is present on the page.

    Args:
        crawler (AsyncWebCrawler): The web crawler instance.
        url (str): The URL to check.
        session_id (str): The session identifier.

    Returns:
        bool: True if "No Results Found" message is found, False otherwise.
    """
    try:
        result = await crawler.arun(
            url=url,
            config=CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                session_id=session_id,
                page_timeout=30000,  # 30 seconds
            ),
        )

        if result.success:
            # Check for various "no results" indicators specific to LinkedIn
            no_results_indicators = [
                "No results found",
                "no jobs found",
                "0 jobs",
                "No matching jobs",
                "We couldn't find any jobs",
                "Try broadening your search",
                "No jobs match your search",
                "jobs-search-no-results",
                "artdeco-empty-state"
            ]
            
            content = result.cleaned_html.lower()
            for indicator in no_results_indicators:
                if indicator.lower() in content:
                    print(f"No results indicator found: {indicator}")
                    return True
                    
            # Also check if the content is suspiciously short (might indicate blocked access)
            if len(result.cleaned_html) < 1000:
                print(f"Warning: Very short content ({len(result.cleaned_html)} chars) - might be blocked")
                
        else:
            print(f"Error fetching page for 'No Results Found' check: {result.error_message}")

        return False
    except Exception as e:
        print(f"Exception in check_no_results: {e}")
        return False


async def fetch_and_process_page(
    crawler: AsyncWebCrawler,
    page_number: int,
    base_url: str,
    css_selector: str,
    llm_strategy: LLMExtractionStrategy,
    session_id: str,
    required_keys: List[str],
    seen_links: Set[str],
) -> Tuple[List[dict], bool]:
    """
    Fetches and processes a single page of job data.

    Args:
        crawler (AsyncWebCrawler): The web crawler instance.
        page_number (int): The page number to fetch.
        base_url (str): The base URL of the website.
        css_selector (str): The CSS selector to target the content.
        llm_strategy (LLMExtractionStrategy): The LLM extraction strategy.
        session_id (str): The session identifier.
        required_keys (List[str]): List of required keys in the job data.
        seen_links (Set[str]): Set of job links that have already been seen.

    Returns:
        Tuple[List[dict], bool]:
            - List[dict]: A list of processed jobs from the page.
            - bool: A flag indicating if the "No Results Found" message was encountered.
    """
    try:
        # LinkedIn uses start parameter for pagination
        start_number = (page_number - 1) * 25
        url = f"{base_url}&start={start_number}"
        print(f"🔗 Crawling URL: {url}")
        print(f"📄 Loading page {page_number}...")

        # Check if "No Results Found" message is present
        no_results = await check_no_results(crawler, url, session_id)
        if no_results:
            return [], True

        # First, let's get the raw content to debug what we're actually getting
        print("🔍 Fetching raw content for debugging...")
        debug_result = await crawler.arun(
            url=url,
            config=CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                session_id=session_id,
                page_timeout=120000,
            ),
        )

        if debug_result.success:
            content_length = len(debug_result.cleaned_html)
            print(f"✅ Page loaded successfully. Content length: {content_length}")
            
            # Check for LinkedIn-specific indicators
            content_lower = debug_result.cleaned_html.lower()
            
            # LinkedIn access indicators
            access_indicators = {
                "LinkedIn page": "linkedin" in content_lower,
                "Jobs content": "job" in content_lower,
                "Search results": "search" in content_lower or "results" in content_lower,
                "Job cards": "job-card" in content_lower or "jobs-search-results" in content_lower,
                "Authentication wall": "sign in" in content_lower or "join now" in content_lower,
                "Rate limited": "rate limit" in content_lower or "too many requests" in content_lower,
                "Blocked/Captcha": "captcha" in content_lower or "challenge" in content_lower,
            }
            
            for indicator, found in access_indicators.items():
                status = "✅" if found else "❌"
                print(f"   {status} {indicator}")
            
            # Save raw content for debugging
            debug_filename = f"debug_page_{page_number}.html"
            with open(debug_filename, "w", encoding="utf-8") as f:
                f.write(debug_result.cleaned_html)
            print(f"💾 Saved raw content to {debug_filename}")
            
            # If we don't see job-related content, this might be the issue
            if not any(["job" in content_lower, "search" in content_lower]):
                print("⚠️ WARNING: No job-related content detected. You might be blocked or need to login.")
                print("   Check the saved HTML file to see what LinkedIn is actually returning.")
                
        else:
            print(f"❌ Failed to load page for debugging: {debug_result.error_message}")
            return [], False

        # Now try to extract with the LLM strategy
        print("🤖 Attempting LLM extraction...")
        result = await crawler.arun(
            url=url,
            config=CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                extraction_strategy=llm_strategy,
                css_selector=css_selector,
                session_id=session_id,
                page_timeout=120000,
            ),
        )

        if not result.success:
            print(f"❌ Error fetching page {page_number}: {result.error_message}")
            return [], False

        if not result.extracted_content:
            print(f"⚠️ No extracted content from page {page_number}")
            print("   This could mean:")
            print("   - CSS selector didn't match any content")
            print("   - LLM couldn't extract structured data")
            print("   - Page content is not accessible")
            return [], False

        # Parse extracted content
        try:
            extracted_data = json.loads(result.extracted_content)
            print(f"✅ Successfully parsed extracted data: {type(extracted_data)}")
            
            # Handle different response formats from LLM
            if isinstance(extracted_data, dict):
                if "jobs" in extracted_data:
                    extracted_data = extracted_data["jobs"]
                elif "items" in extracted_data:
                    extracted_data = extracted_data["items"]
                elif "data" in extracted_data:
                    extracted_data = extracted_data["data"]
                else:
                    # If it's a single job object, convert to list
                    if all(key in extracted_data for key in ["name", "company"]):
                        extracted_data = [extracted_data]
                    else:
                        print(f"⚠️ Unexpected data structure: {list(extracted_data.keys())}")
            
            if not isinstance(extracted_data, list):
                print(f"❌ Expected list, got {type(extracted_data)}")
                return [], False
                
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {e}")
            print(f"Raw extracted content (first 500 chars): {result.extracted_content[:500]}...")
            return [], False

        if not extracted_data:
            print(f"⚠️ No jobs found in extracted data on page {page_number}")
            return [], False

        print(f"📊 Extracted {len(extracted_data)} potential jobs from page {page_number}")

        # Process jobs
        complete_jobs = []
        for i, job in enumerate(extracted_data):
            print(f"🔍 Processing job {i+1}/{len(extracted_data)}: {job.get('name', 'Unknown')}")

            # Handle error field that might be added by LLM
            if job.get("error") is False:
                job.pop("error", None)

            # Check if job has required fields
            if not is_complete_job(job, required_keys):
                missing_keys = [key for key in required_keys if key not in job or not job[key]]
                print(f"   ⚠️ Incomplete job (missing: {missing_keys})")
                continue

            # Check for duplicates using application_link
            job_link = job.get("application_link", "")
            if is_duplicate_job(job_link, seen_links):
                print(f"   🔄 Duplicate job: {job.get('name', 'Unknown')}")
                continue

            # Add job to results
            seen_links.add(job_link)
            complete_jobs.append(job)
            print(f"   ✅ Added: {job.get('name')} at {job.get('company')}")

        print(f"📋 Found {len(complete_jobs)} complete, unique jobs on page {page_number}")
        return complete_jobs, False

    except Exception as e:
        print(f"❌ Exception in fetch_and_process_page: {e}")
        import traceback
        traceback.print_exc()
        return [], False