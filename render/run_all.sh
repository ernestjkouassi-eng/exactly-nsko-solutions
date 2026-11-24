#!/bin/bash
# v4.2 render queue (sequential, TH threads)
cd /home/user/nsko-solutions/render; O=/home/user/nsko-solutions/render/out; mkdir -p $O
export TH=${TH:-3}
SKIP=1 FSTEP=2 ARC=100 A0=-50 python3 objects.py n 120 1600 32 $O/hero-n > $O/hero-n.log 2>&1; echo hero done
for o in drone arm chip blade key arch watch pendant n; do python3 objects.py $o 1 1 1 $O/glb glb > /dev/null 2>&1; done; echo glb done
for o in drone arm chip blade key arch watch pendant; do A0=-20 python3 objects.py $o 1 2048 64 $O/poster-$o > /dev/null 2>&1; done; echo posters done
for o in arm chip blade key; do SKIP=1 FSTEP=2 python3 objects.py $o 96 900 32 $O/loop-$o > $O/loop-$o.log 2>&1; echo loop $o done; done
echo ALL DONE
