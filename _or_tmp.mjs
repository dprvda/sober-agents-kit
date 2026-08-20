import { chromium } from 'playwright';
const b = await chromium.connectOverCDP('http://127.0.0.1:9222');
const ctx = b.contexts()[0];
const page = await ctx.newPage();
try {
  await page.goto('https://openreview.net/forum?id=bbVH40jy7f', {waitUntil:'domcontentloaded', timeout:60000});
  await page.waitForTimeout(12000);
  const t = await page.evaluate(()=>document.body.innerText);
  console.log(t.slice(0, 70000));
} finally { await page.close(); }
