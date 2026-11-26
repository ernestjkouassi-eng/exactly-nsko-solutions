# Media contract

Drop files here with these exact names. Every slot has a built-in fallback, so a missing file never breaks the app.

| File | Used on | Size / aspect | Status | Fallback if missing |
|---|---|---|---|---|
| `founder.mp4` | Founder Film on launch | 720×1280, 9:16, H.264 + AAC, faststart, under 2 MB | Supplied (10.6 s) | Animated stand-in: "Strength is the ability to produce force." |
| `founder.jpg` | Poster for the film | 720×1280, 9:16, JPEG | Supplied | Dark gradient |
| `camp01-duo.jpg` | Account cover, posts grid | 1080×1080, ~1:1, JPEG ≤ 200 KB | Supplied | Gradient with warm light blooms |
| `camp01-group.jpg` | Camp 02 event card, posts grid | 1170×980, ~6:5, JPEG ≤ 200 KB | Supplied | Gradient with warm light blooms |
| `joba.jpg` | Joba's avatar (cropped to face), Weekly Update header | 900×1000, ~9:10, JPEG, face in upper third | Supplied | Initial "J" on cobalt |
| `frankl.jpg` | Founder Line post, posts grid | 900×1000, ~9:10, JPEG | Supplied | Cobalt light gradient |
| `store-tee.png` | Drop 07 Training Tee | 1000×1000, 1:1, PNG with transparent background | Not supplied | Drawn tee silhouette with helix print |
| `store-whey.png` | Specimen Whey | 600×600, 1:1, transparent PNG | Not supplied | Drawn jar |
| `store-creatine.png` | Creatine Mono | 600×600, 1:1, transparent PNG | Not supplied | Drawn jar |

Notes
- People photos are shown with `object-fit: cover` and `object-position` near the top so faces stay in frame.
- Members other than Joba are shown as initials on cobalt. Do not add stock faces.
- Keep JPEGs at quality ~80 and under 200 KB so the first load stays fast on 4G.
