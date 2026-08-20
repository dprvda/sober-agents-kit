const { chromium } = require("playwright");
const F = "file:///C:/Users/dprvd/Documents/app-commonplace/.claude/worktrees/dept-engine/.workspace/northstar-status.html";
const OUT = "C:/Users/dprvd/Documents/app-commonplace/.claude/worktrees/dept-engine/.workspace/";
(async () => {
  const b = await chromium.connectOverCDP("http://127.0.0.1:9222");
  const ctx = b.contexts()[0];
  const page = await ctx.newPage();
  try {
    await page.setViewportSize({ width: 1280, height: 1400 });
    await page.goto(F);
    await page.waitForTimeout(900);
    const h = await page.evaluate(() => document.body.scrollHeight);
    console.log("page height", h);
    for (let i = 0; i < 4; i++) {
      const y = i * 1300;
      await page.evaluate((yy) => window.scrollTo(0, yy), y);
      await page.waitForTimeout(350);
      await page.screenshot({ path: `${OUT}ns-${i + 1}.png` });
    }
    console.log("shots written");
  } finally {
    await page.close();
  }
})();
