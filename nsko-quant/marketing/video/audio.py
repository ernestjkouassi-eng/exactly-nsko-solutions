#!/usr/bin/env python3
"""NSKO QUANT ad: music synthesised in code (no samples, no downloads) + VO placement + ducking.

Music: ~64 BPM low cinematic pulse, soft sub drone, a dark low-passed pad, subtle tick-tock clock,
typing ticks on the opening caption, a quiet riser into the logo and a soft impact on the lockup.
usage: python3 audio.py 16x9|9x16  -> work/mix_<fmt>.wav (48 kHz stereo, unnormalised)
"""
import sys, os
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(7)


def lp(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), 'low'); return signal.lfilter(b, a, x)


def bp(x, f1, f2, order=2):
    b, a = signal.butter(order, [f1 / (SR / 2), f2 / (SR / 2)], 'band'); return signal.lfilter(b, a, x)


def env_adsr(n, a, r):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / r)


def add(buf, x, t0, gain=1.0, pan=0.0):
    i = int(t0 * SR)
    if i >= buf.shape[0]:
        return
    x = x[: buf.shape[0] - i]
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[i:i + len(x), 0] += x * gain * l * 1.414
    buf[i:i + len(x), 1] += x * gain * r * 1.414


def thump(f0=62, f1=40, dur=.7):
    n = int(dur * SR); t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / .06)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * env_adsr(n, .004, .22)
    click = lp(rng.standard_normal(n) * env_adsr(n, .0005, .006), 900)
    return body + .25 * click


def tick(freq=3200, dur=.03):
    n = int(dur * SR)
    return bp(rng.standard_normal(n), freq * .7, freq * 1.3) * env_adsr(n, .0003, .004)


def key_click():
    n = int(.04 * SR)
    x = bp(rng.standard_normal(n), 1800, 6000) * env_adsr(n, .0002, .003)
    x += .4 * bp(rng.standard_normal(n), 300, 900) * env_adsr(n, .0005, .008)
    return x


def pad(dur, freqs, fc=700, detune=.004):
    n = int(dur * SR); t = np.arange(n) / SR; x = np.zeros(n)
    for f in freqs:
        for d in (-detune, 0, detune):
            ph = (f * (1 + d) * t + rng.random()) % 1.0
            x += (2 * ph - 1)                 # saw
    x = lp(lp(x, fc), fc)
    return x / (len(freqs) * 3)


def riser(dur, f_from=300, f_to=4000):
    n = int(dur * SR); t = np.arange(n) / SR; u = t / dur
    noise = rng.standard_normal(n); out = np.zeros(n); blk = 1024
    for i in range(0, n, blk):                # sweeping band-pass, block-wise
        fc = f_from * (f_to / f_from) ** (i / n)
        seg = noise[max(0, i - 2048): i + blk]
        y = bp(seg, fc * .8, min(fc * 1.25, SR / 2 - 100))
        out[i:i + blk] = y[-len(out[i:i + blk]):]
    sweep = np.sin(2 * np.pi * np.cumsum(80 + 160 * u ** 2) / SR) * .25
    return (out + sweep) * u ** 2.2


