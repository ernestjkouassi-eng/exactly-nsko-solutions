#!/usr/bin/env python3
"""Posters A3 and A2, 3 mm bleed, crop marks outside trim. Uses the print render (3600 px wide) so nothing is upscaled for A3 at 300 dpi.
Run: python3 make_posters.py  -> public/media/v42/posters/*.pdf"""
import pathlib, subprocess, json
T = pathlib.Path(__file__).resolve().parent; R = T.parent.parent
OUT = R / 'public/media/v42/posters'; OUT.mkdir(parents=True, exist_ok=True)
src = R / 'render/out/print-n/f000.png'
if not src.exists(): src = R / 'render/out/hero-n/f060.png'
LINES = [('build-beyond', 'Build beyond.', 'Intelligent systems, robots, prototypes and secure platforms.', src), ('idea-to-object', 'From idea to object.', 'Prototype Lab. Drones, models, watches, pendants.', (R / 'render/out/print-pendant/f000.png' if (R / 'render/out/print-pendant/f000.png').exists() else R / 'render/out/poster-pendant/f000.png'))]
SIZES = {'A3': (297, 420), 'A2': (420, 594)}
css = (T / 'doc.css').read_text().split('@page')[0].replace('../../public/fonts/', (R / 'public/fonts').as_uri() + '/')
jobs = []
for size, (w, h) in SIZES.items():
    for key, title, sub, img in LINES:
        bw, bh = w + 6, h + 6; s = w / 297
        html = f'''<!doctype html><html><head><meta charset="utf-8"><style>{css}
@page{{size:{bw}mm {bh}mm;margin:0}}body{{background:#0B0B0D}}
.p{{width:{bw}mm;height:{bh}mm;position:relative;overflow:hidden;background:#0B0B0D}}
.bg{{position:absolute;inset:0;background:radial-gradient(60% 45% at 50% 42%,rgba(207,224,236,.18),transparent 70%)}}
.im{{position:absolute;left:3mm;right:3mm;top:{30*s}mm;width:{w}mm;height:auto;-webkit-mask:radial-gradient(closest-side,#000 64%,transparent);mask:radial-gradient(closest-side,#000 64%,transparent)}}
.t{{position:absolute;left:{3+18*s}mm;right:{3+18*s}mm;bottom:{3+30*s}mm}}
.t h1{{font:700 {30*s}mm/0.95 D-DIN;letter-spacing:.04em;text-transform:uppercase;color:#F0F0FA}}
.t p{{font:400 {5.2*s}mm/1.4 Inter;color:rgba(240,240,250,.78);margin-top:{6*s}mm}}
.hd{{position:absolute;left:{3+18*s}mm;top:{3+16*s}mm;display:flex;align-items:center;gap:{3*s}mm}}.hd svg{{width:{9*s}mm;height:{9*s}mm}}.hd b{{font:900 {6*s}mm Inter;color:#F0F0FA}}
.ft{{position:absolute;left:{3+18*s}mm;right:{3+18*s}mm;bottom:{3+14*s}mm;display:flex;justify-content:space-between;font:500 {3*s}mm D-DIN;letter-spacing:.14em;text-transform:uppercase;color:rgba(240,240,250,.55)}}
.hair{{position:absolute;left:{3+18*s}mm;bottom:{3+24*s}mm;width:{18*s}mm;height:{.6*s}mm;background:#E8541A}}
</style></head><body><div class="p"><div class="bg"></div><img class="im" src="{img.as_uri()}">
<div class="hd"><svg viewBox="0 0 100 100"><rect width="22" height="100" fill="#F0F0FA"/><polygon points="26,0 56,0 58.88,16 28.88,16" fill="#E8541A"/><polygon points="29.96,22 59.96,22 74,100 44,100" fill="#F0F0FA"/><rect x="78" width="22" height="100" fill="#F0F0FA"/></svg><b>NSKO</b></div>
<div class="t"><h1>{title}</h1><p>{sub}</p></div><div class="hair"></div><div class="ft"><span>nskosolutions.co.uk</span><span>Built by NSKO</span></div></div></body></html>'''
        f = T / 'out' / f'poster-{key}-{size}.html'; f.parent.mkdir(exist_ok=True); f.write_text(html)
        jobs.append([str(f), str(OUT / f'nsko-poster-{key}-{size}-3mm-bleed.pdf')])
js = "const {chromium}=require('/opt/node22/lib/node_modules/playwright');(async()=>{const b=await chromium.launch();const p=await b.newPage();for(const [f,o] of JSON.parse(process.argv[1])){await p.goto('file://'+f,{waitUntil:'networkidle'});await p.pdf({path:o,printBackground:true,preferCSSPageSize:true});}await b.close();})()"
subprocess.run(['node', '-e', js, json.dumps(jobs)], check=True)
print('source image:', src.name, '\n' + '\n'.join(o for _, o in jobs))
