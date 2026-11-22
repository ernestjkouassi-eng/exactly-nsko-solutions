# NSKO Solutions launch film (v4, 22 Nov 2026)

60 s master (3840x2160, 24 fps), 9:16 cut (1080x1920) and 15 s 9:16 reel.

How it is made, all in code, no paid generation:
1. `capture.js` records the live site frame by frame (page clock stepped 1/24 s): hero, drone code lab, Nova robot, Medusa field kit, page glide, sectors, phone view.
2. `mark3d.py` renders the silver 3D NSKO lockup in Blender (Cycles, 25 frames, moving light sweep).
3. `promo.html` is the film: one page driven by `seek(t)` (floating glass screens in 3D, depth blur, light sweeps, dots that assemble the N, titles, rail). `?v=1` = 9:16, `?v=1&cut=15` = 15 s reel.
4. `render.js` screenshots each frame into ffmpeg; `runrender.sh` renders in chunks.
5. `audio.py` synthesises the bed and sound design; two mixes at -14 LUFS (with music / effects only, ready for voice-over).
6. `assemble.sh` joins, muxes and writes web copies to `public/media/film/`.

Story: NSKO SOLUTIONS PRESENTS / Some systems cannot fail / dots assemble the N / silver lockup, Complex made real / 01 Who we are / 02 Machine Intelligence / 03 Prototype Lab / 04 NSKO Secure / five sectors / 05 The work (NSKO app live, site live, phone, concept clips) / 06 Bring us the hard problem / end card.

To do: Isi voice-over (ElevenLabs allowance resets about 6 Dec) and burned-in subtitles.
