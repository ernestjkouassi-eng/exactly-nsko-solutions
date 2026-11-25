#!/bin/bash
cd "$(dirname "$0")"
while pgrep -f queue_cp2.sh >/dev/null; do sleep 20; done
CLASP=.82 CAM=.15,-.72,.075 TX=0 TY=0 TZ=.008 RES=1620,2880 SPP=192 python3 cuban_still.py $PWD/../stills/hero_cuban_3k.png > /tmp/v42shots/q_cub.log 2>&1
# clasp macro (the same chain, close on the box clasp)
CLASP=.82 RES=1620,2880 SPP=160 F=5.6 CAM=-.171,-.149,.072 TX=-.0615 TY=-.037 TZ=-.0166 FOCUS=-.0664,-.042,-.0127 python3 cuban_still.py $PWD/../stills/cuban_clasp_macro_3k.png > /tmp/v42shots/q_cubc.log 2>&1
echo CUBAN DONE
