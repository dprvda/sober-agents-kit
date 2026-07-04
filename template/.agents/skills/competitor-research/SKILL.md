---
name: competitor-research
description: Deep competitor teardown — get INSIDE a competitor's real product, not just its marketing pages. Scrape + screenshot the public pages, sign up on the free tier using your project's own catch-all inbox, read the verification / magic code from that inbox, log in, screenshot the real authenticated product, then synthesize a teardown (onboarding, real feature set, pricing/credit model, the patterns to copy, the underserved gap). Trigger on "competitor research", "tear down <product>", "get inside <competitor>", "product teardown".
---

# competitor-research — get INSIDE a competitor's real product, then tear it down

Marketing pages lie by omission. The product that matters — the real onboarding, the actual feature set,
the pricing/credit model, the "show it working" devices — is behind a sign-up. This skill gets you inside,
legitimately, on the free tier the vendor offers to anyone, and captures the real thing so you can copy the
battle-tested craft and find the gap they leave underserved.

## The one rule

**Public products, public pages, the free tier only.** Read politely (rate-limited, cached), honor each
provider's terms, use a genuine free-tier sign-up with an address you control. This is competitive research
on publicly-available products — never breach a paywall, never touch anything private, never scrape behind
someone else's account.

## What your PROJECT provides (in its own PRIVATE docs — never in this public skill)

This kit is public, so it holds the **method** only. Every project-specific value lives in that project's
own private docs (e.g. its `INFRASTRUCTURE.md` or a private method doc) and its key store — look them up
there, never write them here or anywhere public:

- a **catch-all inbox** you control, so you can sign up as `<anything>@your-domain` and receive the mail;
- **inbox read access** (an IMAP host + an app password, or a mail API) — pulled from your key store at run
  time, never hardcoded;
- a **browser automation** tool — `firecrawl` (scrape/screenshot/interact) or `puppeteer`/`playwright`
  driving a local Chrome.

If any of those isn't set up, stop and ask the owner — do not improvise an address or a key.

## The method (five stages)

1. **Outside view.** Scrape the marketing, pricing, and docs pages (firecrawl `scrape`, markdown +
   full-page screenshot). Record the positioning, the advertised feature list, and the pricing / credit
   model as they present it.
2. **Get in.** Sign up on the free tier using a fresh address at your catch-all (`<competitor>@your-domain`).
   Drive a real browser:
   - launch a real Chrome (e.g. `puppeteer-core` with your installed Chrome + a persistent `userDataDir`);
   - type the email with **REAL keystrokes** (`page.keyboard.type`, NOT `input.value = …`) — React-controlled
     sign-in forms leave the submit button disabled unless a real keystroke fires the input event;
   - request the magic code / verification email.
3. **Read the code from the inbox.** Poll your catch-all inbox over IMAP for the newest message to that
   address and extract the code. Two gotchas that waste an hour if missed:
   - codes are often **alphanumeric** (e.g. `KAHVFJ`), not six digits — match
     `code[:\s]*([A-Z0-9]{5,8})` case-insensitively, and take the **newest by date**;
   - check the **Spam / Junk** folder too, not just the inbox.
4. **Enter + capture the real product.** Type the code (real keystrokes), submit, then screenshot the
   authenticated product: the onboarding survey, the empty state, the real tool palette / feature set, and
   the pricing / credit surface once you're inside.
5. **Synthesize the teardown.** Per competitor, write: onboarding screen-by-screen · the REAL feature set ·
   the pricing / credit model · their "show it working" device · strengths · weaknesses. Then the synthesis:
   the **battle-tested patterns to copy**, and the specific **underserved gap** the giant leaves open. Save
   it where your project keeps competitor findings (commonly `docs/COMPETITORS.md`), with the screenshots.

## Generic shape (adapt; keep every specific value in your private config / env)

```js
// puppeteer-core, real Chrome, real keystrokes. All specifics come from env — nothing hardcoded here.
const puppeteer = require("puppeteer-core");
const CHROME = process.env.CHROME_PATH;                 // your installed Chrome
const EMAIL  = process.env.CATCHALL_EMAIL;              // <competitor>@your-domain, from your private config
const browser = await puppeteer.launch({ executablePath: CHROME, headless: "new",
  userDataDir: process.env.PROFILE_DIR, defaultViewport: { width: 1440, height: 900 } });
const page = await browser.newPage();
await page.goto(process.env.TARGET_LOGIN_URL, { waitUntil: "networkidle2" });
const input = await page.$("input[type=email], input");
await input.click({ clickCount: 3 }); await page.keyboard.press("Backspace");
await page.keyboard.type(EMAIL, { delay: 60 });         // REAL keystrokes — value= leaves React disabled
// click "get magic code" / "continue", then poll IMAP for the code (below), type it, screenshot.
```

```python
# IMAP: newest message to EMAIL, alphanumeric code, check Spam. Host + app password from your key store.
import imaplib, email, re, os
M = imaplib.IMAP4_SSL(os.environ["IMAP_HOST"])
M.login(os.environ["IMAP_USER"], os.environ["IMAP_APP_PASSWORD"])  # from the key store, never hardcoded
for box in ("INBOX", "[Gmail]/Spam"):
    M.select(box)
    _, ids = M.search(None, f'(TO "{os.environ["CATCHALL_EMAIL"]}")')
    # take the newest by date; extract:  re.search(r"code[:\s]*\**([A-Z0-9]{5,8})", body, re.I)
```

## Model

Run this on your **strong model at high effort** (multi-step browser + inbox reasoning). Per the project's
model policy, deep reference / competitor research is an Opus-high job.

## Deliverable

A `docs/COMPETITORS.md` (or the project's equivalent) with a real teardown per competitor and the synthesis
— the patterns to copy and the gap to take — plus the screenshots as evidence. Marketing-page summaries are
NOT a teardown; if you didn't get inside the product, say so.
