# Quick preview of the finished parts so far (1080x1920), with the matching slices of the score.
import sys, os, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comp
from PIL import Image
R = comp.R
def have(shot, f): return os.path.exists(os.path.join(R, shot, 'f%04d.png' % f))
segs = []
for shot, (a, b) in comp.SHOTS.items():
    n = a
    while n <= b and have(shot, n - (n - a) % 2) and (have(shot, min(n + 1, b)) or (n - a) % 2 == 0): n += 1
    if n - a > 10: segs.append((a, n - 1 - ((n - 1 - a) % 2)))
print(segs)
out = sys.argv[1]; tmp = out + '.v.mp4'
p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '1080x1920', '-r', '30', '-i', '-', '-c:v', 'libx264', '-crf', '19', '-pix_fmt', 'yuv420p', tmp], stdin=subprocess.PIPE)
af = []
for a, b in segs:
    for f in range(a, b + 1): p.stdin.write(comp.frame(f).resize((1080, 1920), Image.LANCZOS).tobytes())
    af.append('atrim=%f:%f,asetpts=PTS-STARTPTS' % (a / 30, (b + 1) / 30))
p.stdin.close(); p.wait()
fc = ';'.join('[1:a]%s[a%d]' % (x, i) for i, x in enumerate(af)) + ';' + ''.join('[a%d]' % i for i in range(len(af))) + 'concat=n=%d:v=0:a=1,loudnorm=I=-14[a]' % len(af)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp, '-i', os.path.join(comp.ROOT, 'audio', 'score_foley.wav'), '-filter_complex', fc, '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out], check=True)
os.remove(tmp); print('ok', out)
