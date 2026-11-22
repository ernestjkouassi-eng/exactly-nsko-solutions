# NSKO HQ

HQ is the private control room for NSKO Solutions. It lives at **nskosolutions.co.uk/hq** and only you can open it.

## What it shows
- **Inbox**: every brief sent through the website's contact form, newest first: name, company, sector, budget, timeline, NDA request and message. Mark each one New, Replied or Archived. "Reply by email" opens a reply to the sender. Briefs are saved in HQ even when email is switched off, so none are lost.
- **Approvals**: steps the team will not take without your yes (anything paid, public or hard to undo). Tap Approve or Decline. HQ records your decision and the time. It does not do the step itself: Claude carries it out in the next session. "Change my mind" moves it back to waiting.
- **Team**: the ten AI agents shown as desks on an office floor. Orange screens are working now. Tap a desk to see its task, status and last update.
- **Site health**: live checks of nskosolutions.co.uk (does each page and file load, and how fast), plus which settings are switched on. It only ever says "Set" or "Not set"; it never shows a secret.
- **Log**: decisions the team made without stopping to ask, so you can check them.

Every number in HQ comes from real stored data or a real check. Nothing is made up.

## How to sign in
1. Go to nskosolutions.co.uk/hq.
2. Type your HQ password and press Sign in.
3. You stay signed in for 12 hours, then HQ asks again. Press **Sign out** (top right) when you are done on a shared computer.

After 5 wrong passwords from the same place, sign-in pauses for 15 minutes.

## What you need to set (once)
In Cloudflare: **Workers & Pages → nsko-solutions → Settings → Variables and Secrets → Add**.

| Name | Type | What it is | Needed? |
|---|---|---|---|
| `HQ_PASSWORD` | Secret | The password for HQ. Choose a long one (four or more random words). | Yes. Until it is set, /hq shows these setup steps instead of a sign-in box. |
| `CONTACT_TO` | Text | The email address new briefs are sent to. | Only for email alerts. |
| `RESEND_API_KEY` | Secret | Key from resend.com that lets the site send email. | Only for email alerts. |
| `TURNSTILE_SECRET` | Secret | Cloudflare's spam check for the contact form. | Recommended. |

Storage (a Cloudflare KV space called `HQ`) is created automatically the first time the site is deployed with this version. You do not need to set it up.

To change the HQ password, edit the same secret. Everyone signed in is signed out straight away.

## For the team (technical notes)
- Code: `src/worker.js` (router + contact form), `src/hq/api.js` (`/api/hq/*`), `src/hq/auth.js` (sessions), `src/hq/page.js` + `src/hq/shell.html` (the page). `wrangler.jsonc` routes `/hq` and `/api/*` to the Worker and binds KV `HQ` (no id; wrangler provisions it on deploy).
- Team status, approval items and the log come from `hq/status.json` (bundled at deploy). Update it when work moves; mirror new `LAUNCH-LOG.md` entries into its `log` list.
- KV keys: `brief:<iso>:<uuid>`, `decision:<approval id>`, `sess:<id>` (12 h), `hqrl:<ip>` (login limit), `rl:<ip>` (contact form limit). The older binding name `BRIEFS` still works for briefs.
- Sessions: HMAC-signed HttpOnly, Secure, SameSite=Strict cookie (`__Host-nsko_hq`), key derived from `HQ_PASSWORD`, also checked against KV so Sign out ends it on the server. Writes must be same-origin JSON.
- The HQ page sends its own strict CSP (per-request nonce, `'self'` only, no external requests). The public site's CSP in `public/_headers` is unchanged.
- Local test: put `HQ_PASSWORD=devpass123` in `.dev.vars` (gitignored), run `npx wrangler dev --local --port 8793`, open http://localhost:8793/hq. Live-site checks show "Could not connect" if the machine has no internet.
