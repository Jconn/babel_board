"""Export geometry for the negotiated-congestion router (KiCad Python).

Rips every rippable signal net's copper in memory, then writes fixed copper,
holes, keepouts, bodies and the terminal clusters of every net with gaps.
usage: export_pf.py S out.json
"""
import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rt import *

PROTECT = {'GND', 'CC1', 'CC2', 'CC_HIGH_N', 'CHG_N', 'V3V3_CC', 'USB_VBUS_RAW', 'VDD_DAUGHTER',
           'REG_FB', 'REG_L1', 'REG_L2', 'REG_AUX', 'REG_PS', 'CHG_ILIM', 'CHG_TMR', 'CHG_TS_FIXED',
           'CHG_ISET', 'BAT_SENSE', 'PACK_NTC'}


def rippable(b):
    out = set()
    for t in b.GetTracks():
        n = t.GetNetname()
        if n in PROTECT or not n:
            continue
        if b.FindNet(n).GetNetClassName() != 'Default':
            continue
        out.add(n)
    for f in b.GetFootprints():
        for p in f.Pads():
            n = p.GetNetname()
            if n and n not in PROTECT and not n.startswith('unconnected') and b.FindNet(n).GetNetClassName() == 'Default':
                out.add(n)
    # An explicit list permits local rerouting or a no-rip incremental pass.
    # Keep the same value for export and apply; protected nets remain protected.
    if 'RIP_NETS' in os.environ:
        requested = {n for n in os.environ['RIP_NETS'].split(',') if n}
        invalid = requested - out
        if invalid:
            raise ValueError(f'Unknown or protected rip-up nets: {sorted(invalid)}')
        out &= requested
    return out


ESC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pf', 'escapes.json')


def _key(t):
    if t.GetClass() == 'PCB_VIA':
        return ('via', t.GetNetname(), round(mm(t.GetPosition().x), 2), round(mm(t.GetPosition().y), 2))
    a = (round(mm(t.GetStart().x), 2), round(mm(t.GetStart().y), 2)); c = (round(mm(t.GetEnd().x), 2), round(mm(t.GetEnd().y), 2))
    return ('track', t.GetNetname(), t.GetBoard().GetLayerName(t.GetLayer())) + tuple(sorted([a, c]))


def escape_keys():
    """Hand-placed pin escapes of rippable nets (pf/escapes.json): kept as fixed copper."""
    keys = set()
    for e in (json.load(open(ESC)) if os.path.exists(ESC) else []):
        if e[0] == 'via':
            keys.add(('via', e[1], round(e[2][0], 2), round(e[2][1], 2)))
        else:
            x0, y0, x1, y1 = e[3]
            keys.add(('track', e[1], e[2]) + tuple(sorted([(round(x0, 2), round(y0, 2)), (round(x1, 2), round(y1, 2))])))
    return keys


def is_escape(t, keys):
    return _key(t) in keys


def rip_nets(b, nets):
    keys = escape_keys()
    for t in list(b.GetTracks()):
        if t.GetNetname() in nets and not is_escape(t, keys):
            b.RemoveNative(t)
    b.BuildConnectivity()


if __name__ == '__main__':
    b = load()
    R = rippable(b)
    rip_nets(b, R)
    LAYERS = {'F': k.F_Cu, 'In2': k.In2_Cu, 'B': k.B_Cu}

    def poly_of(item, layer):
        ps = k.SHAPE_POLY_SET()
        item.TransformShapeToPolygon(ps, layer, 0, MM(0.005), k.ERROR_INSIDE)
        ps.Simplify()
        return [[[mm(o.CPoint(j).x), mm(o.CPoint(j).y)] for j in range(o.PointCount())]
                for o in (ps.Outline(i) for i in range(ps.OutlineCount()))]

    uid = lambda it: it.m_Uuid.AsString()
    items, holes = [], []
    for f in b.GetFootprints():
        for p in f.Pads():
            for ln, l in LAYERS.items():
                if p.IsOnLayer(l):
                    items.append({'id': uid(p), 'net': p.GetNetname(), 'layer': ln, 'polys': poly_of(p, l)})
            if p.GetDrillSizeX() > 0:
                holes.append([mm(p.GetPosition().x), mm(p.GetPosition().y), mm(max(p.GetDrillSizeX(), p.GetDrillSizeY())) / 2])
                if not p.IsOnLayer(k.F_Cu):
                    for ln in LAYERS:
                        r_ = mm(p.GetDrillSizeX()) / (2 * math.cos(math.pi / 16))
                        items.append({'id': uid(p) + ln, 'net': '#NPTH', 'layer': ln,
                                      'polys': [[[mm(p.GetPosition().x) + r_ * math.cos(a * math.pi / 8),
                                                  mm(p.GetPosition().y) + r_ * math.sin(a * math.pi / 8)] for a in range(16)]]})
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
        cname = b.FindNet(net).GetNetClassName().split(',')[0]
        sig = float(os.environ.get('SIGW', '0.2'))
        nets[net] = {'clusters': lst, 'width': sig if cname == 'Default' else 0.3, 'rippable': net in R}
    json.dump({'items': items, 'bodies': bodies, 'holes': holes, 'keep': keep, 'nets': nets, 'ripped': sorted(R),
               'W': 60.0, 'H': 80.0}, open(sys.argv[2], 'w'))
    print('ripped', len(R), 'items', len(items), 'nets', len(nets), 'gaps', sum(len(v['clusters']) - 1 for v in nets.values()))
