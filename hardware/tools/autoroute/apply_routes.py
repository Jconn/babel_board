"""Apply grid-router proposals with exact pcbnew clearance checks; save if asked."""
import sys, json
sys.path.insert(0, sys.argv[1]); from rt import *
routes = json.load(open(sys.argv[2])); save = len(sys.argv) > 3 and sys.argv[3] == 'save'
b = load(); r = Router(b)
before = b.GetConnectivity().GetUnconnectedCount(True)
kept = rej = 0
for net, info in routes.items():
    w = info['width']
    for rt_ in info['routes']:
        n0 = len(r.added); ok = True
        for l, pts in rt_['tracks']:
            L = {'F': k.F_Cu, 'In2': k.In2_Cu, 'B': k.B_Cu}[l]
            P = [V(*p) for p in pts]
            for a, c in zip(P, P[1:]):
                if not r.seg_ok(a, c, L, w, net, clr=0.152):
                    ok = False; why = f'{l} seg {k.ToMM(a.x):.2f},{k.ToMM(a.y):.2f}'; break
            if not ok: break
            r.track(net, L, P, w)
        if ok:
            for p in rt_['vias']:
                if not r.via_ok(V(*p), net, clr=0.152):
                    ok = False; why = f'via {p}'; break
                r.via(net, V(*p))
        if ok:
            kept += 1
        else:
            rej += 1; r.undo(len(r.added) - n0); print('REJECT', net, why)
fill(b)
after = b.GetConnectivity().GetUnconnectedCount(True)
print(f'kept {kept} rejected {rej}; unconnected {before} -> {after}')
g = gaps(b, list(routes)); print('still open:', {n: len(c) - 1 for n, c in g.items()})
import os
if os.environ.get('SAVEAS'):
    k.SaveBoard(os.environ['SAVEAS'], b); print('saved scratch', os.environ['SAVEAS'])
if save:
    print('saved tracks', r.save())
