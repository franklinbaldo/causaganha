from playwright.sync_api import sync_playwright
import time
import subprocess
import os

def run_cuj(page):
    print("Navigating to admin perf page...")
    page.goto("http://localhost:3000/causaganha/admin/perf")
    page.wait_for_load_state("networkidle")

    # Wait for widget to appear
    page.wait_for_timeout(5000)

    print("Taking screenshot...")
    page.screenshot(path="/home/jules/verification/screenshots/verification.png")
    page.wait_for_timeout(1000)  # Hold final state for the video

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
        context = browser.new_context(
            record_video_dir="/home/jules/verification/videos"
        )
        page = context.new_page()
        try:
            run_cuj(page)
        finally:
            context.close()  # MUST close context to save the video
            browser.close()

    server.terminate()
    print("Verification script finished.")

if __name__ == "__main__":
    run()