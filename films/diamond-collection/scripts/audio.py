# Score + foley for the Diamond Collection film, synthesised in code (royalty-free by construction).
# Slow luxury score at 70 BPM (warm pad, soft felt-piano notes, low pulse) + subtle physical foley on the real object motion.
import numpy as np, wave, os, sys
SR = 48000; DUR = 32.0; N = int(SR * DUR); rng = np.random.default_rng(7)
t = np.arange(N) / SR
BEAT = 60 / 70; BAR = 4 * BEAT
def note(f): return 440 * 2 ** ((f - 69) / 12)
mix = np.zeros((N, 2))

def add(sig, start, pan=0., gain=1.):
    i = max(0, int(start * SR)); j = min(N, i + len(sig))
    if j <= i: return
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    mix[i:j, 0] += sig[:j - i] * l * gain; mix[i:j, 1] += sig[:j - i] * r * gain

def env(n, a, r):
    e = np.ones(n); na = int(a * SR); nr = int(r * SR)
    e[:na] = np.linspace(0, 1, na) ** 2
    if nr: e[-nr:] *= np.linspace(1, 0, nr) ** 2
    return e

# pad: Am9 - Fmaj9 - Cmaj7 - G6sus, two bars each, slow detuned saws through a soft low-pass
chords = [[57, 60, 64, 67, 71], [53, 57, 60, 64, 67], [48, 55, 59, 64, 67], [55, 59, 62, 64, 69]]
def lowpass(x, fc):
    from scipy.signal import lfilter
    a = np.exp(-2 * np.pi * fc / SR); return lfilter([1 - a], [1, -a], x)
pad = np.zeros(N)
for ci in range(int(DUR / (2 * BAR)) + 1):
    st = ci * 2 * BAR; n = int(2 * BAR * SR) + int(1.5 * SR); tt = np.arange(n) / SR; s = np.zeros(n)
    for m in chords[ci % 4]:
        for d in (-.07, 0, .06):
            f = note(m) * 2 ** (d / 12); s += ((tt * f) % 1 * 2 - 1) * .5 + np.sin(2 * np.pi * f * tt)
    s *= env(n, 1.2, 1.6); i = int(st * SR); j = min(N, i + n); pad[i:j] += s[:j - i]
pad = lowpass(pad, 900) * .018
mix[:, 0] += pad; mix[:, 1] += np.roll(pad, 400)

# felt-piano motif on beats (soft, sparse)
def piano(f, dur=3.0):
    n = int(dur * SR); tt = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * h * tt) * np.exp(-tt * (1.6 + h * .9)) / h ** 1.3 for h in (1, 2, 3, 4))
    return s * np.minimum(1, tt / .008)
motif = [76, 74, 72, 71, 72, 74, 76, 79]
for b in range(int(DUR / BEAT)):
    if b % 2 == 0 and 3.0 < b * BEAT < 30.0:
        add(piano(note(motif[(b // 2) % len(motif)])), b * BEAT, pan=.25 * np.sin(b), gain=.07)
# low pulse on each bar
for b in range(int(DUR / BAR) + 1):
    n = int(1.2 * SR); tt = np.arange(n) / SR
    add(np.sin(2 * np.pi * 55 * tt) * np.exp(-tt * 3.5) * np.minimum(1, tt / .02), b * BAR + 3.0 if b * BAR + 3.0 < 30 else 99, gain=.12)

# foley: real metal on metal (inharmonic partials, short), velvet whoosh (band-limited noise swell)
def clink(scale=1.):
    n = int(.6 * SR); tt = np.arange(n) / SR
    return sum(np.sin(2 * np.pi * f * scale * tt) * np.exp(-tt * d) * g for f, d, g in ((2730, 14, 1), (4120, 18, .6), (6310, 25, .35), (8890, 30, .2))) * np.minimum(1, tt / .001)
def whoosh(d=1.2):
    n = int(d * SR); x = rng.standard_normal(n); x = lowpass(x, 1400) - lowpass(x, 250)
    return x * np.sin(np.linspace(0, np.pi, n)) ** 2
for at, sc, g in ((7.62, 1, .05), (10.55, .93, .06), (13.0, 1.08, .04), (15.55, 1, .05), (17.4, 1.12, .04), (20.45, 1.05, .05),
                  (25.55, 1.0, .035), (25.7, 1.2, .03), (25.82, .95, .03)):
    add(clink(sc), at, pan=rng.uniform(-.3, .3), gain=g)
for at, d, g in ((.2, 2.2, .5), (3.0, 1.0, .25), (11.0, 1.0, .25), (16.0, 1.0, .25), (21.0, 1.0, .25), (21.9, 1.4, .3), (26.5, 1.6, .35), (30.0, 1.6, .4)):
    add(whoosh(d), at - .3, gain=g)

# room: short convolution reverb
ir_n = int(2.2 * SR); ir = rng.standard_normal(ir_n) * np.exp(-np.arange(ir_n) / SR * 3.2); ir[0] = 0
L = 1 << int(np.ceil(np.log2(N + ir_n)))
wet = np.stack([np.fft.irfft(np.fft.rfft(mix[:, c], L) * np.fft.rfft(ir * .012, L), L)[:N] for c in (0, 1)], 1)
out = mix + wet * .6
out *= env(N, .05, 1.8)[:, None]
out /= max(1e-9, np.abs(out).max()) / .7
fn = sys.argv[1] if len(sys.argv) > 1 else 'score.wav'
with wave.open(fn, 'w') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((out * 32767).astype('<i2').tobytes())
print('wrote', fn)
