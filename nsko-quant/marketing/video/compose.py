#!/usr/bin/env python3
"""NSKO QUANT ad: scene compositor.

Each scene is built frame by frame with sub-pixel camera moves (cv2.warpAffine with eased keyframes),
then overlays (DEMO DATA label, scene kicker, notification) are alpha-blended. Scenes are joined with
ffmpeg xfade dissolves. Grain, vignette, captions and audio are added in finish.py.

usage: python3 compose.py 16x9|9x16
"""
import subprocess, sys, os, json
import numpy as np, cv2

HERE = os.path.dirname(os.path.abspath(__file__))
REC, CARDS, STILLS, WORK = (os.path.join(HERE, d) for d in ('rec', 'cards', 'stills', 'work'))
os.makedirs(WORK, exist_ok=True)
FPS = 30
BG = (15, 8, 8)  # #08080F in BGR


def ease(x):
    x = min(1.0, max(0.0, x))
    return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2


def interp(kf, t):
    """kf: [(t, cx, cy, vw), ...] -> eased per-segment interpolation."""
    if t <= kf[0][0]:
        return kf[0][1:]
    for a, b in zip(kf, kf[1:]):
        if t <= b[0]:
            u = ease((t - a[0]) / (b[0] - a[0]))
            return tuple(a[i] + (b[i] - a[i]) * u for i in (1, 2, 3))
    return kf[-1][1:]


class VideoSrc:
    """Sequential reader that serves the frame nearest to a (monotonic) source time."""
    def __init__(self, path, w=1920, h=1080):
        self.w, self.h = w, h
        self.p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', path, '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'], stdout=subprocess.PIPE)
        self.idx, self.cur = -1, None

    def at(self, ts):
        want = max(0, int(round(ts * FPS)))
        while self.idx < want:
            buf = self.p.stdout.read(self.w * self.h * 3)
            if len(buf) < self.w * self.h * 3:
                break
            self.cur = np.frombuffer(buf, np.uint8).reshape(self.h, self.w, 3); self.idx += 1
        return self.cur

    def close(self):
        self.p.stdout.close(); self.p.kill()


class StillSrc:
    def __init__(self, path, scale=1.0):
        im = cv2.imread(path, cv2.IMREAD_COLOR)
        self.im = im; self.scale = scale  # scale: source pixels per 1080p "app" pixel

    def at(self, ts):
        return self.im


def load_rgba(path):
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    return im


def blend(dst, ov, x, y, alpha=1.0):
    """alpha-blend BGRA overlay onto BGR dst at float position (x, y) (rounded) with global alpha."""
    if alpha <= 0.002:
        return
    h, w = ov.shape[:2]; x, y = int(round(x)), int(round(y))
    x0, y0, x1, y1 = max(0, x), max(0, y), min(dst.shape[1], x + w), min(dst.shape[0], y + h)
    if x1 <= x0 or y1 <= y0:
        return
    o = ov[y0 - y:y1 - y, x0 - x:x1 - x].astype(np.float32)
    a = o[..., 3:4] / 255.0 * alpha
    d = dst[y0:y1, x0:x1].astype(np.float32)
    dst[y0:y1, x0:x1] = (d * (1 - a) + o[..., :3] * a).astype(np.uint8)


