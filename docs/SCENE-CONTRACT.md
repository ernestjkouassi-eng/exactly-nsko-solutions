# Scene module contract (NSKO Solutions site)

You are building ONE self-contained 3D scene module for the NSKO Solutions marketing site. The page owner integrates it. Read this fully.

## Who and what
NSKO Solutions (said "Nes-ko") is a UK engineering studio. **Positioning: "We don't build the machine. We code the mind and the system."** Partners build hardware; NSKO writes the intelligence, software, data and simulation. Brand: Night `#050B16`, Navy `#071A36`, Ink `#0A1B33`, Ice `#F3F6FB`, NSKO Blue `#1554E0`, Ice-glow `#7FD4FF`, Teal `#19B8A6` (online/secure), Signal coral `#FF5A3C` (the one hot accent). Fonts already loaded by the page: `Geist` (text), `"Geist Mono"` (labels, uppercase, letter-spaced), `"Instrument Serif"` italic (one or two accent words). Feel: quiet, exact, expensive, defence-tech seriousness, cinema-grade motion. No neon cyberpunk, no hooded hackers, no padlock clichés, no emoji, no real brand logos, no real military insignia.

## Hard rules
- Copy rules: short, confident British English. Never claim certifications (ISO, CREST, Cyber Essentials, medical-device approvals, security clearances), clients, or contracts. Describe capabilities ("we code…", "we can deliver…"). Medical and defence = software, data, simulation. Defence content is non-weapon: surveillance, logistics, autonomy, simulation, secure comms. No weapons depicted.
- The machines/screens may carry the wordmark **NSKO SOLUTIONS** (draw it into a canvas texture; Geist Mono / Geist, letter-spaced).
- No external assets or network calls at runtime. Everything procedural (three.js geometry, canvas-drawn textures, shaders). Do not use the filesystem outside your own files.
- Realism target: as complex, detailed and physically convincing as procedural code can get: PBR materials (MeshPhysicalMaterial: clearcoat, metalness, roughness, transmission only if cheap), environment lighting, soft shadows, bevels, panel seams, screws, cables, emissive details, depth of field feel via lighting/fog. It must read at a glance as a specific, believable object. Be honest in your report about where it falls short of photoreal.

## Tech
- three.js r170 is vendored. Page import map: `"three" -> /vendor/three/three.module.js`, `"three/addons/" -> /vendor/three/addons/`. Already vendored addons: `environments/RoomEnvironment.js`, `utils/BufferGeometryUtils.js`, `geometries/RoundedBoxGeometry.js`. You MAY copy more addons you need from `/home/user/nsko-solutions/node_modules/three/examples/jsm/...` into `/home/user/nsko-solutions/public/vendor/three/addons/...` (add files only; never modify existing ones). Check each addon's own imports resolve (`from 'three'` is fine).
- Plain ES module, no build step, no other libraries. gsap is NOT available inside your module (the page uses it outside).
- File: `/home/user/nsko-solutions/public/js/<yourname>.js`. Touch no other existing file (not index.html, main.js, any css, other modules). If you need CSS, inject a `<style>` from your module, every selector scoped under your root's id.

## API (exact)
```js
export function init(root, opts = {}) { ... return { setProgress(p), dispose() }; }
// (hero.js keeps its older name too: export function initHero(root, api) — see your brief)
```
- `root` is a `<section>` (position:relative, 100vh, overflow hidden, background already set by the page, so keep your canvas transparent or draw your own backdrop inside the scene). It contains an empty `<div class="scene">` (position:absolute; inset:0). Append your `<canvas>` there. Create any overlay HTML (captions, labels, code panels) as children of `root` (position:absolute, pointer-events:none unless interactive).
- `setProgress(p)`: p in [0,1] = how far the visitor has scrolled through this scene. The page calls it every frame from a scrubbed scroll timeline. Your scripted story (camera moves, explode/assemble, captions) must be a pure function of p (smooth, scrubbable both directions). Ambient idle motion (breathing, rotor spin, blinking lights) runs on real time on top.
- The page sets `root.dataset.on = '1'` only while the scene is on screen (including during crossfades); otherwise `'0'`. Your rAF loop must early-return (no rendering, no work) unless `root.dataset.on === '1'`. Keep the loop alive; do not rely on IntersectionObserver.
- `dispose()` must cancel rAF, remove listeners, dispose geometries/materials/textures, `renderer.dispose()`, `renderer.forceContextLoss()`, remove the canvas and your overlay nodes. The page may call `init` again later.
- Resize: use ResizeObserver on `root`. Cap pixel ratio at 1.75 (1.5 if `innerWidth < 800`). Must work at 1440x900, 1280x720, 768x1024 and 390x844 (portrait: pull the camera back or reframe so the subject stays fully visible; hide secondary overlay text if cramped).
- `prefers-reduced-motion`: no idle animation; render a good still at the p the page gives you; code-typing shows final text.
- Performance: aim for under ~250k triangles and a few dozen draw calls (use InstancedMesh / mergeGeometries for repeated details). Avoid per-frame allocations. Pointer: you may read `pointermove` on `window` for subtle parallax.
- The overlay captions must be legible on Night/Navy backgrounds (Ice text, Geist Mono labels, Instrument Serif accent words), sit clear of the subject, and never overlap each other.

## How to test (do this properly, look at your own screenshots)
1. Dev page: create `/home/user/nsko-solutions/public/_dev/<yourname>.html` (delete it when finished):
```html
<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><link rel=stylesheet href=/css/fonts.css>
<script type=importmap>{"imports":{"three":"/vendor/three/three.module.js","three/addons/":"/vendor/three/addons/"}}</script>
<style>body{margin:0;background:#050B16;color:#F4F7FB}section{position:relative;height:100vh;overflow:hidden;background:#050B16}.scene{position:absolute;inset:0}</style>
<section id=s data-on=1><div class=scene></div></section>
<script type=module>import {init} from '/js/NAME.js'; window.h=init(document.getElementById('s'),{}); window.h.setProgress(+(new URLSearchParams(location.search).get('p')||0))</script>
```
2. Serve: `cd /home/user/nsko-solutions/public && python3 -m http.server <your port>` in the background (ports given in your brief).
3. Screenshot with Playwright: `const {chromium}=require('playwright'); chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']})`. Run node from a directory where `require('playwright')` resolves (e.g. `cd /tmp`). Save screenshots under the scratchpad directory you were told. Capture at least p = 0, .25, .5, .75, 1 at 1440x900, and p=.5 at 390x844. Call `window.h.setProgress(x)` via `page.evaluate`, wait ~1.5s per shot (software GL is slow), then LOOK at every image and fix what is ugly, flat, clipped, overlapping or unreadable. Iterate until it is genuinely impressive. Collect console errors (`page.on('pageerror')`, `console` type error) — must be zero.
4. Check `h.dispose()` works (no errors, canvas removed) and re-`init` works.

## Deliver
Reply with: the file path(s), the API as built, the story beat per p-range, the screenshot paths you checked, the console-error result, what is still short of photoreal, and any addon files you added. Keep the report short. Delete your `_dev` page. Do not commit to git.
