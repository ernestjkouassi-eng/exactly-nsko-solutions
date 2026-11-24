#!/bin/bash
cd /home/user/nsko-solutions/render; export TH=4
for s in robot chip surgical quad arch wire; do python3 scenes.py $s 1600 64 out/scn/$s.png > out/scn/$s-f.log 2>&1; echo "$s done"; done
python3 scenes.py iced 1600 128 out/scn/iced.png > out/scn/iced-f.log 2>&1; echo "iced done"
python3 luxury.py watch 1600 96 out/lux/watch.png > out/lux/wf.log 2>&1; echo "watch done"
python3 luxury.py pendant 1600 96 out/lux/pendant.png > out/lux/pf.log 2>&1; echo "pendant done"
SKIP=1 FSTEP=2 ARC=100 A0=-50 python3 objects.py n 120 1600 32 out/hero-n > out/hero-n.log 2>&1; echo "hero done"
echo ALL DONE