def render_layer(frame, src_img, unit, cx, cy, vw, dst):
    """Map a view (centre cx,cy, width vw in 1080p app units) of src_img into dst rect (x,y,w,h) of frame."""
    x, y, w, h = dst
    vh = vw * h / w
    sw, sh = src_img.shape[1] / unit, src_img.shape[0] / unit       # source size in app units
    vw = min(vw, sw); vh = vw * h / w
    if vh > sh:
        vh = sh; vw = vh * w / h
    cx = min(max(cx, vw / 2), sw - vw / 2); cy = min(max(cy, vh / 2), sh - vh / 2)
    s = w / (vw * unit)                     # output px per source px
    sx0, sy0 = (cx - vw / 2) * unit, (cy - vh / 2) * unit
    M = np.float32([[s, 0, -sx0 * s], [0, s, -sy0 * s]])
    interp_flag = cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC
    if s < 0.75:   # pre-shrink large stills for clean downsampling
        f = s * 1.25
        small = cv2.resize(src_img, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
        M = np.float32([[s / f, 0, -sx0 * s], [0, s / f, -sy0 * s]]); src_img = small
        interp_flag = cv2.INTER_CUBIC
    out = cv2.warpAffine(src_img, M, (w, h), flags=interp_flag if interp_flag != cv2.INTER_AREA else cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=BG)
    frame[y:y + h, x:x + w] = out


def fade_env(t, dur, a_in, a_out_from_end, fin=.6, fout=.5):
    return min(ease((t - a_in) / fin), ease((dur - a_out_from_end - t) / fout))


def build_scene(name, W, H, dur, layers, overlays, src_t0=0.0, speed=1.0, src_max=1e9):
    """layers: [dict(src=..., unit=1, kf=[...], dst=(x,y,w,h))]. overlays: [dict(img, x, y, t_in, t_out, dy)]"""
    out = os.path.join(WORK, f'{name}.mp4')
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '12', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
    srcs = {}
    for L in layers:
        k = L['src']
        if k not in srcs:
            srcs[k] = StillSrc(k) if k.endswith('.png') else VideoSrc(k)
    N = int(round(dur * FPS))
    for i in range(N):
        t = i / FPS
        frame = np.empty((H, W, 3), np.uint8); frame[:] = BG
        for L in layers:
            img = srcs[L['src']].at(min(src_max, src_t0 + t * speed))
            cx, cy, vw = interp(L['kf'], t)
            render_layer(frame, img, L.get('unit', 1.0), cx, cy, vw, L['dst'])
        for O in overlays:
            a = min(ease((t - O['t_in']) / O.get('fin', .6)), ease((O.get('t_out', dur + 9) - t) / O.get('fout', .5)))
            dy = O.get('dy', 0) * (1 - ease((t - O['t_in']) / O.get('fin', .6)))
            blend(frame, O['img'], O['x'], O['y'] + dy, a)
        enc.stdin.write(frame.tobytes())
    enc.stdin.close(); enc.wait()
    for s in srcs.values():
        if isinstance(s, VideoSrc):
            s.close()
    print('scene', name, dur, 's')
    return out


def card_clip(name, path, dur):
    out = os.path.join(WORK, f'{name}.mp4')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', path, '-t', str(dur), '-vf', f'tpad=stop_mode=clone:stop_duration={dur},fps={FPS}', '-t', str(dur),
                    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '12', '-pix_fmt', 'yuv420p', out], check=True)
    return out


def join(clips, starts, total, out, D=.5):
    """clips[i] has length (start[i+1]-start[i]) + D; xfade at each start."""
    args = ['ffmpeg', '-v', 'error', '-y']
    for c in clips:
        args += ['-i', c]
    fc, prev = [], '[0:v]'
    for k in range(1, len(clips)):
        lab = f'[x{k}]'
        fc.append(f'{prev}[{k}:v]xfade=transition=fade:duration={D}:offset={starts[k]:.3f}{lab}')
        prev = lab
    args += ['-filter_complex', ';'.join(fc), '-map', prev, '-t', str(total), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '12', '-pix_fmt', 'yuv420p', out]
    subprocess.run(args, check=True)
    print('joined', out)


def P(*a):
    return os.path.join(*a)


def ad_16x9():
    W, H, D = 1920, 1080, .5
    demo = load_rgba(P(CARDS, 'demo.png'))
    k = [load_rgba(P(CARDS, f'kick{i}.png')) for i in range(1, 8)]
    notif = load_rgba(P(CARDS, 'notif.png'))
    dm = lambda dur: dict(img=demo, x=W - 200 - 26, y=H - 50 - 26, t_in=0, fin=.01, t_out=dur + 9)
    kick = lambda i, dur: dict(img=k[i], x=44, y=H - 90 - 48, t_in=.5, fin=.8, t_out=dur - .4, fout=.5)
    full = (0, 0, W, H)
    starts = [0, 4, 9, 16, 19, 22, 28, 36, 46, 52]
    total = 60.0
    lens = [starts[i + 1] - starts[i] + D for i in range(len(starts) - 1)] + [total - starts[-1]]
    S = []
    S.append(card_clip('h01_intro', P(CARDS, 'intro.mp4'), lens[0]))
    S.append(card_clip('h02_wordmark', P(CARDS, 'wordmark.mp4'), lens[1]))
    d = lens[2]; S.append(build_scene('h03_overview', W, H, d, [dict(src=P(REC, 'overview.mp4'), kf=[(0, 960, 540, 1920), (d, 1045, 445, 1240)], dst=full)], [dm(d), kick(0, d)], src_t0=1.0))
    d = lens[3]; S.append(build_scene('h04_research', W, H, d, [dict(src=P(REC, 'research.mp4'), kf=[(0, 860, 470, 1600), (d, 754, 480, 1180)], dst=full)], [dm(d), kick(1, d)], src_t0=.5))
    d = lens[4]; S.append(build_scene('h05_agents', W, H, d, [dict(src=P(REC, 'agents.mp4'), kf=[(0, 1044, 560, 1500), (d, 1044, 575, 1180)], dst=full)], [dm(d), kick(2, d)], src_t0=.5))
    d = lens[5]; S.append(build_scene('h06_godseye', W, H, d, [dict(src=P(STILLS, 'godseye@2x.png'), unit=2.0, kf=[(0, 1045, 570, 1560), (d, 1362, 455, 1110)], dst=full)], [dm(d), kick(3, d)]))
    d = lens[6]; S.append(build_scene('h07_lab', W, H, d, [dict(src=P(REC, 'lab.mp4'), kf=[(0, 960, 540, 1920), (4, 1044, 615, 1560), (d, 1250, 628, 1240)], dst=full)], [dm(d), kick(4, d)], src_t0=2.0))
    d = lens[7]; S.append(build_scene('h08_tradecard', W, H, d, [dict(src=P(REC, 'tradecard.mp4'), kf=[(0, 1044, 520, 1820), (5, 1080, 540, 1700), (d, 1170, 600, 1500)], dst=full)], [dm(d), kick(5, d)], src_t0=0.45, src_max=10.95))
    d = lens[8]; S.append(build_scene('h09_desk', W, H, d, [dict(src=P(REC, 'desk.mp4'), kf=[(0, 960, 540, 1920), (d, 1130, 440, 1520)], dst=full)],
                                      [dm(d), kick(6, d), dict(img=notif, x=W - 640 - 40, y=560, t_in=1.4, fin=.9, dy=40)], src_t0=2.0))
    S.append(card_clip('h10_end', P(CARDS, 'end.mp4'), lens[9]))
    join(S, starts, total, P(WORK, 'assembled_16x9.mp4'), D)


