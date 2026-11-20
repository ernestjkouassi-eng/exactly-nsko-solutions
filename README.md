# NSKO Solutions website

Static site in `public/` plus a Cloudflare Worker (`src/worker.js`) for the contact form.
Deploy: connect this repo to Cloudflare (Workers & Pages, Git), deploy command `npx wrangler deploy`. Add the domain in `wrangler.jsonc` once named.
Settings in the Cloudflare dashboard (Variables and Secrets): `CONTACT_TO` (the inbox for briefs), `RESEND_API_KEY`, `TURNSTILE_SECRET`. The Turnstile site key goes in a `<meta name="turnstile-sitekey">` tag in `public/index.html`.
Open items: replace the stand-in hero head with the owned operator model, replace the stand-in skyline with owned footage, supply the Noa Ellsworth prompt.
