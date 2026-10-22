"""List the existing signal nets a proposed route would collide with.

Used to pick a targeted RIP_NETS set: route one open net with every rippable
net lifted (full export), then ask which current copper that path crosses.
usage: crossings.py T routes.json [net]
Prints one comma-separated line: the route's nets plus every rippable net hit.
"""
import sys, json
sys.path.insert(0, sys.argv[1])
from rt import *
import os
os.environ.pop('RIP_NETS', None)
from export_pf import rippable

routes = json.load(open(sys.argv[2]))
only = sys.argv[3] if len(sys.argv) > 3 else None
b = load(); r = Router(b)
R = rippable(b)
L = {'F': k.F_Cu, 'In2': k.In2_Cu, 'B': k.B_Cu}
hit = {}


def blame(shape, layer, net, clr=0.152):
    for it in r._items(layer):
        n = it.GetNetname()
        if n == net or n not in R or isinstance(it, k.PAD):
            continue
        if it.GetEffectiveShape(layer).Collide(shape, MM(clr)):
            hit[n] = hit.get(n, 0) + 1


for net, info in routes.items():
    if only and net != only:
        continue
    w = info['width']
    for rt_ in info['routes']:
        for l, pts in rt_['tracks']:
            P = [V(*p) for p in pts]
            for a, c in zip(P, P[1:]):
                blame(k.SHAPE_SEGMENT(a, c, MM(w)), L[l], net)
        for p in rt_['vias']:
            for l in (k.F_Cu, k.B_Cu):
                blame(k.SHAPE_CIRCLE(V(*p), MM(VIA_D / 2)), l, net)
print(' '.join(f'{n}:{c}' for n, c in sorted(hit.items(), key=lambda x: -x[1])), file=sys.stderr)
print(','.join(sorted(set([only] if only else routes) | set(hit))))
