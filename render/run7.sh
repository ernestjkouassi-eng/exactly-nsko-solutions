#!/bin/bash
cd /home/user/nsko-solutions/render; export TH=4
while pgrep -f "run4.sh|run5.sh|run6.sh" >/dev/null; do sleep 30; done
python3 luxury.py pendant 1600 96 out/lux/pendant.png > out/lux/pf2.log 2>&1; echo "pendant redone"
echo ALL7 DONE
