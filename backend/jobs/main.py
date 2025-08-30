import asyncio
import json
import csv
from typing import List
from dotenv import load_dotenv
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from model.linkedin import Linkedin
from linkedin_parser import LinkedInJobParser

load_dotenv()

class LinkedInJobScraper:
    def __init__(self):
        self.jobs: List[Linkedin] = []
        self.storage_state = self._load_storage_state()
    
    def _load_storage_state(self):
        """Load LinkedIn session storage state"""
        try:
            with open("../linkedin/linkedin_storage.json", "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            print("⚠️ No valid LinkedIn storage state found. Manual login may be required.")
            return None
    
    async def scrape_jobs(self, keywords: str = "intern", max_pages: int = 5):
        """Scrape LinkedIn jobs using Crawl4AI"""
        print(f"🔍 Starting to scrape LinkedIn jobs for '{keywords}'...")
        
        # Create proper browser configuration
        from crawl4ai import BrowserConfig
        
        browser_config = BrowserConfig(
            headless=False,
            browser_type="chromium"
        )
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            for page in range(max_pages):
                start = page * 25
                url = f"https://www.linkedin.com/jobs/search/?keywords={keywords}&start={start}"
                
                print(f"📄 Scraping page {page + 1}: {url}")
                
                result = await crawler.arun(
                    url=url,
                    config=CrawlerRunConfig(
                        cache_mode=CacheMode.BYPASS,
                        wait_for="css:.jobs-search__results-list",
                        delay_before_return_html=3.0
                    )
                )
                
                if result.success:
                    print(f"📝 HTML content length: {len(result.cleaned_html)}")
                    
                    # Debug: Save HTML to file for inspection
                    with open(f"debug_page_{page + 1}.html", "w", encoding="utf-8") as f:
                        f.write(result.cleaned_html)
                    print(f"💾 Saved HTML to debug_page_{page + 1}.html")
                    
                    jobs_data = self._extract_jobs_from_html(result.cleaned_html)
                    self.jobs.extend(jobs_data)
                    print(f"✅ Found {len(jobs_data)} jobs on page {page + 1}")
                else:
                    print(f"❌ Failed to scrape page {page + 1}: {result.error_message}")
                
                # Be respectful with requests
                await asyncio.sleep(2)
        
        return self.jobs
    
    def _extract_jobs_from_html(self, html: str) -> List[Linkedin]:
        """Extract job information from HTML using the parser"""
        return LinkedInJobParser.extract_jobs_from_html(html)
    
    def save_to_csv(self, filename: str = "scraped_jobs.csv"):
        """Save scraped jobs to CSV file"""
        if not self.jobs:
            print("⚠️ No jobs to save")
            return
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['name', 'company', 'location_type', 'job_type', 'posting_date', 'application_link', 'location', 'description']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for job in self.jobs:
                writer.writerow(job.dict())
        
        print(f"💾 Saved {len(self.jobs)} jobs to {filename}")

async def main():
    scraper = LinkedInJobScraper()
    jobs = await scraper.scrape_jobs(keywords="intern", max_pages=3)
    scraper.save_to_csv()
    print(f"🎉 Scraping completed! Found {len(jobs)} total jobs.")
        
        
if __name__ == "__main__":
    asyncio.run(main())