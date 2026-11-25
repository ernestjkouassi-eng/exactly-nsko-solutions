#!/bin/bash
# Waits for all shots, finishes the Cuban clasp frames and the opening title (website lockup), then assembles the films.
cd "$(dirname "$0")"
until [ -f /tmp/v42shots/film_done.txt ]; do sleep 60; done
SHOT=cuban python3 film.py > /tmp/v42shots/film_cuban2.log 2>&1
SHOT=title_open python3 film.py > /tmp/v42shots/film_title_open2.log 2>&1
cd ..; python3 scripts/comp.py > /tmp/v42shots/comp.log 2>&1
echo COMP DONE >> /tmp/v42shots/comp.log
