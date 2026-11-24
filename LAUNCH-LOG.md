# NSKO Solutions v4.2 launch log

## 2026-11-24
- Missing: `nsko-assets/` folder was not in this session. Missing files: whole folder, including `demo/wellspring/`, any brand photos and footage. Placeholders used: new Blender renders made in-house; Wellspring panel shows a still and the label "Simulated data" until the demo files arrive.
- Decision: D-DIN from the official Datto release (SIL Open Font License 1.1), self-hosted. Only Regular and Bold exist, so 500 maps to Regular, 600 to Bold.
- Decision: 3D objects made in Blender from code (no stock models), rendered at native size and never upscaled (Ernest's note on zoomed, soft images).
- Decision: hero is a 120-frame turntable over a 100° arc so the N stays readable; scroll and drag move it.
- Decision: the admin gets its own free Supabase project, so turning off public sign-up never touches the NSKO fitness app.
- Rollback: previous site is commit df6138c on `main`. Cloudflare keeps earlier Worker versions too (Deployments, Rollback).
