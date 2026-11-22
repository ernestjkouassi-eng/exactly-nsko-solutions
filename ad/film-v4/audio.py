# Soundtrack + sound design for the NSKO Solutions launch film, generated in code (48 kHz stereo).
# Writes: music.wav (bed), sfx.wav (effects), and the 15 s cut versions.
import numpy as np
from scipy.signal import butter, sosfilt
from scipy.io import wavfile
SR = 48000; DUR = 60.0; BEAT = .6
rng = np.random.default_rng(11)
N = int(SR * DUR)
def T(d): return np.arange(int(SR * d)) / SR
def lp(x, f, o=2): return sosfilt(butter(o, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x)
def bp(x, a, b): return sosfilt(butter(2, [a, b], 'band', fs=SR, output='sos'), x)
def env(n, a, r): e = np.ones(n); ai = max(1, int(a * SR)); e[:ai] = np.linspace(0, 1, ai); e *= np.exp(-np.arange(n) / SR / r) if r else 1; return e
def put(buf, x, t, g=1.0, pan=0.0):
    i = int(t * SR); x = x[:max(0, buf.shape[0] - i)]
    if i < 0: return
    buf[i:i + len(x), 0] += x * g * (1 - max(0, pan)); buf[i:i + len(x), 1] += x * g * (1 + min(0, pan))
# ---------- instruments ----------
def kick():
    t = T(.5); f = 44 + 110 * np.exp(-t * 28); ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 7) * .9 + lp(rng.standard_normal(len(t)), 3000) * np.exp(-t * 90) * .15
def hat(o=False):
    t = T(.25 if o else .06); return hp(rng.standard_normal(len(t)), 7000) * np.exp(-t * (14 if o else 70)) * .22
def sub_boom(d=2.2):
    t = T(d); f = 30 + 60 * np.exp(-t * 4); ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * 1.6); crack = lp(rng.standard_normal(len(t)), 900) * np.exp(-t * 18) * .5
    return (body + crack) * env(len(t), .004, 0)
def whoosh(d=.9, up=True):
    t = T(d); n = rng.standard_normal(len(t)); out = np.zeros(len(t)); seg = 960
    for i in range(0, len(t), seg):
        k = i / len(t); fc = (300 + 4200 * (k if up else 1 - k)); out[i:i + seg] = bp(n[i:i + seg + 0][:seg], max(80, fc * .6), min(20000, fc * 1.4))[:len(out[i:i + seg])]
    sh = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 1.6
    return lp(out, 9000) * sh * .9
def riser(d=1.8):
    t = T(d); f = 120 * (2 ** (t / d * 3)); ph = 2 * np.pi * np.cumsum(f) / SR
    tone = (np.sin(ph) + .4 * np.sin(2 * ph) + .2 * np.sin(3.01 * ph)) * .25
    noise = hp(rng.standard_normal(len(t)), 1500) * .25
    return (tone + noise) * (t / d) ** 2.2
def braam(d=3.5):
    t = T(d); out = np.zeros(len(t))
    for f, g in [(55, 1), (55 * 1.5, .6), (110, .7), (110.6, .5), (164.8, .35), (220, .25)]:
        saw = 2 * ((t * f) % 1) - 1; out += saw * g
    out = lp(out, 900, 4) * env(len(t), .03, 1.4) * .35
    return out + sub_boom(d) * .8
def tick():
    t = T(.03); return np.sin(2 * np.pi * 3200 * t) * np.exp(-t * 300) * .18
def tap():
    t = T(.12); return (np.sin(2 * np.pi * 1800 * t) * .5 + np.sin(2 * np.pi * 2700 * t) * .25) * np.exp(-t * 60) * .35
def shimmer(d=1.2):
    t = T(d); out = sum(np.sin(2 * np.pi * f * t + rng.random() * 6) for f in (2093, 2637, 3136, 4186)) / 4
    return out * env(len(t), .02, .45) * .12
# ---------- bed ----------
music = np.zeros((N, 2)); sfx = np.zeros((N, 2))
t = T(DUR)
# dark drone: detuned low pad on A, slow filter movement
drone = np.zeros(N)
for f, g in [(55, 1), (55.3, .8), (82.4, .5), (110.2, .35), (130.8, .22)]:
    drone += np.sin(2 * np.pi * f * t + rng.random() * 6) * g
drone = lp(drone, 400) * (.55 + .45 * np.sin(2 * np.pi * t / 9.6) ** 2)
drone_env = np.clip(t / 2.5, 0, 1) * np.clip((60 - t) / 1.5, 0, 1)
music[:, 0] += drone * drone_env * .16; music[:, 1] += np.roll(drone, 240) * drone_env * .16
air = lp(hp(rng.standard_normal(N), 2000), 6000) * .015 * drone_env; music[:, 0] += air; music[:, 1] += np.roll(air, 999)
# pulse: from the logo hit; full beat through the scenes; breaks for the CTA build; out for end card
def in_rng(x, a, b): return a <= x < b
K = kick(); H = hat(); HO = hat(True)
b = 7.2
while b < 55.2:
    full = in_rng(b, 11.4, 49.2); half = in_rng(b, 7.2, 11.4)
    beat_i = int(round(b / BEAT))
    if full or (half and beat_i % 2 == 0): put(music, K, b, .55 if full else .45)
    if full:
        put(music, H, b + BEAT / 2, .7, .3); put(music, H, b + BEAT * .25, .25, -.3); put(music, H, b + BEAT * .75, .25, -.3)
        if beat_i % 4 == 2: put(music, HO, b, .4, .2)
    b += BEAT
