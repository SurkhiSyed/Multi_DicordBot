import json

with open("linkedin_cookies.json", "r") as f:
    cookies = json.load(f)

# Fix sameSite values and wrap in dict
valid_same_site = {"Strict", "Lax", "None"}
for cookie in cookies:
    # Fix sameSite
    if "sameSite" not in cookie or cookie["sameSite"] not in valid_same_site:
        cookie["sameSite"] = "Lax"
    # Remove keys not needed by Playwright/Crawl4AI
    for k in ["hostOnly", "storeId", "session"]:
        cookie.pop(k, None)
    # Fix domain if needed
    if not cookie.get("domain"):
        cookie["domain"] = ".linkedin.com"

storage_state = {"cookies": cookies}

with open("linkedin_storage.json", "w") as f:
    json.dump(storage_state, f, indent=2)