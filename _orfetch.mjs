import { chromium } from 'playwright';
const b = await chromium.connectOverCDP('http://127.0.0.1:9222');
const ctx = b.contexts()[0];
const page = await ctx.newPage();
try {
  await page.goto(process.argv[2], {waitUntil:'domcontentloaded', timeout:60000});
  await page.waitForTimeout(12000);
  console.log(await page.evaluate(()=>document.body.innerText));
} finally { await page.close(); }
