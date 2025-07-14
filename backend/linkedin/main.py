import asyncio
import json
import os

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from dotenv import load_dotenv

from config import BASE_URL, CSS_SELECTOR, REQUIRED_KEYS
from utils.data_utils import save_venues_to_csv
from utils.scraper_utils import (
    fetch_and_process_page,
    get_browser_config,
    get_llm_strategy,
)

load_dotenv()

# Load storage state for LinkedIn session
try:
    with open("linkedin_storage.json", "r") as f:
        LINKEDIN_STORAGE_STATE = json.load(f)
    print("✓ LinkedIn storage state loaded successfully")
except FileNotFoundError:
    print("❌ linkedin_storage.json not found. You may need to create a session first.")
    LINKEDIN_STORAGE_STATE = None
except json.JSONDecodeError:
    print("❌ Invalid JSON in linkedin_storage.json")
    LINKEDIN_STORAGE_STATE = None


async def test_basic_connection():
    """Test basic connection to LinkedIn jobs page"""
    print("Testing basic connection to LinkedIn...")
    
    browser_config = get_browser_config(storage_state=LINKEDIN_STORAGE_STATE)
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        # Import CrawlerRunConfig and CacheMode
        from crawl4ai import CrawlerRunConfig, CacheMode
        
        result = await crawler.arun(
            url=BASE_URL,
            config=CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS
            )
        )
        
        if result.success:
            print(f"✓ Successfully connected. Content length: {len(result.cleaned_html)}")
            
            # Check for common LinkedIn indicators
            content_lower = result.cleaned_html.lower()
            indicators = {
                "LinkedIn page": "linkedin" in content_lower,
                "Jobs content": "job" in content_lower,
                "Search results": "search" in content_lower,
                "Login required": "sign in" in content_lower or "login" in content_lower,
                "Rate limited": "rate limit" in content_lower or "too many requests" in content_lower,
            }
            
            for indicator, found in indicators.items():
                print(f"{'✓' if found else '❌'} {indicator}")
            
            # Save content for inspection
            with open("linkedin_test_content.html", "w", encoding="utf-8") as f:
                f.write(result.cleaned_html)
            print("✓ Saved test content to linkedin_test_content.html")
            
            return result.success
        else:
            print(f"❌ Connection failed: {result.error_message}")
            return False


async def crawl_jobs():
    """
    Main function to crawl job data from LinkedIn.
    """
    print("🚀 Starting LinkedIn job crawl...")
    
    # Test connection first
    if not await test_basic_connection():
        print("❌ Basic connection test failed. Exiting.")
        return

    # Initialize configurations
    browser_config = get_browser_config(storage_state=LINKEDIN_STORAGE_STATE)
    llm_strategy = get_llm_strategy()
    session_id = "linkedin_jobs_crawl"

    # Initialize state variables
    page_number = 1  # Start from page 1
    all_jobs = []
    seen_links = set()
    max_pages = 5  # Limit for testing

    print(f"🔧 Configuration:")
    print(f"   Base URL: {BASE_URL}")
    print(f"   CSS Selector: {CSS_SELECTOR}")
    print(f"   Required Keys: {REQUIRED_KEYS}")
    print(f"   Max Pages: {max_pages}")

    # Start the web crawler
    async with AsyncWebCrawler(config=browser_config) as crawler:
        while page_number <= max_pages:
            print(f"\n📄 Processing page {page_number}/{max_pages}")
            
            try:
                # Fetch and process data from the current page
                jobs, no_results_found = await fetch_and_process_page(
                    crawler,
                    page_number,
                    BASE_URL,
                    CSS_SELECTOR,
                    llm_strategy,
                    session_id,
                    REQUIRED_KEYS,
                    seen_links,
                )

                if no_results_found:
                    print("🛑 No more jobs found. Ending crawl.")
                    break

                if not jobs:
                    print(f"⚠️ No jobs extracted from page {page_number}.")
                    # Don't break immediately, try next page
                    page_number += 1
                    continue

                # Add jobs to collection
                all_jobs.extend(jobs)
                print(f"✅ Added {len(jobs)} jobs from page {page_number}")
                print(f"📊 Total jobs collected: {len(all_jobs)}")

                page_number += 1

                # Pause between requests
                print("⏸️ Pausing 3 seconds...")
                await asyncio.sleep(3)

            except Exception as e:
                print(f"❌ Error processing page {page_number}: {e}")
                import traceback
                traceback.print_exc()
                break

    # Save results
    if all_jobs:
        try:
            save_venues_to_csv(all_jobs, "linkedin_jobs.csv")
            print(f"✅ Saved {len(all_jobs)} jobs to 'linkedin_jobs.csv'")
            
            # Print sample of collected jobs
            print("\n📋 Sample of collected jobs:")
            for i, job in enumerate(all_jobs[:3]):
                print(f"  {i+1}. {job.get('name', 'N/A')} at {job.get('company', 'N/A')}")
                
        except Exception as e:
            print(f"❌ Error saving jobs: {e}")
    else:
        print("❌ No jobs were collected during the crawl.")

    # Show LLM usage stats
    try:
        llm_strategy.show_usage()
    except Exception as e:
        print(f"⚠️ Could not show LLM usage: {e}")


async def main():
    """
    Entry point of the script.
    """
    try:
        await crawl_jobs()
    except KeyboardInterrupt:
        print("\n🛑 Crawl interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Check environment variables
    if not os.getenv("GROQ_API_KEY"):
        print("❌ GROQ_API_KEY not found in environment variables")
        exit(1)
    
    print("🔑 GROQ_API_KEY found")
    asyncio.run(main())