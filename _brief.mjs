import { chromium } from 'playwright';
const b = await chromium.connectOverCDP('http://127.0.0.1:9222');
const ctx = b.contexts()[0];
const page = await ctx.newPage();
try {
  await page.goto('file:///C:/Users/dprvd/Documents/sobko-wallettrace/src/visualize/briefing.html');
  await page.waitForLoadState('load');
  const slides = await page.$$eval('.slide h1, .slide h2', els => els.map(e => e.textContent.trim()));
  const cards = await page.$$eval('.card .value', els => els.map(e => e.textContent.trim()));
  const bad = (await page.content()).match(/undefined|NaN/g);
  console.log(JSON.stringify({ slides, cards, bad }, null, 1));
} finally { await page.close(); }
