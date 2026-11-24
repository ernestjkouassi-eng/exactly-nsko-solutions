#!/bin/bash
cd /home/user/nsko-solutions/render; export TH=4
while pgrep -f "run4.sh|run5.sh" >/dev/null; do sleep 30; done
python3 luxury.py watch 1600 96 out/lux/watch.png > out/lux/wf2.log 2>&1; echo "watch redone"
echo ALL6 DONE
