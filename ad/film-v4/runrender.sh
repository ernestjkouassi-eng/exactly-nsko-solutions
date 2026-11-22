# args: fmt dpr then list of "f0:f1"
cd /home/user/film; fmt=$1; dpr=$2; shift 2
for r in "$@"; do f0=${r%:*}; f1=${r#*:}; o=out/${fmt}_$(printf %04d $f0).mp4; [ -f $o.ok ] && continue; node render.js chunk $fmt $f0 $f1 $o $dpr && touch $o.ok; done
