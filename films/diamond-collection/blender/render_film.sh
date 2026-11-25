#!/bin/bash
# Renders every shot of the film (resumable: finished frames are skipped).
cd "$(dirname "$0")"
for s in title_open cuban neck ring watch hero_cuban hero_neck hero_ring hero_watch title_end; do
  SHOT=$s python3 film.py > /tmp/v42shots/film_$s.log 2>&1
done
echo FILM FRAMES DONE > /tmp/v42shots/film_done.txt
