#!/usr/bin/env python3
"""Original NSKO score, synthesised here (no samples, no licensed music). 56 s, 48 kHz stereo.
Dark drone, slow pad, soft pulse from scene 2, sub hits on title moments, riser into the end card."""
import numpy as np, scipy.io.wavfile as wf, scipy.signal as ss
SR, D = 48000, 56.0; n = int(SR * D); t = np.arange(n) / SR; rng = np.random.default_rng(7)
def env(a, b, fi=1.5, fo=2.0): return np.clip(np.minimum((t - a) / fi, (b - t) / fo), 0, 1)
def lp(x, f): return ss.sosfilt(ss.butter(2, f, 'low', fs=SR, output='sos'), x)
L = np.zeros(n); R = np.zeros(n)
# drone: A1 + E2 with slow beating
for f, g in [(55, .22), (55.4, .16), (82.4, .12), (110, .06)]:
    ph = rng.uniform(0, 6.28); w = np.sin(2 * np.pi * f * t + ph) + .3 * np.sin(4 * np.pi * f * t + ph)
    L += g * w * env(0, 56, 4, 3); R += g * np.roll(w, 37) * env(0, 56, 4, 3)
# pad chords (Am9 -> Fmaj7 -> Cmaj7 -> Em7), filtered saw-ish, changes on scenes
chords = [(4, 13, [220, 261.6, 329.6, 493.9]), (13, 29, [174.6, 220, 261.6, 329.6]), (29, 40, [130.8, 196, 246.9, 329.6]), (40, 51, [164.8, 196, 246.9, 293.7]), (51, 56, [220, 261.6, 329.6, 440])]
for a, b, fs in chords:
    e = env(a - .5, b + 1.5, 2.0, 2.5); pad = np.zeros(n)
    for f in fs:
        for d in (-.18, .18): pad += sum(np.sin(2 * np.pi * k * (f + d) * t) / k for k in (1, 2, 3)) * .022
    pad = lp(pad, 1400) * e; L += pad; R += np.roll(pad, 240)
# pulse: soft kick + tick at 96 bpm from 13 s to 51 s
bpm = 96; beat = 60 / bpm
for k in np.arange(13, 50.9, beat):
    i = int(k * SR); m = min(n - i, int(.35 * SR)); tt = np.arange(m) / SR
    kick = np.sin(2 * np.pi * (50 + 60 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 9) * .32
    L[i:i + m] += kick; R[i:i + m] += kick
    j = int((k + beat / 2) * SR); mm = min(n - j, int(.05 * SR))
    if mm > 0: tick = lp(rng.normal(0, 1, mm), 6000) * np.exp(-np.arange(mm) / SR * 80) * .05; L[j:j + mm] += tick; R[j:j + mm] += tick * .7
# sub hits on titles
for h in (5.6, 13.2, 29.4, 40.3, 46.3, 51.8):
    i = int(h * SR); m = min(n - i, int(2.5 * SR)); tt = np.arange(m) / SR
    s = np.sin(2 * np.pi * (38 + 30 * np.exp(-tt * 6)) * tt) * np.exp(-tt * 1.6) * .5
    air = lp(rng.normal(0, 1, m), 2500) * np.exp(-tt * 3) * .05
    L[i:i + m] += s + air; R[i:i + m] += s + np.roll(air, 50)
# riser into the end card
rs = env(47.5, 51.8, 4.0, .05) ** 2; noise = rng.normal(0, 1, n)
sw = ss.sosfilt(ss.butter(2, [400, 5000], 'band', fs=SR, output='sos'), noise) * rs * .09; L += sw; R += np.roll(sw, 90)
# master: gentle fade, soft clip
fade = env(0, 56, .5, 3.0); L *= fade; R *= fade
st = np.stack([L, R], 1); st = np.tanh(st * 1.2) / 1.2; st /= np.abs(st).max() * 1.12
wf.write('score.wav', SR, (st * 32767).astype(np.int16)); print('score.wav', D, 's')
