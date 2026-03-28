import subprocess
import time

from playwright.sync_api import sync_playwright


def run() -> None:
    # Build astro first to serve static pages
    subprocess.run(["pnpm", "install"], cwd="dashboard")
    subprocess.run(["pnpm", "build"], cwd="dashboard")
    server = subprocess.Popen(["pnpm", "preview", "--port", "4321"], cwd="dashboard")
    time.sleep(3)  # Wait for server to start

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate to index to check TribunalView updates
        page.goto("http://localhost:4321/causaganha/")
        page.wait_for_selector("text=CausaGanha")

        # Take screenshot of the index
        page.screenshot(path="verification/index_screenshot.png")

        # Navigate to admin/perf
        page.goto("http://localhost:4321/causaganha/admin/perf")
        page.wait_for_selector("text=Performance Monitoring", timeout=5000)

        # Take screenshot of the admin/perf page
        page.screenshot(path="verification/admin_perf_screenshot.png")

        browser.close()

    server.terminate()


if __name__ == "__main__":
    run()
