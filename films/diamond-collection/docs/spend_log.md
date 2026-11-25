# Spend log
| Date | Item | Credits | Note |
|---|---|---|---|
| 2026-11-25 | Reference prep, specs, CPU timing test | 0 | done on this machine |

Balance seen 2026-11-24: Higgsfield 1.84 credits (not enough for any generation or GPU hour).

## Render budget (measured)
- CPU here (4 cores): 300 stones, 540x960, 128 samples = 46 s per frame.
- Scaled to the brief (1620x2880, ~5,000 faceted stones, ~512 samples): about 30 to 60 min per frame. 960 frames = 450+ hours. Not workable.
- Rented L40S GPU (71 credits/hour): estimated 30 to 60 s per frame. 960 frames = 8 to 16 GPU hours = about 570 to 1,140 credits, plus about 150 for tests and stills. Plan: 1,000 to 1,300 credits. Wall time about 3 to 4 hours on 4 GPUs.
- 60 fps capture (brief rule 4) doubles this. Same slow-motion feel at 30 fps with real motion blur and slower moves halves the cost.
