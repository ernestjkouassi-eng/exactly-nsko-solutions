#!/bin/bash
# waits for the reels, then renders the promo film 16:9 (3840x2160) and 9:16 (2160x3840), 56 s at 24 fps, and adds the score
cd /home/user/nsko-solutions/brand/templates/film
while pgrep -f run_reels.sh >/dev/null; do sleep 30; done
(cd /home/user/nsko-solutions && (pgrep -f "http.server 8830" >/dev/null || python3 -m http.server 8830 >/dev/null 2>&1 &))
sleep 2; mkdir -p out
node render.js chunk promo h 0 1344 out/h.mp4 2
node render.js chunk promo v 0 1344 out/v.mp4 2
S=score.wav
ffmpeg -v error -y -i out/h.mp4 -i $S -af "loudnorm=I=-14:TP=-1.5" -c:v copy -c:a aac -b:a 256k -shortest out/nsko-solutions-film-4k.mp4
ffmpeg -v error -y -i out/v.mp4 -i $S -af "loudnorm=I=-14:TP=-1.5" -c:v copy -c:a aac -b:a 256k -shortest out/nsko-solutions-film-9x16.mp4
ffmpeg -v error -y -i out/nsko-solutions-film-4k.mp4 -vf scale=1920:1080 -c:v libx264 -crf 21 -preset medium -c:a copy -movflags +faststart out/nsko-solutions-film-1080p.mp4
echo FILM DONE
