import { chromium } from 'playwright';
const b = await chromium.connectOverCDP('http://127.0.0.1:9222');
const page = await b.contexts()[0].newPage();
try {
  await page.goto('https://strategylab.pravda.systems', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(2500);
  const t = await page.evaluate(() => document.body.innerText);
  console.log(JSON.stringify({
    has_health_word: t.includes('free'),
    has_parse_failures: t.includes('parse failures'),
    has_recorder_pid: t.includes('recorder pid'),
    tabs: (t.match(/Health|Charts|Compare|Logs|Processes/g)||[]),
    first600: t.slice(0,600),
  }, null, 1));
} finally { await page.close(); }