def ad_9x16():
    W, H, D = 1080, 1920, .5
    demo = load_rgba(P(CARDS, 'demo_v.png'))
    k = [load_rgba(P(CARDS, f'kickv{i}.png')) for i in range(1, 8)]
    dm = lambda dur: dict(img=demo, x=W - 240 - 40, y=150, t_in=0, fin=.01, t_out=dur + 9)
    kick = lambda i, dur: dict(img=k[i], x=48, y=136, t_in=.4, fin=.7, t_out=dur - .4)
    full = (0, 0, W, H)
    starts = [0, 2.5, 8, 15, 23]
    total = 30.0
    lens = [starts[i + 1] - starts[i] + D for i in range(len(starts) - 1)] + [total - starts[-1]]
    S = []
    S.append(card_clip('v01_intro', P(CARDS, 'intro_v.mp4'), lens[0]))
    d = lens[1]; S.append(build_scene('v02_overview', W, H, d, [dict(src=P(REC, 'overview.mp4'), kf=[(0, 1045, 540, 640), (d, 1045, 470, 500)], dst=full)], [dm(d), kick(0, d)], src_t0=1.0))
    d = lens[2]; S.append(build_scene('v03_lab', W, H, d, [dict(src=P(REC, 'lab.mp4'), kf=[(0, 560, 615, 700), (d, 1520, 615, 700)], dst=full)], [dm(d), kick(4, d)], src_t0=2.0))
    # trade card, reframed for 9:16: the step bar plus three stacked panels (Time Machine -> Order ticket -> Exit),
    # from the Time Machine step to the P&L, slowed a little so the numbers can be read
    d = lens[3]
    panels = [(188, 160, 790, 30), (763, 393, 562, 235), (763, 642, 562, 170), (1337, 642, 563, 170)]
    widths = [1000, 1000, 1000, 1000]
    gap = 26
    hs = [int(round(p[3] * w / p[2])) for p, w in zip(panels, widths)]
    y = 300
    layers = []
    for p, h, w in zip(panels, hs, widths):
        cx, cy = p[0] + p[2] / 2, p[1] + p[3] / 2
        layers.append(dict(src=P(REC, 'tradecard.mp4'), kf=[(0, cx, cy, p[2] + 4), (d, cx, cy, p[2] - 12)], dst=((W - w) // 2, y, w, h)))
        y += h + gap
    S.append(build_scene('v04_tradecard', W, H, d, layers, [dm(d), kick(5, d)], src_t0=4.4, speed=(10.95 - 4.4) / (d - .9), src_max=10.95))
    S.append(card_clip('v05_end', P(CARDS, 'end_v.mp4'), lens[4]))
    join(S, starts, total, P(WORK, 'assembled_9x16.mp4'), D)


if __name__ == '__main__':
    {'16x9': ad_16x9, '9x16': ad_9x16}[sys.argv[1]]()
