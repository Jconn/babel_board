"""Export copper geometry + unrouted clusters for the grid router (KiCad Python)."""
import sys, json
sys.path.insert(0, sys.argv[1])
from rt import *

b = load(sys.argv[2])
out_path = sys.argv[3]
LAYERS = {'F': k.F_Cu, 'In2': k.In2_Cu, 'B': k.B_Cu}


def poly_of(item, layer):
    ps = k.SHAPE_POLY_SET()
    item.TransformShapeToPolygon(ps, layer, 0, MM(0.005), k.ERROR_INSIDE)
    ps.Simplify()
    res = []
    for i in range(ps.OutlineCount()):
        o = ps.Outline(i)
        res.append([[mm(o.CPoint(j).x), mm(o.CPoint(j).y)] for j in range(o.PointCount())])
    return res


def uid(it):
    return it.m_Uuid.AsString()


items = []   # {id, net, layer, polys}
holes = []   # [x, y, r]
for f in b.GetFootprints():
    for p in f.Pads():
        for ln, l in LAYERS.items():
            if p.IsOnLayer(l):
                items.append({'id': uid(p), 'net': p.GetNetname(), 'layer': ln, 'polys': poly_of(p, l),
                              'pad': f.GetReference() + '.' + p.GetNumber(),
                              'c': [mm(p.GetPosition().x), mm(p.GetPosition().y)]})
        if p.GetDrillSizeX() > 0:
            holes.append([mm(p.GetPosition().x), mm(p.GetPosition().y), mm(max(p.GetDrillSizeX(), p.GetDrillSizeY())) / 2])
            if not p.IsOnLayer(k.F_Cu):   # NPTH: block copper on every layer
                for ln in LAYERS:
                    items.append({'id': uid(p) + ln, 'net': '#NPTH', 'layer': ln,
                                  'polys': [[[mm(p.GetPosition().x) + mm(p.GetDrillSizeX()) / 2 * math.cos(a * math.pi / 8),
                                              mm(p.GetPosition().y) + mm(p.GetDrillSizeX()) / 2 * math.sin(a * math.pi / 8)] for a in range(16)]]})
for t in b.GetTracks():
    for ln, l in LAYERS.items():
        if t.IsOnLayer(l):
            items.append({'id': uid(t), 'net': t.GetNetname(), 'layer': ln, 'polys': poly_of(t, l)})
    if t.GetClass() == 'PCB_VIA':
        holes.append([mm(t.GetPosition().x), mm(t.GetPosition().y), mm(t.GetDrill()) / 2])
keep = []
for z in b.Zones():
    if z.GetIsRuleArea() and z.GetDoNotAllowTracks():
        o = z.Outline().Outline(0)
        keep.append([[mm(o.CPoint(j).x), mm(o.CPoint(j).y)] for j in range(o.PointCount())])

# metal/module bodies: no foreign F.Cu copper and no vias beneath them
bodies = []
for ref in ('J4', 'U1', 'SW4'):
    f = b.FindFootprintByReference(ref)
    bb = None
    for gi in f.GraphicalItems():
        if gi.GetLayer() == k.F_Fab:
            gb = gi.GetBoundingBox()
            if bb is None:
                bb = gb
            else:
                bb.Merge(gb)
    bodies.append({'ref': ref, 'rect': [mm(bb.GetX()), mm(bb.GetY()), mm(bb.GetRight()), mm(bb.GetBottom())],
                   'pads': [[mm(p.GetPosition().x), mm(p.GetPosition().y)] for p in f.Pads() if p.IsOnLayer(k.F_Cu)]})

# clusters of every net with gaps, expressed as item ids
c = b.GetConnectivity()
nets = {}
for net, cls in gaps(b).items():
    lst = []
    for cl in cls:
        ids = set()
        for _, p in cl:
            ids.add(uid(p))
            for q in c.GetConnectedItems(p):
                ids.add(uid(q))
        lst.append(sorted(ids))
    cls_name = b.FindNet(net).GetNetClassName().split(',')[0]
    widths = {'Power': 0.8, 'USB': 0.3, 'Default': 0.25}
    nets[net] = {'clusters': lst, 'width': widths[cls_name], 'class': cls_name}

json.dump({'items': items, 'bodies': bodies, 'holes': holes, 'keep': keep, 'nets': nets,
           'W': 60.0, 'H': 80.0}, open(out_path, 'w'))
print('items', len(items), 'nets with gaps', len(nets), 'gaps', sum(len(v['clusters']) - 1 for v in nets.values()))
