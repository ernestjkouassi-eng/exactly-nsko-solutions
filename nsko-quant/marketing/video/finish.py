#!/usr/bin/env python3
"""NSKO QUANT ad: captions (optional burn-in), grade (vignette + fine grain), loudness (two-pass loudnorm), final encodes.
usage: python3 finish.py 16x9|9x16
"""
import subprocess, sys, os, json, re
import numpy as np, cv2

HERE = os.path.dirname(os.path.abspath(__file__))
WORK, OUT, CAPS = (os.path.join(HERE, d) for d in ('work', 'out', os.path.join('cards', 'caps')))
os.makedirs(OUT, exist_ok=True)
FPS = 30

TEXT = ['The markets never sleep.', 'Neither does your desk.', 'A private research team, reading the world, twenty-four hours a day.',
        'The kind of data hedge funds pay millions for.', 'Every idea tested. Most rejected. Only the best survive.',
        'When the odds are right, it trades. Automatically.', 'With your risk rules, every time.',
        'Your account. Your broker. Your money never leaves your hands.', 'NSKO QUANT. Trade the markets. Automatically.']
# (caption index, start, end) relative to VO start; durations from the recorded lines
REL = {1: (.1, 1.55), 2: (.1, 1.55), 3: (.2, 3.4), 4: (.2, 2.8), 5: (.15, 5.4), 6: (.2, 3.9), 7: (4.3, 6.05), 8: (.2, 4.6), 9: (.2, 4.6)}
VO = {'16x9': {1: 4.8, 2: 10.0, 3: 16.8, 4: 22.8, 5: 28.8, 6: 36.8, 7: 36.8, 8: 46.6, 9: 53.0},
      '9x16': {1: .5, 2: 3.0, 5: 8.4, 6: 15.4, 7: 15.4, 9: 23.6}}


def cues(fmt):
    return [(i, VO[fmt][i] + REL[i][0], VO[fmt][i] + REL[i][1]) for i in sorted(VO[fmt])]


def srt(fmt, path):
    def ts(x):
        ms = int(round(x * 1000)); return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'
    with open(path, 'w') as f:
        for n, (i, a, b) in enumerate(cues(fmt), 1):
            f.write(f'{n}\n{ts(a)} --> {ts(b)}\n{TEXT[i - 1]}\n\n')


def burn_captions(src, dst, fmt, W, H):
    cs = [(cv2.imread(os.path.join(CAPS, f"{'h' if fmt == '16x9' else 'v'}{i}.png"), cv2.IMREAD_UNCHANGED), a, b) for i, a, b in cues(fmt)]
    ytop = 800 if fmt == '16x9' else 1420
    dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', src, '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'], stdout=subprocess.PIPE)
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '12', '-pix_fmt', 'yuv420p', dst], stdin=subprocess.PIPE)
    i = 0
    while True:
        buf = dec.stdout.read(W * H * 3)
        if len(buf) < W * H * 3:
            break
        fr = np.frombuffer(buf, np.uint8).reshape(H, W, 3).copy(); t = i / FPS
        for im, a, b in cs:
            al = min(1, (t - a) / .2, (b - t) / .25)
            if al > 0:
                h, w = im.shape[:2]; x = (W - w) // 2
                o = im.astype(np.float32); m = o[..., 3:4] / 255 * al
                fr[ytop:ytop + h, x:x + w] = (fr[ytop:ytop + h, x:x + w] * (1 - m) + o[..., :3] * m).astype(np.uint8)
        enc.stdin.write(fr.tobytes()); i += 1
    enc.stdin.close(); enc.wait(); dec.wait()


def loudnorm_two_pass(wav, out_wav):
    p = subprocess.run(['ffmpeg', '-hide_banner', '-i', wav, '-af', 'loudnorm=I=-14:TP=-1.0:LRA=11:print_format=json', '-f', 'null', '-'], capture_output=True, text=True)
    m = json.loads(re.search(r'\{[^{}]*"input_i"[^{}]*\}', p.stderr, re.S).group(0))
    af = (f"loudnorm=I=-14:TP=-1.0:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
          f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true:print_format=summary,alimiter=limit=0.79:attack=3:release=60:level=false")
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', wav, '-af', af + ',aresample=48000', '-ar', '48000', out_wav], check=True)
    print('loudnorm pass1', {k: m[k] for k in ('input_i', 'input_tp', 'input_lra')})


GRADE = 'vignette=angle=PI/7:mode=forward,noise=c0s=5:c0f=t+u,format=yuv420p'


def encode(video, audio, out, crf=18):
    args = ['ffmpeg', '-v', 'error', '-y', '-i', video]
    if audio:
        args += ['-i', audio]
    args += ['-vf', GRADE, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', str(crf), '-pix_fmt', 'yuv420p', '-r', str(FPS), '-movflags', '+faststart']
    args += ['-map', '0:v:0'] + (['-map', '1:a:0', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-shortest'] if audio else ['-an'])
    subprocess.run(args + [out], check=True); print('wrote', out)


if __name__ == '__main__':
    fmt = sys.argv[1]
    asm = os.path.join(WORK, f'assembled_{fmt}.mp4')
    norm = os.path.join(WORK, f'mix_{fmt}_norm.wav')
    loudnorm_two_pass(os.path.join(WORK, f'mix_{fmt}.wav'), norm)
    if fmt == '16x9':
        srt('16x9', os.path.join(OUT, 'nsko-quant-ad.srt'))
        encode(asm, norm, os.path.join(OUT, 'nsko-quant-ad-16x9.mp4'))
        capd = os.path.join(WORK, 'assembled_16x9_caps.mp4'); burn_captions(asm, capd, '16x9', 1920, 1080)
        encode(capd, None, os.path.join(OUT, 'nsko-quant-ad-16x9-silent.mp4'))
    else:
        srt('9x16', os.path.join(WORK, 'nsko-quant-ad-9x16.srt'))
        capd = os.path.join(WORK, 'assembled_9x16_caps.mp4'); burn_captions(asm, capd, '9x16', 1080, 1920)
        encode(capd, norm, os.path.join(OUT, 'nsko-quant-ad-9x16.mp4'))
