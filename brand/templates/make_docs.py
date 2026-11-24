#!/usr/bin/env python3
"""Build NSKO PDFs from HTML templates: capability statement, portfolio pack, grant pack.
Run: python3 make_docs.py [grants.json]  -> HTML in brand/templates/out, PDFs in public/media/v42."""
import json, pathlib, subprocess, sys, html
T = pathlib.Path(__file__).resolve().parent; OUT = T / 'out'; OUT.mkdir(exist_ok=True)
MEDIA = T.parent.parent / 'public/media/v42'
e = html.escape
MARK = '<div class="mark"><svg viewBox="0 0 100 100"><rect width="22" height="100" fill="#F0F0FA"/><polygon points="26,0 56,0 58.88,16 28.88,16" fill="#E8541A"/><polygon points="29.96,22 59.96,22 74,100 44,100" fill="#F0F0FA"/><rect x="78" width="22" height="100" fill="#F0F0FA"/></svg><b>NSKO</b></div>'
def page(body, n, light=False, title=''):
    return f'<section class="pg{" light" if light else ""}">{"" if light else "<div class=glow></div>"}{MARK.replace("#F0F0FA", "#141519") if light else MARK}{body}<div class="foot"><span>{e(title)}</span><span>Built by NSKO · {n}</span></div></section>'
def doc(name, title, pages):
    h = f'<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><title>{e(title)}</title><link rel="stylesheet" href="../doc.css"></head><body>{"".join(pages)}</body></html>'
    (OUT / f'{name}.html').write_text(h); return OUT / f'{name}.html'
def img(o, s=900):
    for c in (MEDIA / 'poster' / f'{o}-1600.webp', MEDIA / 'poster' / f'{o}-{s}.webp'):
        if c.exists(): return c.as_uri()
    return ''
CAP = [('Intelligent systems', 'chip', ['Perception, planning and control software for robots and drones.', 'Platforms that run fleets of machines, with people in charge.', 'Models tested on your own data before anything goes live.']),
       ('Robotics and prototypes', 'arm', ['Small robots and robot arms, designed and built in house.', '3D-printed working prototypes you can hold and test.', 'Test, improve, hand over, with drawings and source files.']),
       ('Secure platforms', 'blade', ['Web, mobile and data platforms for regulated work.', 'Role-based access, audit trails and UK hosting options.', 'Built to pass review by your own security team.']),
       ('Cyber security', 'key', ['Penetration testing of apps, networks and devices.', 'Technical bug sweeps for rooms and vehicles.', 'Plain-English reports with fixes ranked by risk.'])]
TITLE = 'Capability statement'
cap = [page(f'<p class="k" style="margin-top:28mm">Capability statement · 2026</p><h1>Build beyond.</h1><p class="lede">Intelligent systems, robots, prototypes and secure platforms for healthcare, government, defence and industry.</p><div class="hair"></div>'
            f'<img class="img" src="{img("chip")}" style="width:120mm;margin:6mm 0 0 auto" alt=""><div class="grid" style="margin-top:8mm"><div class="box"><h3>Who we are</h3><p>NSKO Solutions is a UK technology firm. We design, build and test the whole system: the software that thinks, the machine that moves and the platform that runs it.</p></div><div class="box"><h3>How we work</h3><p>Fixed scope, short build cycles and a working demo at each step. You own the drawings, code and files we hand over.</p></div></div>', 1, title=TITLE),
       page('<p class="k" style="margin-top:10mm">What we build</p><h2>Four disciplines. One standard.</h2><div class="grid" style="margin-top:6mm">' + ''.join(
            f'<div class="box"><img class="img" src="{img(o)}" style="aspect-ratio:2/1;margin-bottom:3mm" alt=""><h3>{e(t)}</h3><ul class="l">{"".join(f"<li>{e(x)}</li>" for x in b)}</ul></div>' for t, o, b in CAP) +
            '</div><div class="grid" style="margin-top:5mm"><div class="box"><h3>Track record</h3><p>NSKO: our own fitness, health and coaching membership, live on the web, iOS and Android. NSKO 1.1 Wellspring: demo built on simulated data.</p></div>'
            '<div class="box"><h3>Company</h3><p>Company number and registered office: to be added. Cyber Essentials: in progress. Contact: hello@nskosolutions.co.uk · nskosolutions.co.uk</p></div></div>', 2, title=TITLE)]
LAB = [('Drone', 'drone', 'A compact quadcopter frame with a stabilised camera pod. Printed carbon-nylon arms, swappable payload bay.'), ('Architectural scale model', 'arch', 'A 1:200 presentation model for a small mixed-use scheme. White resin on a dark plinth.'),
       ('Watch', 'watch', 'A minimal three-hand watch with a brushed steel case and a signal-orange seconds hand.'), ('Pendant', 'pendant', 'The NSKO mark as a pendant in polished steel, the orange fragment in enamel.')]
