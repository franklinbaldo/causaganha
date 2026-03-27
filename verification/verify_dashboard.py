import asyncio
from playwright.async_api import async_playwright

async def verify():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto("http://localhost:8080/causaganha/")
        await page.wait_for_selector('text=Filtros', timeout=10000)

        # Check active filters logic by changing status dropdown
        await page.select_option('select:has(option[value="active"])', value="active")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="verification/dashboard_filtered.png")

        # Select all filtered
        await page.check('input[type="checkbox"]:right-of(:text("Selecionar todos"))')
        await page.wait_for_timeout(1000)
        await page.screenshot(path="verification/dashboard_selected.png")

        print("Verification completed successfully")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify())
