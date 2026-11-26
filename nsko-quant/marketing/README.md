# NSKO QUANT: video ad and posters

Promotional material for **NSKO QUANT · by NSKO Solutions**. The look is dark, slow and expensive: background #08080F, one accent colour (NSKO orange #E8541A), green #78D880 and red #E04858 only for money. Every app shot is the real app in demo mode, and a **DEMO DATA** label sits in a corner of each one.

## What was made

| File | What it is | Size |
|---|---|---|
| `video/out/nsko-quant-ad-16x9.mp4` | 60 s master, 1920×1080, 30 fps, H.264 CRF 18 (veryfast), yuv420p, AAC 192k, −14.3 LUFS integrated, −1.3 dBTP | 33.2 MB |
| `video/out/nsko-quant-ad-9x16.mp4` | 30 s cut, 1080×1920, for Instagram and TikTok. VO v01, v02, v05, v06, v08. Captions burned in. −14.5 LUFS | 11.4 MB |
| `video/out/nsko-quant-ad-16x9-silent.mp4` | The master with no audio track. Captions are burned in, because silent placements autoplay muted | 31.4 MB |
| `video/out/nsko-quant-ad.srt` | Captions for the 60 s master (9 cues) | 1 KB |
| `poster/out/nsko-quant-poster-A3.pdf` | A3 portrait print file (297×420 mm), one page, 300 ppi | 2.0 MB |
| `poster/out/nsko-quant-poster-A3-300dpi.png` | The same A3 artwork as a 3508×4961 PNG | 1.8 MB |
| `poster/out/nsko-quant-poster-instagram-1080x1350.png` | Instagram feed post | 0.3 MB |
| `poster/out/nsko-quant-poster-story-1080x1920.png` | Story or Reel cover | 0.3 MB |

QA contact sheets are in `video/qa/`.

### The 60 s master, scene by scene
| Time | Scene | VO |
|---|---|---|
| 0–4 s | Black. An orange line draws across, the caption types out "LONDON · 03:00" with key clicks | none |
| 4–9 s | The NSKO // QUANT wordmark lights up letter by letter, "by NSKO Solutions" | v01 at 4.8 s |
| 9–16 s | Overview: the brain sphere, particle bursts and the scrolling ticker, with a slow push-in | v02 at 10.0 s |
| 16–22 s | Research star field, then the Agent Room | v03 at 16.8 s |
| 22–28 s | God's Eye globe, panning to the MARKET IMPACT cards | v04 at 22.8 s |
| 28–36 s | The Lab equity fan (in-sample, then out-of-sample) | v05 at 28.8 s |
| 36–46 s | Trade Card: Scanner ✓ → Forecast fan → Time Machine to 10,000 → odds → Risk ✓ → lock opens → SENT ✓ → P&L | v06 at 36.8 s |
| 46–52 s | Live Desk with order-flow bubbles, plus a phone-style notification "Trade closed +1.8R (demo)" | v07 at 46.6 s |
| 52–60 s | Slow push-in on the lockup, "Trade the markets. Automatically.", nskosolutions.co.uk, fine print "Demo data. Trading involves risk. You can lose money." | v08 at 53.0 s |

Scenes are joined with 0.5 s dissolves. Camera moves are eased in and out with sub-pixel precision. A light vignette and fine grain are on top. In the app shots the clock reads about 03:01 to 03:05 London time, to match the opening.

The 30 s vertical cut runs: line and caption (v01), the brain sphere (v02), a pan across the Lab fan (v05), the Trade Card reframed as the step bar plus three stacked panels (Time Machine, Order ticket, Exit) (v06), and the lockup (v08).

## Licences
- **Voice:** Piper TTS (MIT), voice `en_GB-northern_english_male-medium`, trained on OpenSLR 83 (**CC BY-SA 4.0**). Credit where the platform allows: "Voice: Piper, OpenSLR 83 (CC BY-SA 4.0)". The script writes the brand as "Nesko" so that it is pronounced correctly.
- **Music and sound:** synthesised in code by NSKO Solutions (`video/audio.py`): a 64 BPM low pulse, sub drone, dark pad, tick-tock clock, typing clicks, quiet risers into the wordmark and the logo, and a soft impact on the lockup. No samples or downloaded music, so no licence applies.
- **Fonts:** Inter and JetBrains Mono, both SIL OFL 1.1.
- Everything is logged in `../assets/LICENSES.md`.

## Known limits
- There is no GPU in the build sandbox. The app was recorded in real time through Chrome's screencast with software rendering at 40 to 50 fps, then resampled to 30 fps. The Agent Room (three.js) ran at only about 20 to 25 fps, so it is a short 3.5 s shot with a slow push. God's Eye (Cesium) ran at about 3 fps, so it is a high-resolution **still** with a slow camera move, not live footage.
- The Trade Card runs its nine steps in about 25 s. For the ad, the app's 50 ms step timer was sped up 2.4× during recording, so the whole flow fits into 10 s. Fades and canvases still run in real time.
- In the app, the Forecast and Time Machine charts redraw from empty at every later step, because they use the time within the current step. Near the end of the Trade Card, these two panels can look empty or only partly drawn. That is how the app behaves today (`app/src/pages/Money.tsx`, `fanDraw` and `tmDraw`), not an editing fault.
- The God's Eye shot shows Esri World Imagery. Check Esri's terms before paid media, or replace that shot with the brain sphere. The app's "Offline" basemap rendered no imagery in the sandbox, so it could not be used instead. The posters do not use the globe.
- The A3 PDF is a 300 ppi raster of the artwork. Chromium renders the tilted Trade Card at low resolution when it prints to vector PDF, so a raster was the sharper option. If a printer asks for vector text, rebuild the card without the 3D tilt.
- The silent version has captions burned in. For a clean silent master, remove the audio track from `nsko-quant-ad-16x9.mp4`.
- The notification card in the Live Desk scene is a marketing overlay drawn for the ad. It is not a screen from the app.

## How to rebuild
Requirements: the app preview at `http://localhost:4190` (`cd ../app && npx vite build && npx vite preview --port 4190`), Playwright, ffmpeg, Python 3 with numpy, scipy and OpenCV. Run each command from `video/` or `poster/` with `NODE_PATH` set to the global node_modules.

```
# video
node rec.js <name> "?page=<page>" <settle s> <record s> [timer speed]   # real-time captures -> rec/*.mp4 (DATE_TARGET sets the app clock)
node stills2.js                                                      # 2x stills (God's Eye)
cd cards && node render.js anim|png ...                              # title cards, labels, captions (cards.html)
python3 compose.py 16x9 && python3 compose.py 9x16                   # camera moves, overlays, dissolves -> work/
python3 audio.py 16x9 && python3 audio.py 9x16                       # synthesised music + VO + ducking -> work/
python3 finish.py 16x9 && python3 finish.py 9x16                     # captions, grade, two-pass loudnorm, encode -> out/
# posters
node capture.js && node render.js && node pdf.js
```
