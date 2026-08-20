import { chromium } from 'playwright';
const b = await chromium.connectOverCDP('http://127.0.0.1:9222');
const ctx = b.contexts()[0];
const page = await ctx.newPage();
try {
  await page.goto('https://strategylab.pravda.systems', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(3000);
  const text = await page.evaluate(() => document.body.innerText);
  console.log(JSON.stringify({
    url: page.url(),
    has_binaries_drive_tile: text.includes('binaries drive'),
    has_backtest_every_swap: text.includes('Backtest every swap'),
    has_H_free: text.includes('H: free'),
    dollar_count: (text.match(/\$/g) || []).length,
    weth_mentions: (text.match(/WETH/g) || []).length,
    len: text.length,
  }, null, 1));
} finally { await page.close(); }
