"""Generates the chart-style inline SVGs for how-it-works.html (ILLUSTRATIVE drawings, not data).
Usage: python3 gen_svgs.py  -> replaces <!--SVG:name--> ... <!--/SVG:name--> blocks in how-it-works.html
"""
import math
import random
import re
from pathlib import Path

O, INK, MID, LO, G, R, GRID = "#E8541A", "#0B0B12", "#4A4D57", "#80838E", "#1E8E4E", "#C8322B", "#ECECF0"


def candles(bars, x0, w, ymap, gap=0.28):
    out = []
    for i, (o, h, l, c) in enumerate(bars):
        x = x0 + i * w
        col = G if c >= o else R
        out.append(f'<line x1="{x + w / 2:.1f}" y1="{ymap(h):.1f}" x2="{x + w / 2:.1f}" y2="{ymap(l):.1f}" stroke="{col}" stroke-width="1.2"/>')
        top, bot = ymap(max(o, c)), ymap(min(o, c))
        out.append(f'<rect x="{x + w * gap / 2:.1f}" y="{top:.1f}" width="{w * (1 - gap):.1f}" height="{max(1.2, bot - top):.1f}" fill="{col}"/>')
    return "\n".join(out)


def label(x, y, t, col=MID, size=9, anchor="start", weight=400, mono=False):
    cls = ' class="mono"' if mono else ""
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{col}" text-anchor="{anchor}" font-weight="{weight}"{cls}>{t}</text>'


def of1_sweep():
    W, H = 680, 300
    lo_p, hi_p = 2632, 2656
    top, bot = 20, 270
    ym = lambda p: bot - (p - lo_p) / (hi_p - lo_p) * (bot - top)
    VAH, POC, VAL = 2651.0, 2647.5, 2641.0
    bars = [(2649.5, 2650.6, 2648.4, 2648.9), (2648.9, 2649.4, 2646.8, 2647.2), (2647.2, 2648.5, 2646.4, 2648.0),
            (2648.0, 2648.3, 2645.2, 2645.6), (2645.6, 2646.6, 2643.9, 2644.3), (2644.3, 2645.2, 2642.6, 2643.0),
            (2643.0, 2643.9, 2641.6, 2642.1), (2642.1, 2642.7, 2639.4, 2642.4),  # sweep + reclaim (signal bar)
            (2642.5, 2644.6, 2642.2, 2644.3), (2644.3, 2646.4, 2643.8, 2646.1), (2646.1, 2647.9, 2645.6, 2647.4),
            (2647.4, 2648.2, 2646.6, 2647.9)]
    w = 34
    x0 = 60
    s = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">',
         f'<rect x="0" y="0" width="{W}" height="{H}" fill="#fff"/>']
    for p in range(2634, 2657, 4):
        s.append(f'<line x1="50" y1="{ym(p):.1f}" x2="500" y2="{ym(p):.1f}" stroke="{GRID}"/>')
        s.append(label(46, ym(p) + 3, f"{p:,}", LO, 7.5, "end", mono=True))
    # value area band
    s.append(f'<rect x="50" y="{ym(VAH):.1f}" width="450" height="{ym(VAL) - ym(VAH):.1f}" fill="#FBF4F0"/>')
    for p, n, col in ((VAH, "VAH", MID), (POC, "POC", O), (VAL, "VAL", MID)):
        s.append(f'<line x1="50" y1="{ym(p):.1f}" x2="500" y2="{ym(p):.1f}" stroke="{col}" stroke-dasharray="5 3" stroke-width="1.1"/>')
        s.append(label(504, ym(p) + 3, n, col, 8.5, weight=700, mono=True))
    s.append(candles(bars, x0, w, ym))
    # profile on the right
    rng = random.Random(3)
    for p10 in range(26330, 26555, 5):
        p = p10 / 10
        d = math.exp(-((p - POC) / 3.2) ** 2) * 100 + rng.random() * 8
        if abs(p - 2644.3) < 0.8:
            d *= 0.35  # an LVN
        col = O if abs(p - POC) < 0.15 else ("#F2B79E" if VAL <= p <= VAH else "#D9D9E0")
        s.append(f'<rect x="560" y="{ym(p + 0.5):.1f}" width="{d:.1f}" height="{(ym(p) - ym(p + 0.5)) * 0.8:.1f}" fill="{col}"/>')
    s.append(label(560, 14, "PROFILE · prior session", LO, 7.5, mono=True))
    s.append(label(668, ym(2644.3) + 3, "LVN", LO, 7.5, "end", mono=True))
    # sweep annotation
    sx = x0 + 7 * w + w / 2
    s.append(f'<circle cx="{sx:.1f}" cy="{ym(2639.4):.1f}" r="11" fill="none" stroke="{O}" stroke-width="1.6"/>')
    s.append(f'<circle cx="{sx:.1f}" cy="{ym(2640.6):.1f}" r="9" fill="{G}" fill-opacity=".28" stroke="{G}"/>')
    s.append(label(sx - 18, ym(2636.4), "1 · sweep below VAL", O, 9, "end", 700))
    s.append(label(sx - 18, ym(2635.4) + 6, "2 · closes back inside value", O, 9, "end", 700))
    s.append(label(sx - 18, ym(2634.4) + 12, "   + aggressive buying (bubble)", G, 8.5, "end", 600))
    # entry / stop / target
    ex = x0 + 8 * w
    for p, n, col in ((2642.5, "ENTRY (next bar open)", INK), (2639.0, "STOP (beyond the swept low)", R), (POC, "TARGET (POC)", G)):
        s.append(f'<line x1="{ex:.1f}" y1="{ym(p):.1f}" x2="{x0 + 12 * w:.1f}" y2="{ym(p):.1f}" stroke="{col}" stroke-width="1.6"/>')
    s.append(label(x0 + 12 * w - 2, ym(2642.5) + 11, "ENTRY · next bar open", INK, 8, "end", 700, True))
    s.append(label(x0 + 12 * w - 2, ym(2639.0) + 11, "STOP · beyond swept low", R, 8, "end", 700, True))
    s.append(label(x0 + 12 * w - 2, ym(POC) - 5, "TARGET · POC", G, 8, "end", 700, True))
    s.append(label(54, 290, "ILLUSTRATIVE drawing. Not real prices.", LO, 8, mono=True))
    s.append("</svg>")
    return "\n".join(s)


