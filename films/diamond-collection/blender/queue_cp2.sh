#!/bin/bash
# Checkpoint-2 stills at 1620x2880, one after another (CPU), then the watch design-sheet views.
cd "$(dirname "$0")"; OUT=../stills
while pgrep -f cuban_still.py >/dev/null; do sleep 20; done
CAM=.1,-.55,-.03 TX=0 TY=-.07 TZ=-.085 RES=1620,2880 SPP=160 python3 necklace_still.py $PWD/$OUT/hero_necklace_3k.png > /tmp/v42shots/q_neck.log 2>&1
RZ=40 CAM=-.07,-.12,.14 TGT=0,0,.02 RES=1620,2880 SPP=192 python3 ring_still.py $PWD/$OUT/hero_ring_3k.png > /tmp/v42shots/q_ring.log 2>&1
CAM=0,-.3,.0 RES=1620,2880 SPP=160 python3 watch_still.py $PWD/$OUT/hero_watch_3k.png > /tmp/v42shots/q_watch.log 2>&1
# design sheet: face-on, 9 o'clock caseband (NSKO engraving), 3/4 back
ROT=90,0,0 CAM=0,-.32,0 F=11 RES=1000,1000 SPP=96 python3 watch_still.py $PWD/$OUT/watch_design_front.png > /tmp/v42shots/q_wd1.log 2>&1
ROT=90,0,90 CAM=0,-.16,.0 F=11 RES=1000,1000 SPP=96 python3 watch_still.py $PWD/$OUT/watch_design_side9.png > /tmp/v42shots/q_wd2.log 2>&1
echo QUEUE DONE
