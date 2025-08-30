"""
Test LinkedIn scraper without authentication first
"""
import asyncio
import nodriver as uc
from bs4 import BeautifulSoup
import json

async def test_linkedin_access():
    """Test if we can access LinkedIn job pages without authentication"""
    print("🧪 Testing LinkedIn access...")
    
    try:
        # Start browser
        browser = await uc.start(headless=False)
        page = await browser.get("about:blank")
        
        # Try to access a public job search page
        test_urls = [
            "https://www.linkedin.com/jobs/search/?keywords=software%20engineer&location=United%20States",
            "https://www.linkedin.com/jobs/search/?keywords=intern",
            "https://www.linkedin.com/jobs/"
        ]
        
        for i, url in enumerate(test_urls):
            print(f"\n📄 Testing URL {i+1}: {url}")
            
            try:
                await page.get(url)
                await asyncio.sleep(5)
                
                # Get page content
                html_content = await page.evaluate("document.documentElement.outerHTML")
                
                # Save for analysis
                filename = f"test_access_{i+1}.html"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(html_content)
                
                # Check if we got a login page or actual content
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Look for signs of login requirement
                login_indicators = soup.find_all(text=lambda text: text and any(
                    phrase in text.lower() for phrase in ['sign in', 'log in', 'join linkedin']
                ))
                
                # Look for job-related content
                job_indicators = soup.select('li[data-occludable-job-id], .job-search-card, .base-search-card')
                
                print(f"   📝 Content length: {len(html_content)}")
                print(f"   🔐 Login indicators: {len(login_indicators)}")
                print(f"   💼 Job cards found: {len(job_indicators)}")
                print(f"   💾 Saved to: {filename}")
                
                if job_indicators:
                    print(f"   ✅ Found job content! ({len(job_indicators)} job cards)")
                    break
                elif login_indicators:
                    print(f"   🚫 Login required detected")
                else:
                    print(f"   ❓ Unclear page content")
                    
            except Exception as e:
                print(f"   ❌ Error accessing {url}: {e}")
        
        # Close browser
        await browser.stop()
        
    except Exception as e:
        print(f"❌ Browser error: {e}")

if __name__ == "__main__":
    asyncio.run(test_linkedin_access())
