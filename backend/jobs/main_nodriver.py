import asyncio
import json
import csv
import os
import urllib.parse
import inspect
from typing import List
from dotenv import load_dotenv
import nodriver as uc
from bs4 import BeautifulSoup
from jobs.model.linkedin import Linkedin
from jobs.linkedin_parser import LinkedInJobParser
from random import uniform
from jobs.linkedin_parser import LinkedInJobParser, extract_description_from_job_html

load_dotenv()

class NoDriverLinkedInScraper:
    def __init__(self):
        self.jobs: List[Linkedin] = []
        self.browser = None
        self.main_tab = None
        
    async def setup_browser(self):
        """Setup nodriver browser with authentication"""
        print("🔧 Setting up browser...")
        
        browser_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-gpu",
        ]
        
        self.browser = await uc.start(
            browser_args=browser_args,
            headless=False  # Keep visible for debugging
        )
        
        # Get the main tab
        self.main_tab = await self.browser.get("about:blank")
        # NEW: a dedicated tab for job detail pages
        self.detail_tab = await self.browser.get("about:blank")
        
        # Setup authentication handlers
        #self.main_tab.add_handler(uc.cdp.fetch.RequestPaused, self.req_paused)
        #self.main_tab.add_handler(uc.cdp.fetch.AuthRequired, self.auth_challenge_handler)
        #await self.main_tab.send(uc.cdp.fetch.enable(handle_auth_requests=True))
        
        print("✅ Browser setup complete")

    async def login_to_linkedin(self, linkedin_username: str = None, linkedin_password: str = None):
        """Handle LinkedIn login"""
        print("🔑 Attempting to login to LinkedIn...")
        
        # Navigate to LinkedIn login page
        await self.main_tab.get("https://www.linkedin.com/login")
        await asyncio.sleep(3)

        # Use provided credentials or fall back to environment variables
        username = linkedin_username or os.getenv("LINKEDIN_USERNAME")
        password = linkedin_password or os.getenv("LINKEDIN_PASSWORD")

        if not username or not password:
            print("❌ LinkedIn credentials not found")
            print("💡 Please provide credentials or set LINKEDIN_USERNAME and LINKEDIN_PASSWORD in your .env file")
            return False
            
        try:
            # Fill in credentials
            username_field = await self.main_tab.select("#username")
            if username_field:
                await username_field.send_keys(username)
                
            password_field = await self.main_tab.select("#password")
            if password_field:
                await password_field.send_keys(password)
                
            # Click login button
            login_button = await self.main_tab.select('button[type="submit"]')
            if login_button:
                await login_button.click()
                
            # Wait for login to complete
            await asyncio.sleep(5)
            
            # Check if we're redirected to the home page or if there's a challenge
            current_url = await self.main_tab.evaluate("window.location.href")
            
            if "feed" in current_url or "in/" in current_url:
                print("✅ Successfully logged in to LinkedIn")
                return True
            elif "challenge" in current_url:
                print("⚠️ LinkedIn security challenge detected")
                print("👀 Please complete the challenge manually in the browser")
                # Wait for manual intervention
                input("Press Enter after completing the challenge...")
                return True
            else:
                print("⚠️ Login may have failed, please check manually")
                return True  # Let's try to continue anyway
                
        except Exception as e:
            print(f"❌ Error during login: {e}")
            return False
    
    async def scrape_jobs(self, keywords: str = "intern", location: str = "", max_pages: int = 8):
        """Scrape LinkedIn jobs after authentication"""
        print(f"🔍 Starting to scrape LinkedIn jobs for '{keywords}' in '{location or 'Any location'}'...")
        
        for page in range(max_pages):
            start = page * 7  # Use 7-job increments since that's what we consistently get
            
            # Build URL with proper encoding
            base_url = "https://www.linkedin.com/jobs/search/"
            params = {
                "keywords": keywords,
                "start": str(start)
            }
            
            # Add location if provided
            if location.strip():
                params["location"] = location.strip()
                
            # Build the query string
            query_string = urllib.parse.urlencode(params)
            url = f"{base_url}?{query_string}"
            
            print(f"📄 Scraping page {page + 1}: {url}")
            
            try:
                # Navigate to the jobs page
                await self.main_tab.get(url)
                
                # Wait for the page to load
                await asyncio.sleep(5)
                
                # Wait for job listings to appear
                try:
                    await self.main_tab.wait_for('.jobs-search-results__list', timeout=10)
                except:
                    print("⚠️ Job results list not found, trying alternative selectors...")
                
                # Scroll down to trigger lazy loading of job cards
                print("📜 Scrolling to load more job content...")
                await self.main_tab.evaluate("""
                    // Scroll down gradually to trigger lazy loading
                    const scrollHeight = document.body.scrollHeight;
                    const scrollStep = scrollHeight / 5;
                    
                    for (let i = 1; i <= 5; i++) {
                        window.scrollTo(0, scrollStep * i);
                        await new Promise(resolve => setTimeout(resolve, 500));
                    }
                    
                    // Scroll back to top
                    window.scrollTo(0, 0);
                """)
                
                # Wait a bit more for content to load
                await asyncio.sleep(2)
                
                # Try to click on some job cards to trigger content loading
                print("🔄 Triggering job card content loading...")
                await self.main_tab.evaluate("""
                    // Find job cards and trigger hover/focus events to load content
                    const jobCards = document.querySelectorAll('li[data-occludable-job-id]');
                    jobCards.forEach((card, index) => {
                        if (index < 10) { // Only trigger first 10 to avoid too much delay
                            card.dispatchEvent(new Event('mouseenter'));
                            card.dispatchEvent(new Event('focus'));
                        }
                    });
                """)
                
                # Wait for the content to potentially load
                await asyncio.sleep(3)
                
                # Get the page HTML
                html_content = await self.main_tab.evaluate("document.documentElement.outerHTML")
                
                # Save debug HTML
                with open(f"nodriver_debug_page_{page + 1}.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                print(f"💾 Saved HTML to nodriver_debug_page_{page + 1}.html")
                
                # Extract jobs from HTML (pydantic objects)
                jobs_objs = LinkedInJobParser.extract_jobs_from_html(html_content)

                # Convert to dicts for mutation
                page_dicts = [j.model_dump() for j in jobs_objs]

                # Enrich (sequential, in dedicated tab)
                await self._enrich_jobs_with_descriptions(page_dicts)

                # Push enriched descriptions back into models
                for src, upd in zip(jobs_objs, page_dicts):
                    src.description = upd.get("description") or src.description

                self.jobs.extend(jobs_objs)
                print(f"✅ Found {len(jobs_objs)} jobs on page {page + 1}")

                # Be respectful with requests
                await asyncio.sleep(3)
                
            except Exception as e:
                print(f"❌ Error scraping page {page + 1}: {e}")
                continue
                
        return self.jobs
    
    async def auth_challenge_handler(self, event: uc.cdp.fetch.AuthRequired):
        """Handle authentication challenges"""
        print("🔐 Handling authentication challenge...")
        asyncio.create_task(
            self.main_tab.send(
                uc.cdp.fetch.continue_with_auth(
                    request_id=event.request_id,
                    auth_challenge_response=uc.cdp.fetch.AuthChallengeResponse(
                        response="ProvideCredentials",
                        username=os.getenv("LINKEDIN_USERNAME"),
                        password=os.getenv("LINKEDIN_PASSWORD")
                    ),
                )
            )
        )

    async def req_paused(self, event: uc.cdp.fetch.RequestPaused):
        """Handle paused requests"""
        asyncio.create_task(
            self.main_tab.send(
                uc.cdp.fetch.continue_request(
                    request_id=event.request_id
                )
            )
        )
    
    def save_to_csv(self, filename: str = "linkedin_jobs_nodriver.csv"):
        """Save scraped jobs to CSV file"""
        if not self.jobs:
            print("⚠️ No jobs to save")
            return
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['name', 'company', 'location_type', 'job_type', 'posting_date', 'application_link', 'location', 'description']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for job in self.jobs:
                writer.writerow(job.model_dump())  # Use model_dump() instead of dict()
        
        print(f"💾 Saved {len(self.jobs)} jobs to {filename}")
    
    async def close(self):
        try:
            # close detail tab (best-effort)
            if getattr(self, "detail_tab", None):
                try:
                    if hasattr(self.detail_tab, "close") and callable(self.detail_tab.close):
                        res = self.detail_tab.close()
                        if inspect.isawaitable(res): await res
                except Exception as e:
                    print(f"⚠️ detail_tab close: {e}")

            if self.browser is not None:
                if hasattr(self.browser, 'stop') and callable(self.browser.stop):
                    res = self.browser.stop()
                    if inspect.isawaitable(res): await res
                print("🔒 Browser closed successfully")
            else:
                print("🔒 Browser was not initialized")
        except Exception as e:
            print(f"⚠️ Error closing browser (safe to ignore): {e}")
        finally:
            self.browser = None
            self.main_tab = None
            self.detail_tab = None
            
    async def _fetch_job_description(self, url: str, timeout: int = 15, retries: int = 1) -> str:
        """
        Navigate to the job detail page and extract the 'About the job' text.
        Works for both right-rail and standalone job pages.
        """
        if not url:
            return ""
        tab = self.detail_tab  # <- use the dedicated tab

        for attempt in range(retries + 1):
            try:
                await tab.get(url)
                # wait for something meaningful to exist
                try:
                    await tab.wait_for(
                        'div.show-more-less-html__markup, div.jobs-description-content__text, '
                        'div.jobs-box__html-content, button.show-more-less-html__button',
                        timeout=timeout
                    )
                except Exception:
                    # No known containers found yet; continue anyway (we’ll still snapshot HTML)
                    pass

                # try to expand
                try:
                    await tab.evaluate("""
                        (function(){
                            const b = document.querySelector('button.show-more-less-html__button');
                            if (b && /show more/i.test(b.innerText)) b.click();
                        })();
                    """)
                    await asyncio.sleep(0.5)
                except Exception:
                    pass

                html = await tab.evaluate("document.documentElement.outerHTML")
                desc = extract_description_from_job_html(html)
                if desc:
                    return desc

            except Exception as e:
                print(f"⚠️ detail fetch attempt {attempt+1} failed: {e}")

            # gentle backoff
            await asyncio.sleep(0.8 + uniform(0, 0.6))

        return ""

    async def _enrich_jobs_with_descriptions(self, jobs: list, limit: int | None = None, per_job_timeout: int = 25):
        """
        Visit each job's detail page in the dedicated detail tab and fill 'description'.
        Sequential on purpose: avoids tab navigation races & CDP 'Invalid InterceptionId'.
        """
        target = jobs if limit is None else jobs[:max(0, limit)]
        for idx, job in enumerate(target, 1):
            link = job.get("application_link")
            if not link:
                job["description"] = ""
                continue

            print(f"🧭 [desc] {idx}/{len(target)} -> {link}")
            try:
                # hard timeout to prevent any single stuck job from hanging the whole run
                job["description"] = await asyncio.wait_for(
                    self._fetch_job_description(link),
                    timeout=per_job_timeout
                )
            except asyncio.TimeoutError:
                print(f"⏳ [desc] timeout for {link}")
                job["description"] = ""
            except Exception as e:
                print(f"❌ [desc] error for {link}: {e}")
                job["description"] = ""
            # small pacing to be polite
            await asyncio.sleep(0.3)

async def main(linkedin_username: str = None, linkedin_password: str = None, location: str = ""):
    scraper = NoDriverLinkedInScraper()

    try:
        # Setup browser
        await scraper.setup_browser()
        
        # Login to LinkedIn
        login_success = await scraper.login_to_linkedin(linkedin_username, linkedin_password)
        
        if login_success:
            # Scrape jobs with location
            jobs = await scraper.scrape_jobs(keywords="intern", location=location, max_pages=8)
            
            # Save results
            scraper.save_to_csv()
            
            print(f"🎉 Scraping completed! Found {len(jobs)} total jobs.")
        else:
            print("❌ Login failed, cannot proceed with scraping")
            
    except KeyboardInterrupt:
        print("\n⏹️ Scraping interrupted by user")
    except Exception as e:
        print(f"❌ Error during scraping: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up - this will handle the browser properly
        await scraper.close()
        print("🏁 Cleanup completed")

if __name__ == "__main__":
    asyncio.run(main())