def states():
    W, H = 680, 200
    s = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">']
    for k, (title, sub) in enumerate((("BALANCED", "rotates inside value: fade the edges, aim for the POC"),
                                      ("IMBALANCED", "3 bars accepted outside value: trade with it, not against it"))):
        X = 6 + k * 342
        s.append(f'<rect x="{X}" y="6" width="330" height="186" rx="6" fill="#fff" stroke="#D9D9E0"/>')
        s.append(label(X + 12, 24, title, O, 9, weight=700, mono=True))
        s.append(label(X + 12, 38, sub, MID, 8.6))
        vah, val = 80, 140
        s.append(f'<rect x="{X + 12}" y="{vah}" width="306" height="{val - vah}" fill="#FBF4F0"/>')
        s.append(f'<line x1="{X + 12}" y1="{vah}" x2="{X + 318}" y2="{vah}" stroke="{MID}" stroke-dasharray="4 3"/>')
        s.append(f'<line x1="{X + 12}" y1="{val}" x2="{X + 318}" y2="{val}" stroke="{MID}" stroke-dasharray="4 3"/>')
        s.append(f'<line x1="{X + 12}" y1="110" x2="{X + 318}" y2="110" stroke="{O}" stroke-dasharray="4 3"/>')
        s.append(label(X + 316, vah - 3, "VAH", MID, 7.5, "end", 700, True))
        s.append(label(X + 316, val + 10, "VAL", MID, 7.5, "end", 700, True))
        s.append(label(X + 316, 107, "POC", O, 7.5, "end", 700, True))
        rng = random.Random(7 + k)
        pts = []
        p = 110
        for i in range(40):
            if k == 0:
                p = 110 + 26 * math.sin(i / 4.2) + rng.uniform(-4, 4)
            else:
                p = (110 - i * 2.9 + rng.uniform(-4, 4)) if i < 22 else (46 + rng.uniform(-6, 6) - (i - 22) * 0.9)
            pts.append(f"{X + 18 + i * 7.4:.1f},{p:.1f}")
        s.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{INK}" stroke-width="1.6"/>')
        if k == 1:
            s.append(f'<rect x="{X + 178}" y="44" width="30" height="34" fill="none" stroke="{O}" stroke-width="1.4"/>')
            s.append(label(X + 212, 58, "accepted", O, 8, weight=700))
            s.append(label(X + 212, 69, "above VAH", O, 8, weight=700))
        s.append(label(X + 12, 182, "ILLUSTRATIVE", LO, 7.5, mono=True))
    s.append("</svg>")
    return "\n".join(s)


