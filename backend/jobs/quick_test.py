"""
Quick test for the improved LinkedIn scraper
"""
import asyncio
from main_nodriver import NoDriverLinkedInScraper

async def quick_test():
    """Test the scraper with just one page"""
    print("🧪 Quick test of the improved LinkedIn scraper...")
    
    scraper = NoDriverLinkedInScraper()
    
    try:
        await scraper.setup_browser()
        
        # Skip login for now, just test the extraction on public pages
        print("⏭️ Skipping login for quick test...")
        
        # Try to scrape just one page
        jobs = await scraper.scrape_jobs(keywords="software engineer", max_pages=1)
        
        if jobs:
            print(f"\n✅ Found {len(jobs)} jobs!")
            for i, job in enumerate(jobs[:3]):  # Show first 3
                print(f"\n📋 Job {i+1}:")
                print(f"   Title: {job.name}")
                print(f"   Company: {job.company}")
                print(f"   Location: {job.location}")
                print(f"   Type: {job.job_type}")
        else:
            print("⚠️ No jobs found in quick test")
            
        scraper.save_to_csv("quick_test_jobs.csv")
        
    except Exception as e:
        print(f"❌ Error in quick test: {e}")
    finally:
        await scraper.close()

if __name__ == "__main__":
    asyncio.run(quick_test())