# bass pulse (8ths) on A / F / C / G every bar (4 beats) during the scenes
roots = [55, 43.65, 65.41, 49]
b = 11.4
while b < 49.2:
    bar = int((b - 11.4) / (4 * BEAT)); f = roots[bar % 4]
    for k in range(8):
        tt = T(BEAT / 2 * .9); note = (np.sin(2 * np.pi * f * tt) + .3 * np.sin(4 * np.pi * f * tt)) * env(len(tt), .005, .12)
        put(music, lp(note, 500), b + k * BEAT / 2, .32)
    b += 4 * BEAT
# ---------- sound design cues (master timeline) ----------
for i in range(len('NSKO SOLUTIONS  PRESENTS')):
    put(sfx, tick(), .5 + i * .5 / 24, .55, (i % 2 - .5) * .4)
put(sfx, sub_boom(), 2.4, .9); put(sfx, sub_boom(), 2.58, .5)
put(sfx, whoosh(1.4), 5.3, .7)
put(sfx, riser(1.8), 5.4, .75)
put(sfx, braam(4.0), 7.2, .95); put(sfx, shimmer(1.8), 7.6, .9)
for i in range(18): put(sfx, tick(), 9.3 + i * .028, .4)
# screen scenes: whoosh in, kicker typing ticks, tap when headline lands, whoosh out
for a, bb, up in [(11.4, 16.8, False), (16.8, 22.8, False), (22.8, 28.2, False), (28.2, 33.6, True)]:
    put(sfx, whoosh(1.0), a - .45, .75, -.2); put(sfx, tap(), a + .6, .5)
    for i in range(14): put(sfx, tick(), a + .45 + i * .035, .3)
    put(sfx, whoosh(.9, up), bb - .75, .6, .25)
put(sfx, shimmer(1.0), 11.9, .8)
# drone step change inside the recording
put(sfx, tap(), 16.8 + 3.0, .4)
# sectors: a hit and a short whoosh per title
for i in range(5):
    a = 33.6 + i * 1.44; put(sfx, sub_boom(1.2), a, .55); put(sfx, whoosh(.5), a - .2, .45, (i % 2 - .5) * .6); put(sfx, tap(), a + .05, .3)
# proof montage: whoosh per clip + UI tap
for i in range(5):
    a = 41.0 + i * 1.88; put(sfx, whoosh(.8), a - .45, .65, .3 - .15 * i); put(sfx, tap(), a + .1, .45)
put(sfx, tap(), 41.2, .4)
# CTA: riser into hit, dots scatter whoosh
put(sfx, riser(1.2), 49.2, .7); put(sfx, sub_boom(2.5), 50.4, 1.0); put(sfx, whoosh(1.6, False), 50.4, .6)
for i in range(20): put(sfx, tick(), 50.6 + i * .025, .35)
# end card
put(sfx, braam(4.6), 55.2, .8); put(sfx, shimmer(2.0), 55.6, .8)
for i in range(30): put(sfx, tick(), 56.6 + i * .02, .25)
# ---------- master, write ----------
def clean(x): x = hp(x.T, 28).T; return np.tanh(x * 1.1) / 1.1
music = clean(music); sfx = clean(sfx)
def w(name, x): wavfile.write(name, SR, (np.clip(x, -1, 1) * 32767).astype(np.int16))
w('music.wav', music); w('sfx.wav', sfx)
# 15 s cut: slices of the master on the beat grid, joined with short crossfades, plus a whoosh on each cut
CUTMAP = [[0, 2.4, 2.4], [2.4, 4.2, 7.2], [4.2, 6.6, 17.4], [6.6, 8.4, 24.0], [8.4, 10.2, 29.4], [10.2, 11.4, 52.2], [11.4, 15, 56.4]]
def cut(src):
    out = np.zeros((int(15 * SR), 2)); xf = int(.012 * SR)
    for a, bb, m in CUTMAP:
        i0 = int(a * SR); n = int((bb - a) * SR); s = src[int(m * SR): int(m * SR) + n + xf].copy()
        ramp = np.linspace(0, 1, xf)[:, None]; s[:xf] *= ramp; s[-xf:] *= ramp[::-1]
        out[i0:i0 + len(s)] += s[:len(out) - i0]
    return out
mc = cut(music); sc = cut(sfx)
for a, bb, m in CUTMAP[1:]: put(sc, whoosh(.6), a - .3, .5); put(sc, sub_boom(.9), a, .35)
fade = np.clip((15 - np.arange(len(mc)) / SR) / 1.0, 0, 1)[:, None]
w('music_15.wav', mc * fade); w('sfx_15.wav', sc * fade)
print('ok')