def fan(kind):
    """kind = 'kronos' (forecast fan) or 'tm' (Time Machine with target/stop)."""
    W, H = 680, 250
    rng = random.Random(11 if kind == "kronos" else 5)
    x0, x1 = 70, 600
    y_entry = 140
    s = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">']
    # history
    hist = []
    p = 170
    for i in range(30):
        p += rng.uniform(-6, 5)
        hist.append(f"{x0 - 60 + i * 2:.1f},{p:.1f}")
    p_last = y_entry
    s.append(f'<polyline points="10,170 {" ".join(hist[::3])} {x0},{p_last}" fill="none" stroke="{INK}" stroke-width="1.8"/>')
    n = 70
    tgt, stp = 82, 178
    hit_t = hit_s = 0
    paths = []
    for j in range(n):
        y = p_last
        pts = [f"{x0},{y:.1f}"]
        state = "open"
        drift = -0.35
        for i in range(1, 40):
            y += rng.gauss(drift, 5.2)
            pts.append(f"{x0 + i * (x1 - x0) / 39:.1f},{y:.1f}")
            if kind == "tm" and state == "open":
                if y >= stp:
                    state = "stop"; break
                if y <= tgt:
                    state = "target"; break
        paths.append((pts, state, y))
    for pts, state, y in paths:
        col = {"open": "#B8BAC2", "stop": R, "target": G}[state] if kind == "tm" else ("#F2B79E" if y < p_last else "#C9CBD3")
        s.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{col}" stroke-width="0.9" stroke-opacity=".75"/>')
    s.append(f'<circle cx="{x0}" cy="{p_last}" r="4" fill="{O}"/>')
    if kind == "tm":
        s.append(f'<line x1="{x0}" y1="{tgt}" x2="{x1 + 10}" y2="{tgt}" stroke="{G}" stroke-width="1.6"/>')
        s.append(f'<line x1="{x0}" y1="{stp}" x2="{x1 + 10}" y2="{stp}" stroke="{R}" stroke-width="1.6"/>')
        s.append(label(x1 + 14, tgt + 3, "TARGET", G, 8.5, weight=700, mono=True))
        s.append(label(x1 + 14, stp + 3, "STOP", R, 8.5, weight=700, mono=True))
        s.append(label(x1 + 14, 128, "SESSION", LO, 7.5, mono=True))
        s.append(label(x1 + 14, 138, "END", LO, 7.5, mono=True))
        s.append(f'<line x1="{x1}" y1="30" x2="{x1}" y2="215" stroke="{LO}" stroke-dasharray="3 3"/>')
        # odds bar
        bx, bw = 70, 540
        segs = ((0.41, G, "41% target first"), (0.33, R, "33% stop first"), (0.26, "#B8BAC2", "26% still open"))
        cx = bx
        for f, col, t in segs:
            s.append(f'<rect x="{cx:.1f}" y="226" width="{bw * f:.1f}" height="8" fill="{col}"/>')
            s.append(label(cx + 2, 246, t, col if col != "#B8BAC2" else MID, 8.5, weight=700, mono=True))
            cx += bw * f
        s.append(label(10, 20, "ILLUSTRATIVE · 70 of 10,000 replays drawn", LO, 8, mono=True))
    else:
        # percentile band labels
        s.append(label(x1 + 8, 70, "p90", LO, 8, mono=True))
        s.append(label(x1 + 8, 140, "p50", O, 8, weight=700, mono=True))
        s.append(label(x1 + 8, 215, "p10", LO, 8, mono=True))
        s.append(f'<line x1="{x0}" y1="{p_last}" x2="{x1}" y2="{p_last}" stroke="{INK}" stroke-dasharray="4 3"/>')
        s.append(label(x0 + 6, p_last - 6, "entry price", INK, 8, mono=True))
        s.append(label(x0 + 300, 236, "orange: path ends above entry (agrees with a BUY) · grey: ends below", MID, 8.5, "middle"))
        s.append(label(10, 20, "ILLUSTRATIVE · 70 of 1,000 paths drawn · horizon 16 bars", LO, 8, mono=True))
        s.append(label(10, 236, "NOW", O, 8, weight=700, mono=True))
    s.append("</svg>")
    return "\n".join(s)


def levels():
    W, H = 680, 230
    s = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">']
    rows = [("Prior session high", 30, INK, ""), ("VAH · top of value area", 60, MID, "4 3"), ("HTF fair value gap (bar closed)", 85, "#B7791F", ""),
            ("POC · most traded price", 110, O, "4 3"), ("LVN · thin, price moves fast", 135, LO, "2 3"), ("VAL · bottom of value area", 160, MID, "4 3"),
            ("Prior session low", 195, INK, "")]
    for t, y, col, dash in rows:
        if "gap" in t:
            s.append(f'<rect x="250" y="{y - 9}" width="300" height="18" fill="#FFF2DC" stroke="#E2C48E"/>')
        else:
            s.append(f'<line x1="250" y1="{y}" x2="550" y2="{y}" stroke="{col}" stroke-width="1.5" stroke-dasharray="{dash}"/>')
        s.append(label(240, y + 3, t, col, 9.2, "end", 600))
    s.append(f'<rect x="250" y="60" width="300" height="100" fill="{O}" fill-opacity=".06"/>')
    s.append(label(560, 108, "act only", O, 9, weight=700))
    s.append(label(560, 120, "AT a level", O, 9, weight=700))
    s.append(label(250, 222, "ILLUSTRATIVE level map. Levels come only from bars that have already closed.", LO, 8, mono=True))
    s.append("</svg>")
    return "\n".join(s)


SVGS = {"of1": of1_sweep, "states": states, "kronos": lambda: fan("kronos"), "tm": lambda: fan("tm"), "levels": levels}

if __name__ == "__main__":
    p = Path(__file__).with_name("how-it-works.html")
    html = p.read_text()
    for name, fn in SVGS.items():
        html = re.sub(rf"<!--SVG:{name}-->.*?<!--/SVG:{name}-->", lambda m: f"<!--SVG:{name}-->\n{fn()}\n<!--/SVG:{name}-->", html, flags=re.S)
    p.write_text(html)
    print("svgs injected")