def build(total, logo_t, intro_scale, vo_plan, pulse_from, wordmark_t=None):
    buf = np.zeros((int(total * SR), 2))
    beat = 60 / 64.0
    # sub drone (E1 + A1), slow breathing
    n = buf.shape[0]; t = np.arange(n) / SR
    sub = (np.sin(2 * np.pi * 41.2 * t) * .6 + np.sin(2 * np.pi * 55 * t) * .4) * (0.75 + .25 * np.sin(2 * np.pi * t / 7.5))
    sub *= np.clip((t - .3) / 3.5, 0, 1) * np.clip((total - t) / 2.5, 0, 1)
    add(buf, sub, 0, .22)
    # dark pad, A minor -> F -> A minor; swells
    chords = [[110, 164.8, 261.6], [87.3, 130.8, 220], [110, 164.8, 246.9]]
    seg = (total - 1) / 3
    for k, ch in enumerate(chords):
        p = pad(seg + 2, ch, fc=520 + 120 * k)
        e = np.clip(np.arange(len(p)) / SR / 1.6, 0, 1) * np.clip((len(p) / SR - np.arange(len(p)) / SR) / 1.6, 0, 1)
        add(buf, p * e, 1 + k * seg - .5, .09, pan=(-.3, .3, 0)[k])
    # pulse on every beat from pulse_from until the logo; offbeat ghost
    tb = pulse_from
    while tb < logo_t - .2:
        add(buf, thump(), tb, .55)
        add(buf, thump(52, 38, .5), tb + beat / 2, .12)
        tb += beat
    # clock: tick-tock on the half beats, quiet, panned slightly
    tb, k = .25, 0
    while tb < logo_t - .1:
        add(buf, tick(3400 if k % 2 == 0 else 2600), tb, .05, pan=-.25 if k % 2 == 0 else .25)
        tb += beat / 2; k += 1
    # typing ticks on "LONDON · 03:00" (14 chars, 1.9-3.1 s in card time)
    for i in range(14):
        add(buf, key_click(), (1.9 + i * 1.2 / 14) / intro_scale, .22, pan=rng.uniform(-.2, .2))
    # the line drawing across: soft air swell
    n2 = int(2.0 / intro_scale * SR)
    air = bp(rng.standard_normal(n2), 400, 2500) * np.sin(np.linspace(0, np.pi, n2)) ** 2
    add(buf, air, .5 / intro_scale, .05)
    # small riser into the wordmark, big (still quiet) riser into the logo
    if wordmark_t:
        add(buf, riser(1.8, 200, 1800), wordmark_t - 1.8, .06)
        add(buf, thump(70, 36, 1.6), wordmark_t + .05, .35)
    add(buf, riser(3.4), logo_t - 3.4, .14)
    # impact on the lockup: sub boom + soft bell (E5/B5) with long tail
    add(buf, thump(80, 30, 3.0), logo_t, .9)
    nb = int(5 * SR); tt = np.arange(nb) / SR
    bell = (np.sin(2 * np.pi * 659.3 * tt) + .5 * np.sin(2 * np.pi * 987.8 * tt) + .2 * np.sin(2 * np.pi * 1318.5 * tt)) * env_adsr(nb, .005, 1.6)
    add(buf, bell, logo_t + .02, .06, pan=-.1)
    # simple stereo room: short decorrelated delays
    for d, g in ((.031, .18), (.047, .14), (.089, .1)):
        k = int(d * SR); buf[k:, 0] += buf[:-k, 1] * g; buf[k:, 1] += buf[:-k, 0] * g * .9
    music = buf
    # VO track
    vo = np.zeros(n)
    for f, t0 in vo_plan:
        sr, x = wavfile.read(os.path.join(HERE, 'vo', f))
        x = x.astype(np.float64) / 32768.0
        x = signal.resample_poly(x, 320, 147)                   # 22050 -> 48000
        x = signal.lfilter(*signal.butter(2, 70 / (SR / 2), 'high'), x)
        x = x / np.max(np.abs(x)) * .5
        i = int(t0 * SR); vo[i:i + len(x)] += x[: n - i]
    # duck music under VO (smoothed envelope, about -7 dB)
    act = np.abs(vo) > .01
    w = int(.25 * SR); envv = np.convolve(act.astype(float), np.ones(w) / w, 'same'); envv = np.clip(envv * 4, 0, 1)
    envv = signal.lfilter([.002], [1, -.998], envv)
    gain = 1 - .55 * np.clip(envv, 0, 1)
    music = music * gain[:, None]
    mix = music * .55 + np.stack([vo, vo], 1)
    mix *= np.clip((total - t) / .4, 0, 1)[:, None]             # clean end
    mix /= max(1e-9, np.max(np.abs(mix))) / .89
    return mix


if __name__ == '__main__':
    fmt = sys.argv[1]
    if fmt == '16x9':
        plan = [('v01.wav', 4.8), ('v02.wav', 10.0), ('v03.wav', 16.8), ('v04.wav', 22.8), ('v05.wav', 28.8), ('v06.wav', 36.8), ('v07.wav', 46.6), ('v08.wav', 53.0)]
        mix = build(60.0, 52.0, 1.0, plan, pulse_from=4.0, wordmark_t=4.0)
    else:
        plan = [('v01.wav', .5), ('v02.wav', 3.0), ('v05.wav', 8.4), ('v06.wav', 15.4), ('v08.wav', 23.6)]
        mix = build(30.0, 23.0, 1.45, plan, pulse_from=2.5, wordmark_t=None)
    out = os.path.join(HERE, 'work', f'mix_{fmt}.wav')
    wavfile.write(out, SR, (mix * 32767).astype(np.int16))
    print('wrote', out)
