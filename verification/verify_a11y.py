import subprocess
import time

from playwright.sync_api import sync_playwright


def run():
    print("Starting Astro preview server...")
    server = subprocess.Popen(["pnpm", "preview", "--port", "4321"], cwd="dashboard")
    time.sleep(3)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(record_video_dir="verification/videos")
        page = context.new_page()

        try:
            # Navigate to index
            page.goto("http://localhost:4321/causaganha/")
            page.wait_for_selector("text=CausaGanha")
            page.wait_for_timeout(1000)

            # Test 1: Command Palette (Ctrl+K)
            page.keyboard.press("Control+k")
            page.wait_for_timeout(1000)
            page.screenshot(path="verification/screenshots/command_palette.png")
            print("Captured command palette.")

            # Close palette
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)

            # Test 2: Network Status Banner (simulate slow network via JS event)
            page.evaluate("window.dispatchEvent(new CustomEvent('cg-network-slow'))")
            page.wait_for_timeout(1000)
            page.screenshot(path="verification/screenshots/network_slow.png")
            print("Captured network slow banner.")

            # Simulate error network
            page.evaluate("window.dispatchEvent(new CustomEvent('cg-network-error'))")
            page.wait_for_timeout(1000)
            page.screenshot(path="verification/screenshots/network_error.png")
            print("Captured network error banner.")

            # Test 3: Keyboard Navigation on Heatmap
            # Tab to the heatmap (it has tabIndex=0)
            # Find the grid and focus it
            page.locator('div[role="grid"]').first.focus()
            page.wait_for_timeout(500)

            # Press left arrow a few times to move focus
            page.keyboard.press("ArrowLeft")
            page.wait_for_timeout(300)
            page.keyboard.press("ArrowLeft")
            page.wait_for_timeout(300)
            page.keyboard.press("ArrowUp")
            page.wait_for_timeout(500)

            # Take screenshot showing focus ring
            page.screenshot(path="verification/screenshots/heatmap_focus.png")
            print("Captured heatmap focus.")

            # Press Enter to open tooltip
            page.keyboard.press("Enter")
            page.wait_for_timeout(1000)
            page.screenshot(path="verification/screenshots/heatmap_tooltip.png")
            print("Captured heatmap tooltip via keyboard.")

            # Close tooltip
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)

        finally:
            context.close()
            browser.close()

    server.terminate()
    print("Verification complete.")


if __name__ == "__main__":
    import os
    os.makedirs("verification/screenshots", exist_ok=True)
    os.makedirs("verification/videos", exist_ok=True)
    run()
