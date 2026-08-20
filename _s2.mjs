import { chromium } from 'playwright';
const b = await chromium.connectOverCDP('http://127.0.0.1:9222');
const page = await b.contexts()[0].newPage();
try {
  const bad=[];
  page.on('response', r => { if (r.status() >= 400) bad.push(`${r.status()} ${r.url()}`); });
  const errs=[]; page.on('pageerror', e=>errs.push(String(e)));
  const warns=[]; page.on('console', m => { if (m.type()==='error') warns.push(m.text().slice(0,160)); });
  await page.setViewportSize({width:1440,height:1000});
  await page.goto('http://localhost:5280/', {waitUntil:'networkidle', timeout:60000});
  await page.waitForTimeout(2000);
  console.log(JSON.stringify({bad, errs, warns}, null, 1));
} finally { await page.close(); }
