#!/bin/bash
cd /home/user/nsko-solutions/marketing/v42; mkdir -p reels
for p in robot quad surgical arch watch; do node render_reel.js $p reels/raw-$p.mp4; done
S=/home/user/nsko-solutions/brand/templates/film/score.wav
for p in robot quad surgical arch watch; do
  ffmpeg -v error -y -i reels/raw-$p.mp4 -ss 3 -t 12.5 -i $S -af "afade=t=in:d=.6,afade=t=out:st=11.3:d=1.2,loudnorm=I=-14:TP=-1.5" -c:v copy -c:a aac -b:a 192k -shortest reels/nsko-reel-$p.mp4
done
echo REELS DONE
