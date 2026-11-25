#!/bin/bash
cd "$(dirname "$0")"
while pgrep -f queue_cp2.sh >/dev/null; do sleep 20; done
CLASP=.76 CAM=.12,-.62,.075 TX=0 TY=0 TZ=.003 RES=1620,2880 SPP=192 python3 cuban_still.py $PWD/../stills/hero_cuban_3k.png > /tmp/v42shots/q_cub.log 2>&1
CLASP=.76 RES=1620,2880 SPP=160 F=8 FILL=6 CAM=-.1797,-.0386,.1074 TX=-.0571 TY=-.0088 TZ=-.0065 FOCUS=-.0636,-.0104,-.0005 python3 cuban_still.py $PWD/../stills/cuban_clasp_macro_3k.png > /tmp/v42shots/q_cubc.log 2>&1
echo CUBAN DONE
