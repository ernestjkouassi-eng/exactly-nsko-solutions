#!/usr/bin/env python3
"""Remove capture flicker from the Trade Card recording.

The demo Trade Card remounts its two <canvas> charts (Forecast fan, Time Machine) on every timer tick. With software
rendering, the screencast sometimes grabs a frame between a remount and the next draw, so the charts blink empty for a
few frames. This pass pastes the last drawn chart back into those frames. A blank run longer than 1.5 s is a real reset
(a new trade cycle), and is left alone.

usage: python3 fix_canvas.py rec/tradecard.mp4 rec/tradecard_rects.json
"""
import json, subprocess, sys, os
import numpy as np

src, rects_path = sys.argv[1], sys.argv[2]
W, H = 1920, 1080
R = [tuple(int(round(v)) for v in r) for r in json.load(open(rects_path))]

dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', src, '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'], stdout=subprocess.PIPE)
frames = []
while True:
    b = dec.stdout.read(W * H * 3)
    if len(b) < W * H * 3:
        break
    frames.append(np.frombuffer(b, np.uint8).reshape(H, W, 3).copy())
dec.wait()

MAXRUN = 45  # frames (1.5 s at 30 fps)
patched = 0
for (x, y, w, h) in R:
    drawn = [(f[y:y + h, x:x + w].max(axis=2) > 60).mean() > .005 for f in frames]
    i = 0
    while i < len(frames):
        if drawn[i]:
            i += 1; continue
        j = i
        while j < len(frames) and not drawn[j]:
            j += 1
        if i > 0 and drawn[i - 1] and j < len(frames) and j - i <= MAXRUN:
            good = frames[i - 1][y:y + h, x:x + w].copy()
            for k in range(i, j):
                frames[k][y:y + h, x:x + w] = good; patched += 1
        i = j

tmp = src + '.tmp.mp4'
enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', '30', '-i', '-',
                        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '14', '-pix_fmt', 'yuv420p', tmp], stdin=subprocess.PIPE)
for f in frames:
    enc.stdin.write(f.tobytes())
enc.stdin.close(); enc.wait()
os.replace(tmp, src)
print('patched', patched, 'region-frames of', len(frames), 'frames')
