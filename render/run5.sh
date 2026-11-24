#!/bin/bash
cd /home/user/nsko-solutions/render; export TH=4
while pgrep -f run4.sh >/dev/null; do sleep 30; done
for s in robot chip; do python3 scenes.py $s 1600 64 out/scn/$s.png > out/scn/$s-f.log 2>&1; echo "$s redone"; done
echo ALL5 DONE
