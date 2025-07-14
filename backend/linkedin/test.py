import asyncio
import json
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from dotenv import load_dotenv

load_dotenv()

# Load LinkedIn storage state
try:
    with open("linkedin_storage.json", "r") as f:
        LINKEDIN_STORAGE_STATE = json.load(f)
    print("✅ LinkedIn storage state loaded")
except FileNotFoundError:
    print("❌ linkedin_storage.json not found")
    LINKEDIN_STORAGE_STATE = None

async def test_linkedin_access():
    """Simple test to see if we can access LinkedIn"""
    
    # Configure browser
    browser_config = BrowserConfig(
        browser_type="chromium",
        headless=False,
        verbose=True,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        storage_state=LINKEDIN_STORAGE_STATE,
    )
    
    url = "https://www.linkedin.com/jobs/search/?keywords=intern"
    
    print(f"🔗 Testing URL: {url}")
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        try:
            # Simple crawl without complex config
            result = await crawler.arun(url=url)
            
            if result.success:
                print(f"✅ Successfully accessed LinkedIn")
                print(f"📏 Content length: {len(result.html)}")
                print(f"📄 Cleaned content length: {len(result.cleaned_html)}")
                
                # Save the content to inspect
                with open("linkedin_raw_content.html", "w", encoding="utf-8") as f:
                    f.write(result.html)
                    
                with open("linkedin_cleaned_content.html", "w", encoding="utf-8") as f:
                    f.write(result.cleaned_html)
                    
                print("💾 Saved content to linkedin_raw_content.html and linkedin_cleaned_content.html")
                
                # Check for key indicators
                content_lower = result.cleaned_html.lower()
                
                checks = {
                    "LinkedIn page": "linkedin" in content_lower,
                    "Jobs content": "job" in content_lower,
                    "Search results": "search" in content_lower,
                    "Login required": "sign in" in content_lower,
                    "Rate limited": "rate limit" in content_lower,
                    "Captcha": "captcha" in content_lower,
                }
                
                print("\n🔍 Content analysis:")
                for check, found in checks.items():
                    status = "✅" if found else "❌"
                    print(f"   {status} {check}")
                
                # Look for job-related elements
                job_indicators = [
                    "job-card",
                    "jobs-search",
                    "job-result",
                    "artdeco-card",
                    "job-tile",
                ]
                
                print("\n🎯 Job-related elements found:")
                for indicator in job_indicators:
                    if indicator in content_lower:
                        print(f"   ✅ {indicator}")
                    else:
                        print(f"   ❌ {indicator}")
                
                return True
                
            else:
                print(f"❌ Failed to access LinkedIn: {result.error_message}")
                return False
                
        except Exception as e:
            print(f"❌ Exception occurred: {e}")
            import traceback
            traceback.print_exc()
            return False

async def main():
    """Run the LinkedIn access test"""
    print("🚀 Starting LinkedIn Access Test")
    print("=" * 50)
    
    success = await test_linkedin_access()
    
    if success:
        print("\n✅ Test completed successfully!")
        print("Check the saved HTML files to see what LinkedIn returned.")
    else:
        print("\n❌ Test failed. Check the error messages above.")

if __name__ == "__main__":
    asyncio.run(main())