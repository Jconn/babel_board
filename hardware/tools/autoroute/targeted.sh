#!/bin/bash
# Targeted rip-up: for each open net, find the signal nets its unobstructed
# route crosses, rip only those, renegotiate, and save if the exact-checked
# result reduces the unconnected count.
# usage: targeted.sh WORKDIR NUMPY_PYTHON [net ...]   (run from the repo root)
set -u
W=$1; NP=$2; shift 2
T=hardware/tools/autoroute
A=AppDir/bin/python3.11
mkdir -p $W
g++ -O3 -march=native -fopenmp -std=c++17 -w -o $W/pfr $T/pf.cpp || exit 1

count() { RIP_NETS='' $A $T/export_pf.py $T $W/cnt.json 2>/dev/null | sed 's/.*gaps //'; }
open_nets() {
    RIP_NETS='' $A $T/export_pf.py $T $W/open.json 2>/dev/null >/dev/null
    python3 -c "import json; print(' '.join(json.load(open('$W/open.json'))['nets']))"
}

nets=${*:-$(open_nets)}
echo "start: $(count) open connections; nets: $nets"
for n in $nets; do
    echo "== $n"
    # 1) unobstructed route with every rippable net lifted
    $A $T/export_pf.py $T $W/full.json 2>/dev/null >/dev/null
    $NP -I $T/prep_pf.py $W/full.json $W/full.bin $W/full-n.json >/dev/null
    ONLY=$n $W/pfr $W/full.bin $W/full-n.json $W/x.json 1 2>/dev/null
    set_=$($A $T/crossings.py $T $W/x.json $n 2>$W/cross.txt)
    echo "   crosses: $(cat $W/cross.txt)"
    [ -z "$set_" ] && { echo "   no unobstructed route"; continue; }
    # 2) rip only that set and renegotiate
    RIP_NETS=$set_ $A $T/export_pf.py $T $W/t.json 2>/dev/null | tail -1 | sed 's/^/   /'
    $NP -I $T/prep_pf.py $W/t.json $W/t.bin $W/t-n.json >/dev/null
    $W/pfr $W/t.bin $W/t-n.json $W/t-r.json ${ITERS:-30} 2>$W/t.log
    grep -E "^final" $W/t.log | sed 's/^/   /'
    out=$(RIP_NETS=$set_ $A $T/apply_pf.py $T $W/t-r.json save 2>/dev/null)
    echo "$out" | grep -E "^new|^unconnected|^saved|^not saved" | sed 's/^/   /'
    echo "$out" | grep "^REJECT" | head -5 | sed 's/^/   /'
done
echo "end: $(count) open connections"
