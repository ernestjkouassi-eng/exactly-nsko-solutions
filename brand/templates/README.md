# NSKO brand templates (v4.2)

| Template | Makes | Run |
|---|---|---|
| `make_docs.py` + `doc.css` | Capability statement, portfolio pack, grant pack (A4 PDF) | `python3 make_docs.py grants-2026-11.json` |
| `make_posters.py` | Posters A3 and A2, 3 mm bleed (PDF) | `python3 make_posters.py` |
| `film/promo.html` | 56 s promo film, 16:9 (3840x2160) and 9:16 (2160x3840) | `node film/render.js chunk promo h 0 1344 out.mp4 2` |
| `film/score.py` | Original soundtrack (synthesised, no licensed music) | `python3 film/score.py` |
| `../../render/objects.py` | Blender 3D objects and turntables | see `render/run2.sh` |

Rules: images are never shown above their rendered size. No "cutting-edge", "revolutionary", "next-gen", no exclamation marks.
Remotion was not used: the HTML film engine does the same job with no extra install.
