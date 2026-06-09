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

      // Let the sleep-screen React UI render before we look for the wake button —
      // checking too early was why a sleeping app slipped through before.
      await page.waitForTimeout(8000);

      // If the app slept, Streamlit shows a "Yes, get this app back up!" button.
      // Match by role first (robust to copy tweaks), fall back to text.
      const wake = page
        .getByRole('button', { name: /get this app back up/i })
        .or(page.getByText(/get this app back up/i));
      if (await wake.count()) {
        console.log('  app was asleep -> clicking wake button');
        await wake.first().click();
        // Wait for the wake button to disappear (app is booting), up to ~90s.
        try {
          await wake.first().waitFor({ state: 'hidden', timeout: 90000 });
        } catch {
          console.log('  (wake button still visible after 90s — app slow to boot)');
        }
        await page.waitForTimeout(15000); // let the websocket session establish
      } else {
        console.log('  app already awake');
      }

      // Dwell so the websocket session counts as active traffic.
      await page.waitForTimeout(15000);
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
