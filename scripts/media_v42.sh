#!/bin/bash
# Convert Blender renders into web media. Never upscale: sizes are at or below the render size.
set -e; R=/home/user/nsko-solutions/render/out; P=/home/user/nsko-solutions/public/media/v42; mkdir -p $P/hero $P/poster $P/loop $P/glb
if [ -d $R/hero-n ]; then for f in $R/hero-n/f*.png; do b=$(basename $f .png); [ -f $P/hero/$b.webp -a $P/hero/$b.webp -nt $f ] || cwebp -quiet -q 80 -m 6 $f -o $P/hero/$b.webp; done; fi
for o in drone arm chip blade key arch watch pendant; do src=$R/poster-$o/f000.png; [ -f $src ] || src=/tmp/v42t/$o/f000.png; [ -f $src ] || continue
  for s in 900 600; do cwebp -quiet -q 82 -m 6 -resize $s $s $src -o $P/poster/$o-$s.webp; done
  [ -f $R/poster-$o/f000.png ] && cwebp -quiet -q 86 -m 6 $src -o $P/poster/$o-2048.webp; done
for o in arm chip blade key; do d=$R/loop-$o; [ -f $d/f095.png ] || continue
  ffmpeg -y -loglevel error -framerate 12 -i $d/f%03d.png -vf "minterpolate=fps=24:mi_mode=mci:mc_mode=aobmc:vsbmc=1,format=yuv420p" -c:v libx264 -preset slow -crf 26 -movflags +faststart -an $P/loop/$o.mp4; done
[ -d $R/glb ] && cp $R/glb/*.glb $P/glb/ 2>/dev/null || true
du -sh $P/* 
