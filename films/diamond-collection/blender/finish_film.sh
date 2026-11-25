#!/bin/bash
# Waits for all frames, then assembles the 3K + 1080 films with callouts, grain, score and foley.
cd "$(dirname "$0")/.."
until [ -f /tmp/v42shots/film_done.txt ]; do sleep 60; done
python3 scripts/comp.py > /tmp/v42shots/comp.log 2>&1
echo COMP DONE >> /tmp/v42shots/comp.log
