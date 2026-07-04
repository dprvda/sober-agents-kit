---
name: web-recon
description: Drive a REAL browser to get inside a web service you can't reach by scraping — sign in (including reading a magic / verification code from mail), click through, take screenshots, and capture the authenticated product. Main use is a deep competitor teardown; also any "log into a real web app and operate or capture it" task. Trigger on "get inside <product>", "log into <service> and screenshot", "tear down <competitor>", "competitor research", "web recon".
---

# web-recon — operate a real web service behind a login (sign in, click, screenshot, capture)

Some things you cannot get by scraping HTML: what lives behind a sign-in — the real onboarding, the actual
feature set, the pricing once you're inside. This skill drives a **real browser** to get in, legitimately,
on the free tier a vendor offers to anyone, and capture it: sign in (including reading a magic / verification
code from a mailbox), click through, and screenshot the authenticated product. Its main use is a **deep
competitor teardown**, but reach for it any time you must log into a real web app and operate or capture it.

## The one rule

**Public products, public pages, the free tier only.** Read politely (rate-limited, cached), honor each
provider's terms, use a genuine free-tier sign-up with an address you control. Never breach a paywall, never
touch anything private, never operate someone else's account.

## What your PROJECT provides (in its own PRIVATE config — never in this public skill)

This kit skill is public, so it holds the **method** only. Every project-specific value lives in that
project's own private docs and key store — look them up there, never write them here or anywhere public:

- a **catch-all inbox** you control, so you can sign up as `<anything>@your-domain` and receive the mail;
- **inbox read access** (an IMAP host + an app password, or a mail API) — pulled from the key store at run
  time, never hardcoded;
- a **browser automation** tool — `firecrawl` (scrape/screenshot/interact) or `puppeteer`/`playwright`
  driving a local Chrome.

(In this project family those live in `INFRASTRUCTURE.md` + the git-ignored `INFRASTRUCTURE.keys.local.md`.)
If any isn't set up, stop and ask the owner — do not improvise an address or a key.

## The method (five stages)

1. **Outside view.** Scrape the marketing, pricing, and docs pages (firecrawl `scrape`, markdown +
   full-page screenshot). Record the positioning, the advertised features, and the pricing / credit model.
2. **Get in.** Sign up on the free tier using a fresh address at your catch-all (`<target>@your-domain`).
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
4. **Enter + capture.** Type the code (real keystrokes), submit, then screenshot the authenticated product:
   the onboarding survey, the empty state, the real tool palette / feature set, the pricing surface inside.
5. **Synthesize.** For a competitor teardown, write per competitor: onboarding screen-by-screen · the REAL
   feature set · the pricing / credit model · their "show it working" device · strengths · weaknesses. Then
   the synthesis: the **battle-tested patterns to copy**, and the **underserved gap** the giant leaves open.
   Save it where the project keeps competitor findings (commonly `docs/COMPETITORS.md`), with the screenshots.

## Generic shape (adapt; keep every specific value in your private config / env)

```js
// puppeteer-core, real Chrome, real keystrokes. All specifics come from env — nothing hardcoded here.
const puppeteer = require("puppeteer-core");
const browser = await puppeteer.launch({ executablePath: process.env.CHROME_PATH, headless: "new",
  userDataDir: process.env.PROFILE_DIR, defaultViewport: { width: 1440, height: 900 } });
const page = await browser.newPage();
await page.goto(process.env.TARGET_LOGIN_URL, { waitUntil: "networkidle2" });
const input = await page.$("input[type=email], input");
await input.click({ clickCount: 3 }); await page.keyboard.press("Backspace");
await page.keyboard.type(process.env.CATCHALL_EMAIL, { delay: 60 });   // REAL keystrokes; value= leaves React disabled
// click "get magic code" / "continue", poll IMAP for the code, type it, screenshot.
```

```python
# IMAP: newest message to CATCHALL_EMAIL, alphanumeric code, check Spam. Host + app password from the key store.
import imaplib, re, os
M = imaplib.IMAP4_SSL(os.environ["IMAP_HOST"]); M.login(os.environ["IMAP_USER"], os.environ["IMAP_APP_PASSWORD"])
for box in ("INBOX", "[Gmail]/Spam"):
    M.select(box); _, ids = M.search(None, f'(TO "{os.environ["CATCHALL_EMAIL"]}")')
    # newest by date; extract:  re.search(r"code[:\s]*\**([A-Z0-9]{5,8})", body, re.I)
```

## Model

Run this on your **strong model at high effort** — multi-step browser + inbox reasoning.

## Deliverable

For a teardown: a `docs/COMPETITORS.md` (or the project's equivalent) with a real teardown per competitor +
the synthesis (patterns to copy, the gap to take) + the screenshots as evidence. A marketing-page summary is
NOT a teardown; if you didn't get inside the product, say so.
