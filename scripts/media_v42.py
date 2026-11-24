#!/usr/bin/env python3
"""Convert Blender renders into web media. Never upscales: output sizes are at or below the render size."""
import pathlib, subprocess, shutil
from PIL import Image
R = pathlib.Path('/home/user/nsko-solutions/render/out'); P = pathlib.Path('/home/user/nsko-solutions/public/media/v42')
for d in ('hero', 'poster', 'loop', 'glb'): (P / d).mkdir(parents=True, exist_ok=True)
def webp(src, dst, size=None, q=80):
    if dst.exists() and dst.stat().st_mtime > src.stat().st_mtime: return
    im = Image.open(src).convert('RGB')
    if size and size < im.width: im = im.resize((size, round(im.height * size / im.width)), Image.LANCZOS)
    im.save(dst, 'WEBP', quality=q, method=6)
for f in sorted((R / 'hero-n').glob('f*.png')): webp(f, P / 'hero' / (f.stem + '.webp'), q=78)
SRC = {'surgical': R / 'scn/surgical.png', 'robot': R / 'scn/robot.png', 'n1': R / 'scn/chip.png', 'quad': R / 'scn/quad.png', 'arch': R / 'scn/arch.png',
       'wire': R / 'scn/wire.png', 'pendant': R / 'scn/iced.png', 'watch': R / 'lux/watch.png', 'goldpendant': R / 'lux/pendant.png', 'key': R / 'poster-key/f000.png'}
for o, src in SRC.items():
    if not src.exists(): src = pathlib.Path(str(src).replace('.png', '-t.png'))
    if not src.exists(): continue
    im = Image.open(src); w, h = im.size
    if h > w:  # portrait render: centre square crop for posters, keep the full frame as -tall
        top = (h - w) // 2; sq = R / 'tmp_sq.png'; im.crop((0, top, w, top + w)).save(sq); webp(src, P / 'poster' / f'{o}-tall.webp', None, 84); src2 = sq
    else: src2 = src
    for s_ in (900, 600): (P / 'poster' / f'{o}-{s_}.webp').unlink(missing_ok=True); webp(src2, P / 'poster' / f'{o}-{s_}.webp', s_, 84)
    (P / 'poster' / f'{o}-1600.webp').unlink(missing_ok=True); webp(src2, P / 'poster' / f'{o}-1600.webp', None, 86)
for o in 'arm chip blade key'.split():
    d = R / f'loop-{o}'
    if (d / 'f094.png').exists() and not (P / 'loop' / f'{o}.mp4').exists():
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', '6', '-pattern_type', 'glob', '-i', str(d / 'f*.png'), '-vf', 'minterpolate=fps=24:mi_mode=mci:mc_mode=aobmc:vsbmc=1,format=yuv420p',
                        '-c:v', 'libx264', '-preset', 'slow', '-crf', '26', '-movflags', '+faststart', '-an', str(P / 'loop' / f'{o}.mp4')], check=True)
for g in (R / 'glb').glob('*.glb'): shutil.copy(g, P / 'glb' / g.name)
print(subprocess.run(['du', '-sh', *map(str, P.iterdir())], capture_output=True, text=True).stdout)
