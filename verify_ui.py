from playwright.sync_api import sync_playwright
import time
import subprocess
import os

def run():
    print("Starting Astro dev server...")

    env = os.environ.copy()
    env["__VITE_ADDITIONAL_SERVER_ALLOWED_HOSTS"] = ".com"

    server = subprocess.Popen(
        ["pnpm", "run", "dev", "--host", "0.0.0.0", "--port", "3000"],
        cwd="dashboard",
        env=env
    )
    time.sleep(10)  # Wait for server to start

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print("Navigating to admin perf page...")
        page.goto("http://localhost:3000/causaganha/admin/perf")
        page.wait_for_load_state("networkidle")

        # Wait for widget to appear
        time.sleep(5)

        print("Taking screenshot...")
        os.makedirs("verification", exist_ok=True)
        page.screenshot(path="verification/live_status_screenshot.png")
        print("Screenshot saved to verification/live_status_screenshot.png")

        browser.close()

    server.terminate()
    print("Verification script finished.")

if __name__ == "__main__":
    run()