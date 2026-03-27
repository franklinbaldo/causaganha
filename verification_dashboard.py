from playwright.sync_api import sync_playwright

def run_cuj(page):
    page.goto("http://localhost:4321/causaganha")
    page.wait_for_timeout(2000)

    # 1. Take a screenshot of the initial load (shows STF)
    page.screenshot(path="/home/jules/verification/screenshots/verification_stf.png", full_page=True)
    page.wait_for_timeout(1000)

    # 2. Select another tribunal, e.g., TST
    page.get_by_role("combobox", name="Select Tribunal").select_option("TST")
    page.wait_for_timeout(2000)

    # Take screenshot of the TST view
    page.screenshot(path="/home/jules/verification/screenshots/verification_tst.png", full_page=True)
    page.wait_for_timeout(1000)

    # 3. Select another tribunal, e.g., TRF3
    page.get_by_role("combobox", name="Select Tribunal").select_option("TRF3")
    page.wait_for_timeout(2000)

    # Take screenshot of the TRF3 view
    page.screenshot(path="/home/jules/verification/screenshots/verification_trf3.png", full_page=True)
    page.wait_for_timeout(1000)

if __name__ == "__main__":
    import os
    os.makedirs("/home/jules/verification/screenshots", exist_ok=True)
    os.makedirs("/home/jules/verification/videos", exist_ok=True)
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