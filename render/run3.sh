#!/bin/bash
cd /home/user/nsko-solutions/render; O=/home/user/nsko-solutions/render/out; export TH=4
while pgrep -f run2.sh >/dev/null; do sleep 30; done
ASP=1.414 A0=-20 python3 objects.py pendant 1 3600 64 $O/print-pendant > /dev/null 2>&1; echo print pendant done
