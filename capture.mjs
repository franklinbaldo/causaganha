import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  // Navigate to the local server
  await page.goto('http://127.0.0.1:3000/');

  // Wait for the specific element to be present
  await page.waitForSelector('text=Dados atualizados', { timeout: 10000 });

  // Take a screenshot
  await page.screenshot({ path: 'verification10.png', fullPage: true });

  await browser.close();
})();
