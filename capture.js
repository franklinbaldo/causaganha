const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  // Navigate to the local server
  await page.goto('http://127.0.0.1:3000/causaganha');

  // Wait a bit
  await page.waitForTimeout(2000);

  // Take a screenshot
  await page.screenshot({ path: 'verification11.png', fullPage: true });

  await browser.close();
})();
