#!/usr/bin/env python3
"""Make the site copy of the Wellspring demo from assets-source (kept unchanged as the source of truth).
The site's CSP allows only same-origin scripts and fonts, so: libraries are self-hosted (three.js r128 from npm),
the inline script moves to app.js, and Google Fonts is swapped for the self-hosted Inter and JetBrains Mono."""
import pathlib, re
R = pathlib.Path(__file__).resolve().parent.parent
src = (R / 'assets-source/demo/wellspring/index.html').read_text()
out = R / 'public/demo/wellspring'; out.mkdir(parents=True, exist_ok=True)
m = re.search(r'<script>\n(\(function\(\)\{.*?\}\)\(\);)\n</script>', src, re.S)
(out / 'app.js').write_text(m.group(1) + '\n')
h = src.replace(m.group(0), '<script src="app.js"></script>')
h = h.replace('<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>', '<script src="three.r128.min.js"></script>')
h = h.replace('<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>', '<script src="OrbitControls.r128.js"></script>')
FONTS = ('<meta name="robots" content="noindex"><style>@font-face{font-family:Inter;src:url(/fonts/Inter.woff2) format("woff2");font-weight:100 900}'
         '@font-face{font-family:"JetBrains Mono";src:url(/fonts/JetBrainsMono-400.woff2) format("woff2");font-weight:400}'
         '@font-face{font-family:"JetBrains Mono";src:url(/fonts/JetBrainsMono-500.woff2) format("woff2");font-weight:500}</style>')
h = re.sub(r'<link href="https://fonts.googleapis.com[^>]*>', FONTS, h)
assert 'googleapis' not in h and 'cdnjs' not in h and 'jsdelivr' not in h and '<script>' not in h
(out / 'index.html').write_text(h)
print('wellspring site copy ok:', len(h), 'bytes html,', (out / 'app.js').stat().st_size, 'bytes js')
