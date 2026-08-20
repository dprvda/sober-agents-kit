import { chromium } from 'playwright';
const b = await chromium.connectOverCDP('http://127.0.0.1:9222');
const page = await b.contexts()[0].newPage();
try {
  const snap = async (url) => {
    await page.goto(url, {waitUntil:'networkidle', timeout:60000});
    await page.waitForTimeout(1800);
    return page.evaluate(() => {
      const txt = document.body.innerText;
      return {
        aiBoxes: document.querySelectorAll('.ai').length,
        sections: document.querySelectorAll('section.sec, header.sec').length,
        tables: document.querySelectorAll('table.grid').length,
        charts: document.querySelectorAll('.chart-host canvas').length,
        // every digit-bearing line still present without AI prose
        numberLines: txt.split('\n').filter(l => /\d/.test(l)).length,
        chars: txt.length,
      };
    });
  };
  const withAi = await snap('http://localhost:5280/');
  const noAi   = await snap('http://localhost:5280/?noai=1');
  console.log(JSON.stringify({withAi, noAi}, null, 1));
  await page.goto('http://localhost:5280/?noai=1', {waitUntil:'networkidle'});
  await page.waitForTimeout(1500);
  await page.screenshot({path:'C:/Users/dprvd/Documents/sobko-strategylab/.shot-noai.png'});
} finally { await page.close(); }
