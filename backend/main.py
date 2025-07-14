import asyncio

from crawl4ai import AsyncWebCrawler, LLMConfig
from dotenv import load_dotenv

from config import BASE_URL, CSS_SELECTOR, REQUIRED_KEYS
from utils.data_utils import (
    save_jobs_to_csv,
)
from utils.scraper_utils import (
    fetch_and_process_page,
    get_browser_config,
    get_llm_strategy,
)
from models.jobs import Jobs
from utils.data_utils import is_complete_job, is_duplicate_job

load_dotenv()

async def crawl_jobs():
    browser_config = get_browser_config()
    llm_strategy = get_llm_strategy()
    session_id = "indeed_crawl_session"

    page_number = 1
    all_jobs = []
    seen_urls = set()

    async with AsyncWebCrawler(config=browser_config) as crawler:
        while True:
            jobs, no_results_found = await fetch_and_process_page(
                crawler,
                page_number,
                BASE_URL,
                CSS_SELECTOR,
                llm_strategy,
                session_id,
                REQUIRED_KEYS,
                seen_urls,
            )

            if no_results_found:
                print("No more jobs found. Ending crawl.")
                break

            if not jobs:
                print(f"No jobs extracted from page {page_number}.")
                break

            all_jobs.extend(jobs)
            page_number += 1
            await asyncio.sleep(2)

    if all_jobs:
        save_jobs_to_csv(all_jobs, "complete_jobs.csv")
        print(f"Saved {len(all_jobs)} jobs to 'complete_jobs.csv'.")
    else:
        print("No jobs were found during the crawl.")

    llm_strategy.show_usage()

async def main():
    await crawl_jobs()

if __name__ == "__main__":
    asyncio.run(main())