TP = 'Prototype Lab portfolio'
pack = [page('<p class="k" style="margin-top:28mm">Prototype Lab · Portfolio pack</p><h1>From idea to object.</h1><p class="lede">Drones, architectural models, watches and pendants. Designed, printed and finished in house. Every item below is labelled with its real status.</p><div class="hair"></div>' +
             f'<img class="img" src="{img("pendant")}" style="width:130mm;margin:4mm auto 0" alt="">', 1, title=TP)]
for i, (t, o, d) in enumerate(LAB):
    pack.append(page(f'<p class="k" style="margin-top:10mm">Prototype Lab · {i + 1:02d}</p><h2>{e(t)}</h2><span class="tag">Concept</span><img class="img" src="{img(o)}" style="margin-top:6mm" alt=""><p class="lede" style="margin-top:6mm">{e(d)}</p><p class="k" style="margin-top:5mm">Studio render made by NSKO. Not a photograph of a finished product.</p>', i + 2, title=TP))
built = [doc('nsko-capability-statement', 'NSKO Solutions capability statement', cap), doc('nsko-portfolio-pack', 'NSKO Prototype Lab portfolio pack', pack)]
if len(sys.argv) > 1:
    G = json.loads(pathlib.Path(sys.argv[1]).read_text()); TG = 'Grant pack'
    PROG = {'water': ('Clean water', 'Low-cost sensor kits that check water quality at the tap and report it to the people who run the supply.'),
            'health': ('Health diagnostics concept', 'A simple screening device and app for clinics with little equipment. A concept only, with no medical claims until it is tested and approved.'),
            'climate': ('Climate and food resilience', 'Drones and ground sensors that help small farms see crop stress, water use and soil health early.')}
    gp = [page('<p class="k" style="margin-top:28mm">Impact · Grant pack</p><h1>Technology with purpose.</h1><p class="lede">Three programme concepts, how each would be funded and run, and the open funding calls that fit. Nothing here is funded yet.</p><div class="hair"></div>'
               '<div class="grid3" style="margin-top:8mm">' + ''.join(f'<div class="box"><h3>{e(a)}</h3><p>{e(b)}</p><span class="tag">Concept</span></div>' for a, b in PROG.values()) + '</div>'
               '<div class="box" style="margin-top:6mm"><h3>Grant structure (each programme)</h3><ul class="l"><li>Phase 1: feasibility and lab tests, 3 to 6 months.</li><li>Phase 2: pilot with a delivery partner.</li><li>Phase 3: scale with partners and local makers.</li><li>Governance: monthly reports, open budget lines, independent evaluation.</li></ul></div>'
               '<div class="box" style="margin-top:5mm"><h3>Still needed</h3><ul class="l"><li>Decision: community interest company (CIC) or charity for this work.</li><li>Named partners and letters of support.</li><li>Confirmed company number and registered office.</li></ul></div>', 1, title=TG)]
    rows = ''.join(f'<tr><td>{e(PROG.get(g["programme"], ("General",))[0])}</td><td><b>{e(g["funder"])}</b><br>{e(g["call_name"])}</td><td>{e(g["amount"])}</td><td>{e(g["deadline"])}</td><td>{e(g["notes"])}<br><a href="{e(g["url"])}">{e(g["url"][:70])}</a></td></tr>' for g in G)
    gp.append(page(f'<p class="k" style="margin-top:10mm">Open and recurring calls · checked 24 Nov 2026</p><h2>Where the money is.</h2><table><tr><th>Programme</th><th>Funder and call</th><th>Amount</th><th>Deadline</th><th>Notes and source</th></tr>{rows}</table><p class="k" style="margin-top:4mm">Always check the funder page before applying. Deadlines change.</p>', 2, title=TG))
    built.append(doc('nsko-grant-pack', 'NSKO Impact grant pack', gp))
js = "const {chromium}=require('/opt/node22/lib/node_modules/playwright');(async()=>{const b=await chromium.launch();const p=await b.newPage();for(const [f,o] of JSON.parse(process.argv[1])){await p.goto('file://'+f,{waitUntil:'networkidle'});await p.pdf({path:o,format:'A4',printBackground:true,preferCSSPageSize:true});}await b.close();})()"
subprocess.run(['node', '-e', js, json.dumps([[str(f), str(MEDIA / (f.stem + '.pdf'))] for f in built])], check=True)
print('\n'.join(str(MEDIA / (f.stem + '.pdf')) for f in built))
