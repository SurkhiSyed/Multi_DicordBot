import json
from playwright.async_api import async_playwright
import asyncio

async def main():
    with open("linkedin_cookies.json", "r") as f:
        cookies = json.load(f)

    # Fix sameSite values
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
        await page.goto("https://www.linkedin.com/jobs/")
        await page.wait_for_timeout(5000)
        await browser.close()

asyncio.run(main())