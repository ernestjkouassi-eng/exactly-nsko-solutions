#!/bin/bash
# Joins rendered chunks, adds the two mixes, makes phone and web copies.
set -e
cd /home/user/film; mkdir -p final
join(){ fmt=$1; out=$2; ls out/${fmt}_*.mp4 | sort | sed "s#^#file '#; s#\$#'#" > list_$fmt.txt; ffmpeg -v error -y -f concat -safe 0 -i list_$fmt.txt -c copy $out; }
mux(){ v=$1; a=$2; out=$3; ffmpeg -v error -y -i $v -i $a -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart $out; }
join h silent_h.mp4; join v silent_v.mp4; join c silent_c.mp4
# 4K master: re-encode to a sensible size
ffmpeg -v error -y -i silent_h.mp4 -c:v libx264 -crf 20 -preset slow -pix_fmt yuv420p -colorspace bt709 -color_primaries bt709 -color_trc bt709 silent_h4k.mp4
mux silent_h4k.mp4 mixA.wav final/nsko-solutions-film-4k.mp4
mux silent_h4k.mp4 mixB.wav final/nsko-solutions-film-4k-no-music.mp4
# 1080p phone copy
ffmpeg -v error -y -i silent_h.mp4 -vf scale=1920:1080:flags=lanczos -c:v libx264 -crf 19 -preset slow -pix_fmt yuv420p silent_h1080.mp4
mux silent_h1080.mp4 mixA.wav final/nsko-solutions-film-1080p.mp4
# 9:16 and the 15 s cut
ffmpeg -v error -y -i silent_v.mp4 -c:v libx264 -crf 19 -preset slow -pix_fmt yuv420p silent_v2.mp4
mux silent_v2.mp4 mixA.wav final/nsko-solutions-film-9x16.mp4
mux silent_v2.mp4 mixB.wav final/nsko-solutions-film-9x16-no-music.mp4
ffmpeg -v error -y -i silent_c.mp4 -c:v libx264 -crf 19 -preset slow -pix_fmt yuv420p silent_c2.mp4
mux silent_c2.mp4 mixA_15.wav final/nsko-solutions-reel-15s-9x16.mp4
mux silent_c2.mp4 mixB_15.wav final/nsko-solutions-reel-15s-9x16-no-music.mp4
# web copies for the site (kept small)
W=/home/user/nsko-solutions/public/media/film; mkdir -p $W
ffmpeg -v error -y -i silent_h.mp4 -i mixA.wav -map 0:v -map 1:a -vf scale=1920:1080:flags=lanczos -c:v libx264 -crf 25 -preset slow -maxrate 3M -bufsize 6M -pix_fmt yuv420p -c:a aac -b:a 160k -movflags +faststart -shortest $W/nsko-solutions-film.mp4
ffmpeg -v error -y -i silent_v.mp4 -i mixA.wav -map 0:v -map 1:a -c:v libx264 -crf 25 -preset slow -maxrate 2.5M -bufsize 5M -pix_fmt yuv420p -c:a aac -b:a 160k -movflags +faststart -shortest $W/nsko-solutions-film-9x16.mp4
ffmpeg -v error -y -ss 13.5 -i silent_h.mp4 -frames:v 1 -vf scale=1920:1080:flags=lanczos -q:v 4 $W/poster.jpg
cp mixA.wav final/soundtrack-with-music.wav; cp mixB.wav final/soundtrack-effects-only.wav
ls -la final $W
