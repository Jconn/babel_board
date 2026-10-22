"""Apply pf router output to the native board with exact pcbnew checks.

Rips the rippable nets (as export_pf.py), adds each routed net all-or-nothing
(every segment and via checked at 0.152 mm), and restores a net's original
copper when its new route is rejected or missing (if that copper still clears).
usage: apply_pf.py S routes.json [save]
"""
import sys, json, os
sys.path.insert(0, sys.argv[1])
from rt import *
from export_pf import rippable, escape_keys, is_escape

routes = json.load(open(sys.argv[2]))
save = sys.argv[3:] == ['save']
b = load(); r = Router(b)
before = b.GetConnectivity().GetUnconnectedCount(True)
R = rippable(b)
orig = {}
keys = escape_keys()
for t in list(b.GetTracks()):
    n = t.GetNetname()
    if n in R and not is_escape(t, keys):
        if t.GetClass() == 'PCB_VIA':
            orig.setdefault(n, []).append(('via', t.GetPosition()))
        else:
            orig.setdefault(n, []).append(('track', t.GetLayer(), t.GetStart(), t.GetEnd(), mm(t.GetWidth())))
        b.RemoveNative(t)
b.BuildConnectivity()
L = {'F': k.F_Cu, 'In2': k.In2_Cu, 'B': k.B_Cu}


def try_net(net, items):
    """items: list of ('track', layer, a, b, w) / ('via', p); add all or nothing."""
    n0 = len(r.added)
    for it in items:
        if it[0] == 'via':
            if not r.via_ok(it[1], net, clr=0.152):
                r.undo(len(r.added) - n0); return f'via {mm(it[1].x):.2f},{mm(it[1].y):.2f}'
            r.via(net, it[1])
        else:
            _, l, a, c, w = it
            if not r.seg_ok(a, c, l, w, net, clr=0.152):
                r.undo(len(r.added) - n0); return f'{b.GetLayerName(l)} seg {mm(a.x):.2f},{mm(a.y):.2f}-{mm(c.x):.2f},{mm(c.y):.2f}'
            r.track(net, l, [a, c], w)
    return None


new_ok, new_rej, restored, partial, lost = [], [], [], [], []


def items_of(info):
    w = info['width']
    items = []
    for rt_ in info['routes']:
        for l, pts in rt_['tracks']:
            P = [V(*p) for p in pts]
            items += [('track', L[l], a, c, w) for a, c in zip(P, P[1:])]
        items += [('via', V(*p)) for p in rt_['vias']]
    return items


# 1) complete new routes
for net, info in routes.items():
    if not info.get('complete', True):
        continue
    why = try_net(net, items_of(info))
    if why:
        new_rej.append(net); print('REJECT', net, why, 'blocked by', r.last_failure)
    else:
        new_ok.append(net)
# 2) original copper for everything else, 3) partial new routes as a fallback
for net in sorted(R | set(routes)):
    if net in new_ok:
        continue
    if net in orig and not try_net(net, orig[net]):
        restored.append(net); continue
    if net in routes and not routes[net].get('complete', True) and not try_net(net, items_of(routes[net])):
        partial.append(net); continue
    if net in orig or net in routes:
        lost.append(net)
print(f'new {len(new_ok)} rejected {len(new_rej)} restored {len(restored)} partial {partial} lost {lost}')
fill(b)
after = b.GetConnectivity().GetUnconnectedCount(True)
print(f'unconnected {before} -> {after}')
g = gaps(b, sorted(R | set(routes)))
print('still open:', {n: len(c) - 1 for n, c in g.items()})
if os.environ.get('SAVEAS'):
    k.SaveBoard(os.environ['SAVEAS'], b); print('saved scratch', os.environ['SAVEAS'])
if save:
    if after >= before:
        print('not saved: no improvement')
    else:
        print('saved tracks', r.save())
