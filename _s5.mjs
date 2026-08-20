import { chromium } from 'playwright';
const b = await chromium.connectOverCDP('http://127.0.0.1:9222');
const page = await b.contexts()[0].newPage();
try {
  const bad=[], errs=[];
  page.on('response', r => { if (r.status()>=400 && !r.url().includes('favicon')) bad.push(`${r.status()} ${r.url()}`); });
  page.on('pageerror', e => errs.push(String(e)));
  await page.setViewportSize({width:1440,height:1000});
  await page.goto('http://localhost:5280/', {waitUntil:'networkidle', timeout:60000});
  await page.waitForTimeout(3000);
  const out = await page.evaluate(() => ({
    momentOpen: !!document.querySelector('.moment'),
    sparkPts: document.querySelector('.spark polyline')?.getAttribute('points')?.split(' ').length ?? 0,
    thresholdLine: !!document.querySelector('.spark line'),
    rawReason: document.querySelector('.moment-facts dd code')?.textContent ?? null,
    charts: document.querySelectorAll('.chart-host canvas').length,
    gapNote: document.querySelector('.chart-gaps')?.textContent ?? null,
    staleFinding: document.querySelector('.finding.alarm h3')?.textContent?.trim() ?? null,
    raceFinding: document.querySelector('.finding h3')?.textContent?.trim() ?? null,
    decisions: document.querySelectorAll('.dec').length,
    reversed: document.querySelectorAll('.dec.reversed, .dec.amended').length,
  }));
  console.log(JSON.stringify({out, bad, errs}, null, 1));
  await page.screenshot({path:'C:/Users/dprvd/Documents/sobko-strategylab/.shot-full.png', fullPage:true});
} finally { await page.close(); }
