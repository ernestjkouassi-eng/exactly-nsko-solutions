#!/bin/bash
cd /home/user/nsko-solutions/render; O=/home/user/nsko-solutions/render/out; export TH=4
while pgrep -f "objects.py n 120" >/dev/null; do sleep 20; done
SKIP=1 FSTEP=2 ARC=100 A0=-50 python3 objects.py n 120 1600 32 $O/hero-n > $O/hero-n.log 2>&1; echo hero done
for o in drone arm chip blade key arch watch pendant n; do python3 objects.py $o 1 1 1 $O/glb glb > /dev/null 2>&1; done; echo glb done
for o in chip arm blade key drone arch watch pendant; do A0=-20 python3 objects.py $o 1 1600 48 $O/poster-$o > /dev/null 2>&1; echo poster $o; done
for o in chip arm blade key; do SKIP=1 FSTEP=2 python3 objects.py $o 96 720 24 $O/loop-$o > $O/loop-$o.log 2>&1; echo loop $o done; done
ASP=1.414 A0=-12 python3 objects.py n 1 3600 64 $O/print-n > /dev/null 2>&1; echo print done
echo ALL DONE
