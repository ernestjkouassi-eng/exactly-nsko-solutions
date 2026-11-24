#!/usr/bin/env python3
"""NSKO v4.2 Instagram posts (1080x1350) from the branded product renders. Renders HTML with Playwright."""
import pathlib, subprocess, json
H = pathlib.Path(__file__).resolve().parent; R = H.parent.parent
OUT = H / 'posts'; OUT.mkdir(exist_ok=True); TMP = H / 'html'; TMP.mkdir(exist_ok=True)
FONTS = (R / 'public/fonts').as_uri()
MARK = '<svg viewBox="0 0 100 100" width="34" height="34"><rect width="22" height="100" fill="#F0F0FA"/><polygon points="26,0 56,0 58.88,16 28.88,16" fill="#E8541A"/><polygon points="29.96,22 59.96,22 74,100 44,100" fill="#F0F0FA"/><rect x="78" width="22" height="100" fill="#F0F0FA"/></svg>'
POSTS = [
 ('01-robot', 'robot', 'Robotics', 'NSKO R1', 'Six axes. One standard.'),
 ('02-sentinel', 'quad', 'Defence systems', 'NSKO Sentinel', 'Eyes where people should not go.'),
 ('03-surgical', 'surgical', 'Healthcare · concept', 'Surgical Assist', 'Precision you can see.'),
 ('04-tower', 'arch', '3D building models', 'NSKO Tower 1:200', 'Scale models that sell the idea.'),
 ('05-tourbillon', 'watch', 'Watches', 'NSKO Tourbillon', 'Engineering you can wear.'),
 ('06-medallion', 'pendant', 'Prototype Lab', 'Iced Medallion', 'From idea to object.'),
 ('07-n1', 'n1', 'Secure platforms', 'NSKO N1', 'Security starts in the silicon.'),
 ('08-build-beyond', 'wire', 'NSKO Solutions', 'Build beyond.', 'Intelligent systems, robots, prototypes and secure platforms.'),
]
CSS = f'''@font-face{{font-family:D;src:url({FONTS}/D-DIN-Bold.woff2)}}@font-face{{font-family:I;src:url({FONTS}/Inter.woff2);font-weight:100 900}}
*{{margin:0;box-sizing:border-box}}body{{width:1080px;height:1350px;background:#0B0B0D;color:#F0F0FA;overflow:hidden;position:relative;font-family:I}}
.bg{{position:absolute;inset:0;background-size:cover;background-position:center 40%}}
.sh{{position:absolute;inset:0;background:linear-gradient(180deg,rgba(11,11,13,.55) 0%,rgba(11,11,13,0) 22%,rgba(11,11,13,0) 55%,rgba(11,11,13,.92) 82%,#0B0B0D 100%)}}
.top{{position:absolute;left:64px;right:64px;top:58px;display:flex;justify-content:space-between;align-items:center}}
.brand{{display:flex;align-items:center;gap:14px}}.brand b{{font:900 30px I;letter-spacing:-.02em}}
.k{{font:600 17px D;letter-spacing:.28em;text-transform:uppercase;color:rgba(240,240,250,.72)}}
.bot{{position:absolute;left:64px;right:64px;bottom:70px}}
.hair{{width:64px;height:3px;background:#E8541A;margin:0 0 26px}}
h1{{font:700 104px/0.95 D;letter-spacing:.04em;text-transform:uppercase}}
p{{font:400 30px/1.35 I;color:rgba(240,240,250,.82);margin-top:22px;max-width:860px}}
.foot{{display:flex;justify-content:space-between;margin-top:40px}}'''
jobs = []
for key, img, kicker, title, line in POSTS:
    src = R / f'public/media/v42/poster/{img}-tall.webp'
    if not src.exists(): src = R / f'public/media/v42/poster/{img}-1600.webp'
    html = f'''<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<div class="bg" style="background-image:url({src.as_uri()})"></div><div class="sh"></div>
<div class="top"><div class="brand">{MARK}<b>NSKO</b></div><span class="k">NSKO Solutions</span></div>
<div class="bot"><div class="hair"></div><span class="k">{kicker}</span><h1 style="margin-top:18px">{title}</h1><p>{line}</p>
<div class="foot"><span class="k">nskosolutions.co.uk</span><span class="k">Built by NSKO</span></div></div></body></html>'''
    f = TMP / f'{key}.html'; f.write_text(html); jobs.append([str(f), str(OUT / f'nsko-{key}.jpg')])
js = """const {chromium}=require('/opt/node22/lib/node_modules/playwright');(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1080,height:1350}});
for(const [f,o] of JSON.parse(process.argv[1])){await p.goto('file://'+f,{waitUntil:'networkidle'});await p.waitForTimeout(300);await p.screenshot({path:o,type:'jpeg',quality:94});}await b.close();})()"""
subprocess.run(['node', '-e', js, json.dumps(jobs)], check=True)
print('\n'.join(o for _, o in jobs))
