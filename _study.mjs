import { chromium } from 'playwright';
const b = await chromium.connectOverCDP('http://127.0.0.1:9222');
const page = await b.contexts()[0].newPage();
try {
  const errs=[], logs=[];
  page.on('pageerror', e => errs.push(String(e)));
  page.on('console', m => { if (m.type()==='error') logs.push(m.text().slice(0,200)); });
  await page.setViewportSize({width:1440,height:1000});
  await page.goto('http://localhost:5280/', {waitUntil:'networkidle', timeout:60000});
  await page.waitForTimeout(2500);
  const state = await page.evaluate(() => ({
    refusing: !!document.querySelector('.fail'),
    failMsg: document.querySelector('.fail-msg')?.textContent?.slice(0,300) || null,
    loading: !!document.querySelector('.loading'),
    sections: document.querySelectorAll('section.sec, header.sec').length,
    kpis: [...document.querySelectorAll('.kpi-v')].map(e=>e.textContent),
    aiNotes: document.querySelectorAll('.ai').length,
    charts: document.querySelectorAll('.chart-host canvas').length,
    tables: document.querySelectorAll('table.grid').length,
  }));
  console.log(JSON.stringify({state, errs, logs}, null, 1));
  await page.screenshot({path:'C:/Users/dprvd/Documents/sobko-strategylab/.shot-study.png', fullPage:false});
} finally { await page.close(); }
