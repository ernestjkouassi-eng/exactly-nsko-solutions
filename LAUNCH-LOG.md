# NSKO Solutions v4.2 launch log

## 2026-11-24
- Missing: `nsko-assets/` folder was not in this session. Missing files: whole folder, including `demo/wellspring/`, any brand photos and footage. Placeholders used: new Blender renders made in-house; Wellspring panel shows a still and the label "Simulated data" until the demo files arrive.
- Decision: D-DIN from the official Datto release (SIL Open Font License 1.1), self-hosted. Only Regular and Bold exist, so 500 maps to Regular, 600 to Bold.
- Decision: 3D objects made in Blender from code (no stock models), rendered at native size and never upscaled (Ernest's note on zoomed, soft images).
- Decision: hero is a 120-frame turntable over a 100° arc so the N stays readable; scroll and drag move it.
- Decision: the admin gets its own free Supabase project, so turning off public sign-up never touches the NSKO fitness app.
- Rollback: previous site is commit df6138c on `main`. Cloudflare keeps earlier Worker versions too (Deployments, Rollback).
- Decision: admin is a new free Supabase project `nsko-solutions-admin` (London). Owner account created for the allow-listed email; data needs two-step sign-in (aal2) by database rule.
- Decision: "Send pack" marks the request approved and opens a ready email in Ernest's own mail app. Nothing is emailed to anyone automatically.
- Decision: social plan saved as 9 drafts in the Content studio. Nothing posted.
- Grants: 11 calls found by web search on 24 Nov 2026. Official sites were blocked from this session, so each needs checking on the funder page. Two open now with near deadlines: BridgeAI Deployment Catalyst (8 Dec) and Full ADOPT Round 10 (about 2 Dec, farm-led only).
- Decision: film soundtrack is synthesised in-house, so there is no music licence to manage.
- Fix: branch previews failed on Cloudflare because the KV store had no ID in `wrangler.jsonc`. ID added (not a secret).
- Lighthouse (mobile, local server): performance 97, accessibility 97 after fixes, best practices 96, SEO 100. LCP 2.3 s, CLS 0.
- Assets pack received: `assets-source/` now holds tokens.json, the 8 logo SVGs (plus PNGs), README-ASSETS.md and the Wellspring demo.
- Logo fix: the supplied logos used #FF4F00 for the orange fragment. Regenerated with #E8541A as the pack instructs (`scripts/make_logo_pack.py --fix`).
- Wellspring: live at /demo/wellspring/ (noindex). The site copy self-hosts three.js r128 and the fonts and moves the script to app.js, because the site blocks outside scripts. The supplied file is unchanged in assets-source.
- Still missing (heavy media, style reference only): board/, references/uploads, references/frames, prompts/, and the munchnow video.
- Cloudflare branch previews fail (no build log visible from here). Ernest asked for v4.2 to replace the live site, so it ships from `main` after local QA. Rollback: Cloudflare Deployments, or revert to commit df6138c.
