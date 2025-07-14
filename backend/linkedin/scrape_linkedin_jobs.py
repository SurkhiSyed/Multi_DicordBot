import json
import csv
from playwright.async_api import async_playwright
import asyncio

async def main():
    with open("linkedin_cookies.json", "r") as f:
        cookies = json.load(f)
    valid_same_site = {"Strict", "Lax", "None"}
    for cookie in cookies:
        if "sameSite" not in cookie or cookie["sameSite"] not in valid_same_site:
            cookie["sameSite"] = "Lax"
        if 'domain' not in cookie or not cookie['domain']:
            cookie['domain'] = '.linkedin.com'

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        await context.add_cookies(cookies)
        page = await context.new_page()

        jobs = []
        # Let's say you want to scrape the first 5 pages (0, 25, 50, 75, 100)
        for job_number in range(0, 125, 25):  # Adjust 125 to scrape more/less pages
            base_url = "https://www.linkedin.com/jobs/search-results/?keywords=intern&origin=JOB_COLLECTION_PAGE_SEARCH_BUTTON"
            start_number = (job_number - 1) * 25
            url = f"{base_url}&start={start_number}"
            print(f"Scraping: {url}")
            await page.goto(url)
            await page.wait_for_timeout(3000)  # Wait for page to load

            job_cards = await page.query_selector_all('.jobs-search__results-list li')
            for card in job_cards:
                title = await card.query_selector_eval('h3', 'el => el.innerText') if await card.query_selector('h3') else ''
                company = await card.query_selector_eval('.base-search-card__subtitle', 'el => el.innerText') if await card.query_selector('.base-search-card__subtitle') else ''
                location = await card.query_selector_eval('.job-search-card__location', 'el => el.innerText') if await card.query_selector('.job-search-card__location') else ''
                link = await card.query_selector_eval('a', 'el => el.href') if await card.query_selector('a') else ''
                jobs.append({
                    "name": title,
                    "company": company,
                    "location": location,
                    "application_link": link,
                    # Add more fields as needed
                })

        # Save to CSV
        if jobs:
            with open("linkedin_jobs.csv", "w", newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=jobs[0].keys())
                writer.writeheader()
                writer.writerows(jobs)
            print(f"Saved {len(jobs)} jobs to linkedin_jobs.csv")
        else:
            print("No jobs found.")

        await browser.close()

asyncio.run(main())