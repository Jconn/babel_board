#!/bin/bash
# Like targeted.sh, but tries K router variants per net in parallel (dry runs),
# then saves the best one if it reduces the unconnected count.
# usage: targeted_multi.sh WORKDIR NUMPY_PYTHON [net ...]   (run from the repo root)
# env: K (variants, default 8), ITERS (default 40), GROUP=1 (treat the listed
#      nets as one group: rip the union of their crossings and renegotiate once)
set -u
W=$1; NP=$2; shift 2
T=hardware/tools/autoroute
A=AppDir/bin/python3.11
K=${K:-8}
mkdir -p $W
g++ -O3 -march=native -fopenmp -std=c++17 -w -o $W/pfr $T/pf.cpp || exit 1

count() { RIP_NETS='' $A $T/export_pf.py $T $W/cnt.json 2>/dev/null | sed 's/.*gaps //'; }
open_nets() {
    RIP_NETS='' $A $T/export_pf.py $T $W/open.json 2>/dev/null >/dev/null
    python3 -c "import json; print(' '.join(json.load(open('$W/open.json'))['nets']))"
}
PFM=(1.6 1.3 1.2 1.6 1.4 1.3 1.5 1.2 1.6 1.3 1.4 1.2)
HF=(0.4 1.0 2.0 1.0 0.6 0.4 1.5 1.0 2.0 2.0 0.8 0.5)

nets=${*:-$(open_nets)}
echo "start: $(count) open connections; nets: $nets"
groups=$nets
[ -n "${GROUP:-}" ] && groups=$(echo $nets | tr ' ' ',')
for g in $groups; do
    cur=$(count)
    echo "== $g (board at $cur)"
    $A $T/export_pf.py $T $W/full.json 2>/dev/null >/dev/null
    $NP -I $T/prep_pf.py $W/full.json $W/full.bin $W/full-n.json >/dev/null
    set_=""
    for n in ${g//,/ }; do
        ONLY=$n $W/pfr $W/full.bin $W/full-n.json $W/x.json 1 2>/dev/null
        s=$($A $T/crossings.py $T $W/x.json $n 2>$W/cross.txt)
        echo "   $n crosses: $(cat $W/cross.txt)"
        [ -n "$s" ] && set_=$set_${set_:+,}$s
    done
    set_=$(echo $set_ | tr ',' '\n' | sort -u | paste -sd,)
    [ -z "$set_" ] && { echo "   no unobstructed route"; continue; }
    RIP_NETS=$set_ $A $T/export_pf.py $T $W/t.json 2>/dev/null | tail -1 | sed 's/^/   /'
    $NP -I $T/prep_pf.py $W/t.json $W/t.bin $W/t-n.json >/dev/null
    for i in $(seq 0 $((K - 1))); do
        ( SEED=$i PFMUL=${PFM[$i % 12]} HFAC=${HF[$i % 12]} $W/pfr $W/t.bin $W/t-n.json $W/v$i.json ${ITERS:-40} 2>$W/v$i.log
          RIP_NETS=$set_ $A $T/apply_pf.py $T $W/v$i.json 2>/dev/null | grep '^unconnected' | sed "s/.*-> //;s/^/$i /" > $W/v$i.score ) &
    done
    wait
    best=$(cat $W/v*.score 2>/dev/null | sort -k2 -n | head -1)
    echo "   variants: $(cat $W/v*.score | sort -k2 -n | awk '{printf "%s:%s ", $1, $2}')"
    rm -f $W/v*.score
    bi=${best%% *}; bc=${best##* }
    if [ -n "$best" ] && [ "$bc" -lt "$cur" ]; then
        RIP_NETS=$set_ $A $T/apply_pf.py $T $W/v$bi.json save 2>/dev/null | grep -E "^new|^unconnected|^saved|^not saved" | sed 's/^/   /'
    else
        echo "   no improvement ($bc vs $cur)"
    fi
done
echo "end: $(count) open connections"
