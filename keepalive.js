// Keep the Streamlit Community Cloud demos awake by actually rendering them in a
// headless browser. A bare HTTP GET does NOT register as traffic — Streamlit
// Cloud only refreshes "last active" when the page's JS opens its websocket, so
// we load the page, wake it if it's asleep, and dwell long enough for the
// session to register. This is a redundancy hedge: the always-on Hugging Face
// mirrors are the primary live backup; this keeps the Streamlit links live too.
const { chromium } = require('playwright');

const URLS = [
  'https://dooling-cmapss-rul.streamlit.app',
  'https://dooling-techintel-quantum.streamlit.app',
];

(async () => {
  const browser = await chromium.launch();
  let failures = 0;
  for (const url of URLS) {
    const page = await browser.newPage();
    try {
      console.log('visiting', url);
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 90000 });

      // If the app slept, Streamlit shows a "Yes, get this app back up!" button.
      const wake = page.getByText(/get this app back up/i);
      if (await wake.count()) {
        console.log('  app was asleep -> clicking wake button');
        await wake.first().click();
        await page.waitForTimeout(45000); // give the container time to boot
      }

      // Dwell so the websocket session counts as active traffic.
      await page.waitForTimeout(20000);
      console.log('  ok:', await page.title());
    } catch (e) {
      failures++;
      console.error('  ERROR on', url, '-', e.message);
    } finally {
      await page.close();
    }
  }
  await browser.close();
  if (failures) process.exit(1); // surface failures in the Actions run status
})();
