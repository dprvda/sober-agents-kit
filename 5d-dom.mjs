import { chromium } from 'playwright';
const b = await chromium.connectOverCDP('http://127.0.0.1:9222');
const ctx = b.contexts()[0];
const page = await ctx.newPage();
try {
  await page.goto('http://localhost:3005/stats', { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForSelector('table[data-account-stats]', { timeout: 30000 });
  console.log('TITLE', await page.title());
  const rows = await page.$$eval('tr[data-account-row]', (trs) => trs.map((tr) => ({
    label: tr.getAttribute('data-account-row'),
    cells: [...tr.querySelectorAll('td[data-metric]')].map((td) =>
      `${td.getAttribute('data-metric')} => "${td.textContent.trim()}"`),
  })));
  for (const r of rows) console.log(r.label, JSON.stringify(r.cells));
  const paras = await page.$$eval('main p', (ps) => ps.map((p) => p.textContent.trim()));
  console.log('--- PARAGRAPHS ---');
  for (const p of paras) console.log('|', p);
  await page.screenshot({ path: 'C:/Users/dprvd/Documents/sobko-swarm/ss-5D/shots/stats-three-states.png', fullPage: true });
  console.log('SHOT written');
} finally { await page.close(); }
