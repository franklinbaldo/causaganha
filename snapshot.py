from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("http://localhost:3000/causaganha/stats")
    page.wait_for_selector("h1")
    time.sleep(2)  # Allow fetch to complete
    page.screenshot(path="stats.png", full_page=True)

    page.goto("http://localhost:3000/causaganha/")
    page.wait_for_selector("h1")
    time.sleep(2)
    page.screenshot(path="dashboard.png")

    browser.close()
