# Final comp: rendered frames -> 1620x2880 30 fps with callouts (thin lines, 4 px dot, uppercase letterspaced labels), fine grain,
# then the 1080x1920 cut. Every second frame is rendered; the frame between is the average of its two neighbours (slow moves only).
import os, json, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); R = os.path.join(ROOT, 'render')
sys.path.insert(0, os.path.join(ROOT, 'blender'))
SHOTS = {'title_open': (0, 89), 'cuban': (90, 329), 'neck': (330, 479), 'ring': (480, 629), 'watch': (630, 794),
         'hero_cuban': (795, 854), 'hero_neck': (855, 869), 'hero_ring': (870, 884), 'hero_watch': (885, 899), 'title_end': (900, 959)}
W, H = 1620, 2880
FONT = ImageFont.truetype('/home/user/nsko-solutions/node_modules/geist/dist/fonts/geist-sans/Geist-Regular.ttf', 27)
rng = np.random.default_rng(11)

def shot_of(f):
    for k, (a, b) in SHOTS.items():
        if a <= f <= b: return k, a, b

_cache = {}
def load(shot, f):
    fn = os.path.join(R, shot, 'f%04d.png' % f)
    if fn not in _cache:
        if len(_cache) > 6: _cache.clear()
        _cache[fn] = np.asarray(Image.open(fn).convert('RGB').resize((W, H), Image.LANCZOS), dtype=np.float32) if os.path.exists(fn) else None
    return _cache[fn]

anchors = {k: (json.load(open(os.path.join(R, k, 'anchors.json'))) if os.path.exists(os.path.join(R, k, 'anchors.json')) else {}) for k in SHOTS}

def frame(f):
    shot, a, b = shot_of(f)
    if (f - a) % 2 == 0 or f == b: img = load(shot, f); an = anchors[shot].get(str(f), {})
    else:
        p, q = load(shot, f - 1), load(shot, min(f + 1, b))
        img = p if q is None else (q if p is None else (p + q) / 2)
        A1, A2 = anchors[shot].get(str(f - 1), {}), anchors[shot].get(str(min(f + 1, b)), {})
        an = {k: [(A1[k][i] + A2.get(k, A1[k])[i]) / 2 for i in range(3)] for k in A1}
    if img is None: img = np.zeros((H, W, 3), np.float32)
    img = img + rng.normal(0, 2.2, (H // 2, W // 2, 1)).repeat(2, 0).repeat(2, 1)          # fine film grain (luma)
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    return callouts(im, an)

def spaced_w(t): return sum(FONT.getlength(c) for c in t) + 0.22 * 27 * (len(t) - 1)

def callouts(im, an):
    if not an: return im
    lay = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    items = sorted(an.items(), key=lambda kv: kv[1][1])[:4]                      # max 4 on screen
    used = []
    for label, (x, y, al) in items:
        X, Y = x * W, y * H
        if not (0 < X < W and 0 < Y < H): continue
        a = int(255 * max(0, min(1, al)))
        right = X < W / 2; tw = spaced_w(label)
        lx = W - 110 - tw if right else 110                                         # labels sit in the side margins, never on a stone
        ly = Y - 150 if Y > 400 else Y + 150
        while any(abs(ly - u) < 70 for u in used): ly += 72
        used.append(ly)
        ex = lx - 24 if right else lx + tw + 24
        col = (242, 246, 250, a)
        d.ellipse((X - 4, Y - 4, X + 4, Y + 4), fill=col)
        d.line([(X, Y), (ex, ly + 16)], fill=col, width=1)
        d.line([(ex, ly + 16), (ex + (14 if right else -14), ly + 16)], fill=col, width=1)
        cx = lx
        for c in label:
            d.text((cx, ly), c, font=FONT, fill=col); cx += FONT.getlength(c) + .22 * 27
    return Image.alpha_composite(im.convert('RGBA'), lay).convert('RGB')

if __name__ == '__main__':
    out3k = os.path.join(ROOT, 'NSKO_Diamond_Collection_3K_9x16.mp4'); out1k = os.path.join(ROOT, 'NSKO_Diamond_Collection_1080_9x16.mp4')
    aud = os.path.join(ROOT, 'audio', 'score_foley.wav')
    if len(sys.argv) > 1 and sys.argv[1] == 'still':          # python3 comp.py still <frame> <out.png>
        frame(int(sys.argv[2])).save(sys.argv[3]); sys.exit()
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H), '-r', '30', '-i', '-', '-i', aud,
                          '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p',
                          '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-c:a', 'aac', '-b:a', '256k', '-shortest', '-movflags', '+faststart', out3k],
                         stdin=subprocess.PIPE)
    for f in range(960):
        p.stdin.write(frame(f).tobytes())
        if f % 60 == 0: print('comp', f, flush=True)
    p.stdin.close(); p.wait()
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', out3k, '-vf', 'scale=1080:1920:flags=lanczos', '-c:v', 'libx264', '-preset', 'slow', '-crf', '18',
                    '-pix_fmt', 'yuv420p', '-c:a', 'copy', '-movflags', '+faststart', out1k], check=True)
    print('done', out3k, out1k)
