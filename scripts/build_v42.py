#!/usr/bin/env python3
"""Build the v4.2 site: home page plus a static copy for every shareable panel URL."""
import os, pathlib
R = pathlib.Path(__file__).resolve().parent.parent
tpl = (R / 'site-src/index.tpl.html').read_text()
TS = os.environ.get('TURNSTILE_SITEKEY', '').strip()
if TS: tpl = tpl.replace('<meta name="nsko-route"', f'<meta name="nsko-ts" content="{TS}"><meta name="nsko-route"')
D = 'Intelligent systems, robots, prototypes and secure platforms for healthcare, government, defence and industry.'
routes = {
  '': ('NSKO Solutions · Build beyond.', D),
  'start': ('Start a project · NSKO Solutions', 'Tell us what you want to build. We reply to every brief.'),
  'capabilities/intelligent-systems': ('Intelligent systems · NSKO Solutions', 'Perception, planning and control software for robots, drones and fleets.'),
  'capabilities/robotics': ('Robotics and prototypes · NSKO Solutions', 'Small robots, robot arms and working 3D-printed prototypes, built in house.'),
  'capabilities/secure-platforms': ('Secure platforms · NSKO Solutions', 'Web, mobile and data platforms for regulated work, with audit trails.'),
  'capabilities/cyber-security': ('Cyber security · NSKO Solutions', 'Penetration testing, technical bug sweeps and plain-English reports.'),
  'lab/quadruped': ('Inspection quadruped · Prototype Lab · NSKO Solutions', 'From idea to object. An unarmed inspection robot concept.'),
  'lab/architecture': ('Architectural scale model · Prototype Lab · NSKO Solutions', 'From idea to object. A 1:200 stacked tower model concept.'),
  'lab/watch': ('Watch · Prototype Lab · NSKO Solutions', 'From idea to object. A minimal watch concept.'),
  'lab/pendant': ('Pendant · Prototype Lab · NSKO Solutions', 'From idea to object. An iced medallion with the NSKO mark.'),
  'lab/portfolio': ('Portfolio pack · Prototype Lab · NSKO Solutions', 'Request renders, drawings and build notes from the Prototype Lab.'),
  'projects/nsko': ('NSKO · Projects · NSKO Solutions', 'Our live fitness, health and coaching membership.'),
  'projects/wellspring': ('NSKO 1.1 Wellspring · Projects · NSKO Solutions', 'A working demo on simulated data.'),
  'projects/pure': ('NSKO 1.2 Pure · Projects · NSKO Solutions', 'An early concept.'),
}
for r, (t, d) in routes.items():
    path = '/' + r + ('/' if r else '')
    h = tpl.replace('{{TITLE}}', t).replace('{{DESC}}', d).replace('{{PATH}}', path).replace('{{ROUTE}}', r)
    out = R / 'public' / r / 'index.html' if r else R / 'public/index.html'
    out.parent.mkdir(parents=True, exist_ok=True); out.write_text(h)
# NSKO QUANT product page: its own template (site-src/nsko-quant.html), same Turnstile key injection.
q = (R / 'site-src/nsko-quant.html').read_text()
if TS: q = q.replace('<meta name="nsko-route"', f'<meta name="nsko-ts" content="{TS}"><meta name="nsko-route"')
(R / 'public/nsko-quant').mkdir(parents=True, exist_ok=True); (R / 'public/nsko-quant/index.html').write_text(q)
sm = ['/', '/nsko-quant/', '/trust/', '/impact/', '/privacy/', '/security/'] + ['/' + r + '/' for r in routes if r and r != 'start']
(R / 'public/sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + ''.join(f'<url><loc>https://nskosolutions.co.uk{u}</loc></url>\n' for u in sm) + '</urlset>\n')
print('built', len(routes), 'pages')
