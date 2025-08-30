"""
Test script for LinkedIn job scraping
"""

import asyncio
import sys
import os

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jobs.main import LinkedInJobScraper

async def test_scraper():
    """Test the LinkedIn job scraper"""
    print("🧪 Testing LinkedIn Job Scraper...")
    
    try:
        scraper = LinkedInJobScraper()
        
        # Test with a small number of pages first
        jobs = await scraper.scrape_jobs(keywords="python developer", max_pages=1)
        
        if jobs:
            print(f"✅ Successfully scraped {len(jobs)} jobs!")
            
            # Display first few jobs
            for i, job in enumerate(jobs[:3]):
                print(f"\n📋 Job {i+1}:")
                print(f"   Title: {job.name}")
                print(f"   Company: {job.company}")
                print(f"   Location: {job.location}")
                print(f"   Type: {job.job_type}")
                print(f"   Link: {job.application_link}")
            
            # Save to test file
            scraper.save_to_csv("test_linkedin_jobs.csv")
            
        else:
            print("⚠️ No jobs found. This might indicate:")
            print("   - LinkedIn is blocking requests")
            print("   - Need to login first")
            print("   - HTML structure has changed")
            print("   - Rate limiting in effect")
            
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        print("\n💡 Possible solutions:")
        print("   - Check internet connection")
        print("   - Verify LinkedIn isn't blocking your IP")
        print("   - Try using a storage state with valid session")
        print("   - Check if HTML selectors need updating")

if __name__ == "__main__":
    asyncio.run(test_scraper())
