import { chromium } from 'playwright';
const b = await chromium.connectOverCDP('http://127.0.0.1:9222');
const page = await b.contexts()[0].newPage();
try {
  const errs=[]; page.on('pageerror',e=>errs.push(String(e)));
  await page.setViewportSize({width:1600,height:900});
  await page.goto('file:///C:/Users/dprvd/Documents/sobko-strategylab/docs/presentation/progress-2026-07-29.html');
  await page.evaluate(()=>Deck.enter());
  await page.waitForTimeout(400);
  for (let n=0;n<11;n++){
    if(n){ await page.keyboard.press('ArrowRight'); await page.waitForTimeout(220); }
    if([0,7].includes(n)) await page.screenshot({path:`C:/Users/dprvd/Documents/sobko-strategylab/.shots/k${n}.png`});
  }
  console.log('errs:',JSON.stringify(errs));
} finally { await page.close(); }
