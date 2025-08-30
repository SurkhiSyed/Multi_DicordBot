import asyncio
import json
import csv
import os
from typing import List
from dotenv import load_dotenv
import nodriver as uc
from bs4 import BeautifulSoup
from model.indeed import Indeed
from indeed_parser import IndeedJobParser

load_dotenv()

class NoDriverIndeedScraper:
    def __init__(self):
        self.jobs: List[Indeed] = []
        self.browser = None
        self.main_tab = None
        
    async def setup_browser(self):
        """Setup nodriver browser with authentication"""
        print("🔧 Setting up browser for Indeed...")
        
        browser_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-gpu",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
            "--disable-popup-blocking",  # Allow popups for OAuth
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        
        self.browser = await uc.start(
            browser_args=browser_args,
            headless=False  # Keep visible for Google OAuth
        )
        
        # Get the main tab
        self.main_tab = await self.browser.get("about:blank")
        
        print("✅ Browser setup complete")

    async def login_to_indeed_with_google(self, gmail_email: str = None, gmail_password: str = None):
        """Handle Indeed login via Google OAuth with popup handling"""
        print("🔑 Attempting to login to Indeed with Google...")
        
        # Use provided credentials or fall back to environment variables
        email = gmail_email or os.getenv("GOOGLE_EMAIL")
        password = gmail_password or os.getenv("GOOGLE_PASSWORD")

        if not email or not password:
            print("❌ Google credentials not found")
            print("💡 Please provide credentials or set GOOGLE_EMAIL and GOOGLE_PASSWORD in your .env file")
            return False
            
        try:
            # Navigate to Indeed sign in page
            print("🌐 Navigating to Indeed login page...")
            await self.main_tab.get("https://secure.indeed.com/account/login")
            await asyncio.sleep(5)

            # Wait for page to fully load
            try:
                await self.main_tab.wait_for('body', timeout=15)
                print("✅ Page loaded successfully")
            except Exception as e:
                print(f"⚠️ Page load timeout: {e}")

            # Look for Google sign-in button
            print("🔍 Looking for Google sign-in button...")
            
            google_login_button = None
            
            # Try the selector that worked
            try:
                google_login_button = await self.main_tab.select('button[data-tn-element="login-google-button"]')
                if google_login_button:
                    print("✅ Found Google button using data-tn-element")
            except Exception as e:
                print(f"❌ Error finding Google button: {e}")
                return False
            
            if not google_login_button:
                print("❌ Google sign-in button not found")
                return False

            # Get current tab count before clicking
            initial_tabs = await self.browser.get_all_tabs()
            initial_tab_count = len(initial_tabs)
            
            print("🎯 Found Google sign-in button, clicking...")
            await google_login_button.click()
            await asyncio.sleep(3)

            # Wait for popup to appear
            print("⏳ Waiting for Google OAuth popup...")
            popup_tab = None
            
            for i in range(15):  # Wait up to 15 seconds for popup
                current_tabs = await self.browser.get_all_tabs()
                
                if len(current_tabs) > initial_tab_count:
                    # New tab/popup appeared, find the Google OAuth tab
                    for tab in current_tabs:
                        try:
                            tab_url = await tab.evaluate("window.location.href")
                            if "accounts.google.com" in tab_url:
                                popup_tab = tab
                                print(f"🔐 Found Google OAuth popup: {tab_url}")
                                break
                        except:
                            continue
                    
                    if popup_tab:
                        break
                
                await asyncio.sleep(1)
            
            if not popup_tab:
                print("❌ Google OAuth popup not found")
                # Check if redirect happened in main tab instead
                main_url = await self.main_tab.evaluate("window.location.href")
                if "accounts.google.com" in main_url:
                    print("🔐 Google OAuth opened in main tab instead of popup")
                    popup_tab = self.main_tab
                else:
                    print(f"❌ Main tab URL: {main_url}")
                    return False

            # Handle Google OAuth in the popup/tab
            print("🔐 Handling Google OAuth flow...")
            
            # Wait for email field
            try:
                await popup_tab.wait_for('input[type="email"], #identifierId', timeout=10)
                print("✅ Email field found")
            except:
                print("⚠️ Email field not found immediately")
            
            # Enter email
            email_field = await popup_tab.select('input[type="email"], #identifierId')
            if email_field:
                await email_field.clear_all()
                await email_field.send_keys(email)
                await asyncio.sleep(2)
                
                # Click Next
                next_button = await popup_tab.select('#identifierNext, button:contains("Next"), [data-testid="next-button"]')
                if next_button:
                    await next_button.click()
                    await asyncio.sleep(4)
                    print("✅ Email entered, clicked Next")
            else:
                print("❌ Email field not found")
                return False
            
            # Wait for password field
            try:
                await popup_tab.wait_for('input[type="password"], input[name="password"]', timeout=10)
                print("✅ Password field found")
            except:
                print("⚠️ Password field not found immediately")
            
            # Enter password
            password_field = await popup_tab.select('input[type="password"], input[name="password"]')
            if password_field:
                await password_field.send_keys(password)
                await asyncio.sleep(2)
                
                # Click Next/Sign In
                password_next = await popup_tab.select('#passwordNext, button:contains("Next"), button:contains("Sign in"), [data-testid="signin-button"]')
                if password_next:
                    await password_next.click()
                    await asyncio.sleep(5)
                    print("✅ Password entered, clicked Sign In")
            else:
                print("❌ Password field not found")
                return False

            # Handle potential 2FA or verification
            try:
                current_url = await popup_tab.evaluate("window.location.href")
                print(f"🔗 OAuth URL after login: {current_url}")
                
                if any(keyword in current_url for keyword in ["challenge", "verify", "factor", "signin/v2"]):
                    print("🔐 Google 2FA/Verification detected")
                    print("👀 Please complete the verification manually in the popup window")
                    
                    # Wait for manual intervention
                    print("⏳ Waiting for you to complete verification (up to 5 minutes)...")
                    
                    # Monitor both popup and main tab for completion
                    for i in range(60):  # 60 * 5 seconds = 5 minutes
                        await asyncio.sleep(5)
                        
                        # Check if popup closed (sign of completion)
                        try:
                            popup_url = await popup_tab.evaluate("window.location.href")
                            if "indeed.com" in popup_url:
                                print("✅ OAuth completed, popup redirected to Indeed")
                                break
                        except:
                            # Popup might have closed
                            print("🔄 Popup might have closed, checking main tab...")
                        
                        # Check main tab for login
                        try:
                            main_url = await self.main_tab.evaluate("window.location.href")
                            if "indeed.com" in main_url and "login" not in main_url:
                                print("✅ Main tab shows successful login")
                                break
                        except:
                            pass
                        
                        if i % 12 == 0:  # Print progress every minute
                            print(f"⏳ Still waiting... ({i//12 + 1}/5 minutes)")
                    
                else:
                    # Wait for OAuth completion
                    print("⏳ Waiting for OAuth completion...")
                    
                    for i in range(20):  # Wait up to 20 seconds
                        try:
                            # Check if popup redirected back to Indeed
                            popup_url = await popup_tab.evaluate("window.location.href")
                            if "indeed.com" in popup_url:
                                print("✅ OAuth completed successfully")
                                break
                        except:
                            # Popup might have closed, check main tab
                            try:
                                main_url = await self.main_tab.evaluate("window.location.href")
                                if "indeed.com" in main_url and "login" not in main_url:
                                    print("✅ OAuth completed, main tab updated")
                                    break
                            except:
                                pass
                        
                        await asyncio.sleep(1)
            except Exception as e:
                print(f"⚠️ Error during OAuth completion check: {e}")

            # Final verification - check main tab for login status
            await asyncio.sleep(3)
            try:
                main_url = await self.main_tab.evaluate("window.location.href")
                print(f"🔗 Final main tab URL: {main_url}")
                
                # Navigate to Indeed home page to verify login
                await self.main_tab.get("https://indeed.com")
                await asyncio.sleep(3)
                
                # Check for login indicators
                try:
                    # Look for profile indicators
                    profile_indicators = await self.main_tab.select('a[data-testid="gnav-profile-menu"], [data-testid="user-menu"], a:contains("Sign out"), [data-testid="gnav-profile-dropdown"]')
                    
                    if profile_indicators:
                        print("✅ Successfully logged in to Indeed via Google")
                        return True
                    else:
                        print("⚠️ Login status unclear, checking manually...")
                        # Manual verification
                        user_input = input("Check the Indeed homepage - are you logged in? (you should see your profile/avatar in top right). Press Enter if yes, 'n' if no: ")
                        return user_input.lower() != 'n'
                except Exception as e:
                    print(f"⚠️ Error checking login status: {e}")
                    user_input = input("Please manually check if you're logged in to Indeed. Press Enter to continue, 'n' to abort: ")
                    return user_input.lower() != 'n'
                    
            except Exception as e:
                print(f"❌ Error during final verification: {e}")
                return False
                    
        except Exception as e:
            print(f"❌ Error during Google OAuth login: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def scrape_jobs(self, keywords: str = "intern", location: str = "", max_pages: int = 8):
        """Scrape Indeed jobs after authentication"""
        print(f"🔍 Starting to scrape Indeed jobs for '{keywords}' in '{location}'...")
        
        for page in range(max_pages):
            start = page * 10  # Indeed typically shows 10 jobs per page
            
            # Build Indeed search URL
            base_url = "https://www.indeed.com/jobs"
            params = f"q={keywords.replace(' ', '+')}"
            if location:
                params += f"&l={location.replace(' ', '+')}"
            params += f"&start={start}"
            
            url = f"{base_url}?{params}"
            
            print(f"📄 Scraping page {page + 1}: {url}")
            
            try:
                # Navigate to the jobs page
                await self.main_tab.get(url)
                
                # Wait for the page to load
                await asyncio.sleep(4)
                
                # Wait for job listings to appear
                try:
                    await self.main_tab.wait_for('[data-testid="job-title"], .jobTitle, [data-jk]', timeout=15)
                    print("✅ Job listings loaded")
                except:
                    print("⚠️ Job results not found with primary selectors, trying alternatives...")
                
                # Scroll down to trigger lazy loading
                print("📜 Scrolling to load more job content...")
                await self.main_tab.evaluate("""
                    (async () => {
                        const scrollHeight = document.body.scrollHeight;
                        const scrollStep = scrollHeight / 4;
                        
                        for (let i = 1; i <= 4; i++) {
                            window.scrollTo(0, scrollStep * i);
                            await new Promise(resolve => setTimeout(resolve, 1000));
                        }
                        
                        // Scroll back to top
                        window.scrollTo(0, 0);
                        await new Promise(resolve => setTimeout(resolve, 500));
                    })();
                """)
                
                await asyncio.sleep(3)
                
                # Get the page HTML
                html_content = await self.main_tab.evaluate("document.documentElement.outerHTML")
                
                # Save debug HTML
                with open(f"indeed_debug_page_{page + 1}.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                print(f"💾 Saved HTML to indeed_debug_page_{page + 1}.html")
                
                # Extract jobs from HTML using Indeed parser
                jobs_data = IndeedJobParser.extract_jobs_from_html(html_content)
                self.jobs.extend(jobs_data)
                
                print(f"✅ Found {len(jobs_data)} jobs on page {page + 1}")
                
                # Check if we've reached the end of results
                if len(jobs_data) == 0:
                    print("📭 No more jobs found, stopping pagination")
                    break
                
                # Be respectful with requests
                await asyncio.sleep(4)
                
            except Exception as e:
                print(f"❌ Error scraping page {page + 1}: {e}")
                continue
                
        return self.jobs
    
    def save_to_csv(self, filename: str = "indeed_jobs_nodriver.csv"):
        """Save scraped jobs to CSV file"""
        if not self.jobs:
            print("⚠️ No jobs to save")
            return
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['name', 'company', 'location_type', 'job_type', 'application_link', 'location', 'description']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for job in self.jobs:
                writer.writerow(job.model_dump())
        
        print(f"💾 Saved {len(self.jobs)} jobs to {filename}")
    
    async def close(self):
        """Close the browser safely"""
        try:
            if self.browser is not None:
                if hasattr(self.browser, 'stop') and callable(getattr(self.browser, 'stop', None)):
                    await self.browser.stop()
                    print("🔒 Browser closed successfully")
                else:
                    print("🔒 Browser stop method not available")
            else:
                print("🔒 Browser was not initialized")
        except Exception as e:
            print(f"⚠️ Error closing browser (this is usually safe to ignore): {e}")
        finally:
            self.browser = None
            self.main_tab = None

async def main(gmail_email: str = None, gmail_password: str = None, keywords: str = "intern", location: str = ""):
    scraper = NoDriverIndeedScraper()
    scraped_jobs = []

    try:
        # Setup browser
        await scraper.setup_browser()
        
        # Login to Indeed via Google
        login_success = await scraper.login_to_indeed_with_google(gmail_email, gmail_password)
        
        if login_success:
            # Scrape jobs
            jobs = await scraper.scrape_jobs(keywords=keywords, location=location, max_pages=8)
            scraped_jobs = jobs
            
            # Save results
            scraper.save_to_csv()
            
            print(f"🎉 Indeed scraping completed! Found {len(jobs)} total jobs.")
        else:
            print("❌ Login failed, cannot proceed with scraping")
            
    except KeyboardInterrupt:
        print("\n⏹️ Scraping interrupted by user")
    except Exception as e:
        print(f"❌ Error during scraping: {e}")
        print(f"✅ Successfully scraped {len(scraped_jobs)} jobs before cleanup")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        await scraper.close()
        print("🏁 Cleanup completed")
        
    return scraped_jobs

if __name__ == "__main__":
    asyncio.run(main())

