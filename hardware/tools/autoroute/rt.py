"""Scratch routing toolkit for the native radio PCB (KiCad Python)."""
import math, sys, json, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pcbnew as k
from routing_io import save_routed_board

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) + '/'
MM = k.FromMM
mm = k.ToMM
CLR = 0.2          # working clearance (rule is 0.15)
VIA_D, VIA_H = 0.6, 0.3
CU = [k.F_Cu, k.In1_Cu, k.In2_Cu, k.B_Cu]


def load(name=None):
    import os
    name = name or os.environ.get('BOARD', 'radio/babel-radio.kicad_pcb')
    b = k.LoadBoard(name if name.startswith('/') else ROOT + name)
    b.BuildConnectivity()
    return b


def V(x, y):
    return k.VECTOR2I(MM(x), MM(y))


class Router:
    def __init__(self, b):
        self.b = b
        self.rules = [z for z in b.Zones() if z.GetIsRuleArea() and z.GetDoNotAllowTracks()]
        self.edge = b.GetBoardEdgesBoundingBox()
        self.added = []
        self.last_failure = None

    def net(self, name):
        return self.b.FindNet(name)

    # ---- collision -------------------------------------------------
    def _items(self, layer):
        for t in self.b.GetTracks():
            if t.IsOnLayer(layer):
                yield t
        for f in self.b.GetFootprints():
            for p in f.Pads():
                if p.IsOnLayer(layer) or p.GetDrillSizeX() > 0:
                    yield p

    def clear(self, shape, layer, net, clr=CLR, ignore=()):
        self.last_failure = None
        c = MM(clr)
        for it in self._items(layer):
            if it.GetNetname() == net and net != '':
                continue
            if it in ignore:
                continue
            if isinstance(it, k.PAD) and not it.IsOnLayer(layer):
                # hole of a pad on a layer it has no copper: check hole only
                hs = it.GetEffectiveHoleShape()
                if hs and hs.Collide(shape, c):
                    self.last_failure = "pad hole " + it.m_Uuid.AsString()
                    return False
                continue
            if it.GetEffectiveShape(layer).Collide(shape, c):
                label = (it.GetParentFootprint().GetReference() + "." + it.GetNumber()) if isinstance(it, k.PAD) else it.GetClass()
                pos = it.GetPosition()
                self.last_failure = f"{label} [{it.GetNetname()}] at {mm(pos.x):.3f},{mm(pos.y):.3f} on {self.b.GetLayerName(layer)}"
                return False
        return True

    def in_rules(self, pt, layer):
        for z in self.rules:
            if z.IsOnLayer(layer) and z.Outline().Contains(pt):
                return True
        return False

    def on_board(self, pt, margin):
        e = self.edge
        m = MM(margin)
        return e.GetX() + m <= pt.x <= e.GetRight() - m and e.GetY() + m <= pt.y <= e.GetBottom() - m

    def seg_ok(self, a, b_, layer, w, net, clr=CLR):
        self.last_failure = "board edge or rule area"
        s = k.SHAPE_SEGMENT(a, b_, MM(w))
        if self.in_rules(a, layer) or self.in_rules(b_, layer):
            return False
        if not (self.on_board(a, 0.3 + w / 2) and self.on_board(b_, 0.3 + w / 2)):
            return False
        return self.clear(s, layer, net, clr)

    def via_ok(self, p, net, layers=(k.F_Cu, k.In2_Cu, k.B_Cu), clr=CLR):
        self.last_failure = "board edge or rule area"
        if not self.on_board(p, 0.3 + VIA_D / 2):
            return False
        s = k.SHAPE_CIRCLE(p, MM(VIA_D / 2))
        for l in CU:
            if self.in_rules(p, l):
                return False
        for l in layers:
            if not self.clear(s, l, net, clr):
                return False
        # hole-to-hole vs vias/holes of any net
        for t in self.b.GetTracks():
            if t.GetClass() == 'PCB_VIA' and (t.GetPosition() - p).EuclideanNorm() < MM(VIA_D + 0.2):
                q = t.GetPosition()
                self.last_failure = f"via spacing [{t.GetNetname()}] at {mm(q.x):.3f},{mm(q.y):.3f}"
                return False
        return True

    # ---- creation --------------------------------------------------
    def track(self, net, layer, pts, w):
        n = self.net(net)
        for a, b_ in zip(pts, pts[1:]):
            t = k.PCB_TRACK(self.b)
            t.SetStart(a); t.SetEnd(b_); t.SetWidth(MM(w)); t.SetLayer(layer); t.SetNet(n)
            self.b.Add(t); self.added.append(t)

    def via(self, net, p):
        v = k.PCB_VIA(self.b)
        v.SetPosition(p); v.SetWidth(MM(VIA_D)); v.SetDrill(MM(VIA_H)); v.SetNet(self.net(net))
        v.SetViaType(k.VIATYPE_THROUGH)
        self.b.Add(v); self.added.append(v)
        return v

    def undo(self, n):
        if n <= 0:
            return
        for it in self.added[-n:]:
            self.b.RemoveNative(it)
        del self.added[-n:]

    def save(self):
        import os
        if os.environ.get('BOARD'):
            raise RuntimeError('BOARD override set: refusing native save')
        return save_routed_board(self.b)


def pads(b, net):
    return [(f.GetReference() + '.' + p.GetNumber(), p) for f in b.GetFootprints() for p in f.Pads() if p.GetNetname() == net]


def dump_zones(b, out):
    zs = []
    for z in b.Zones():
        if z.GetIsRuleArea():
            continue
        for l in z.GetLayerSet().Seq():
            ps = z.GetFilledPolysList(l)
            for i in range(ps.OutlineCount()):
                o = ps.Outline(i)
                zs.append([z.GetNetname(), b.GetLayerName(l), [[mm(o.CPoint(j).x), mm(o.CPoint(j).y)] for j in range(o.PointCount())]])
    json.dump(zs, open(out, 'w'))


def add_plane(b, net, layer, name, pts=((0.3, 0.3), (59.7, 0.3), (59.7, 79.7), (0.3, 79.7)), clr=0.3):
    z = k.ZONE(b); z.SetLayer(layer); z.SetNet(b.FindNet(net))
    o = z.Outline(); o.NewOutline()
    for x, y in pts:
        o.Append(MM(x), MM(y))
    z.SetLocalClearance(MM(clr)); z.SetMinThickness(MM(0.25))
    z.SetThermalReliefGap(MM(0.4)); z.SetThermalReliefSpokeWidth(MM(0.5))
    z.SetPadConnection(k.ZONE_CONNECTION_THERMAL)
    z.SetIslandRemovalMode(k.ISLAND_REMOVAL_MODE_ALWAYS); z.SetZoneName(name)
    b.Add(z)
    return z


def fill(b):
    b.BuildConnectivity(); k.ZONE_FILLER(b).Fill(b.Zones()); b.BuildConnectivity()


def clusters(b, net):
    """Pad clusters of a net that are copper-connected (list of lists of (ref, pad))."""
    c = b.GetConnectivity()
    ps = pads(b, net); seen = set(); out = []
    for name, p in ps:
        if name in seen:
            continue
        group = {name}
        for q in c.GetConnectedItems(p):
            if isinstance(q, k.PAD):
                group.add(q.GetParentFootprint().GetReference() + '.' + q.GetNumber())
        seen |= group
        out.append([(n, pp) for n, pp in ps if n in group])
    return out


def gaps(b, nets=None):
    names = nets or sorted({p.GetNetname() for f in b.GetFootprints() for p in f.Pads() if p.GetNetname() and not p.GetNetname().startswith('unconnected')})
    res = {}
    for n in names:
        cl = clusters(b, n)
        if len(cl) > 1:
            res[n] = cl
    return res


def in_fill(z, layer, p, r):
    ps = z.GetFilledPolysList(layer)
    pts = [p] + [k.VECTOR2I(int(p.x + MM(r) * math.cos(a)), int(p.y + MM(r) * math.sin(a))) for a in [i * math.pi / 4 for i in range(8)]]
    return all(ps.Contains(q) for q in pts)


def drop_via(r, name, pad, net, zone, w=0.3, dmax=3.2, layer=k.F_Cu, angles=None):
    """Short stub from pad centre on `layer` to a via that lands inside `zone` fill."""
    c = pad.GetPosition()
    best = None
    for d10 in range(8, int(dmax * 10) + 1, 2):
        d = d10 / 10
        for a in ([math.radians(x) for x in angles] if angles else [i * math.pi / 12 for i in range(24)]):
            v = k.VECTOR2I(int(c.x + MM(d) * math.cos(a)), int(c.y + MM(d) * math.sin(a)))
            if pad.GetEffectiveShape(layer).Collide(k.SHAPE_CIRCLE(v, MM(VIA_D / 2)), MM(0.1)):
                continue
            if not in_fill(zone, zone.GetLayer(), v, VIA_D / 2 + 0.05):
                continue
            if not r.via_ok(v, net):
                continue
            if not r.seg_ok(c, v, layer, w, net):
                continue
            best = v
            break
        if best:
            break
    if not best:
        return None
    r.track(net, layer, [c, best], w)
    r.via(net, best)
    return (mm(best.x), mm(best.y))


def rip(b, specs):
    """Remove copper matched exactly: ('via', net, (x,y)) or ('track', net, layer, (x0,y0,x1,y1))."""
    gone = []
    for t in list(b.GetTracks()):
        for s in specs:
            if t.GetNetname() != s[1]:
                continue
            if s[0] == 'via' and t.GetClass() == 'PCB_VIA':
                if abs(mm(t.GetPosition().x) - s[2][0]) < 0.01 and abs(mm(t.GetPosition().y) - s[2][1]) < 0.01:
                    gone.append(t); break
            if s[0] == 'track' and t.GetClass() == 'PCB_TRACK' and b.GetLayerName(t.GetLayer()) == s[2]:
                a = (mm(t.GetStart().x), mm(t.GetStart().y), mm(t.GetEnd().x), mm(t.GetEnd().y))
                if all(abs(u - v) < 0.01 for u, v in zip(a, s[3])) or all(abs(u - v) < 0.01 for u, v in zip(a[2:] + a[:2], s[3])):
                    gone.append(t); break
    if len(gone) != len(specs):
        raise RuntimeError(f'rip matched {len(gone)} of {len(specs)}')
    for t in gone:
        b.RemoveNative(t)
    return len(gone)


FANOUT_RIP = [
    ('via', 'USB_VBUS_RAW', (7.40, 43.40)), ('track', 'USB_VBUS_RAW', 'F.Cu', (7.40, 42.60, 7.40, 43.40)),
    ('track', 'USB_VBUS_RAW', 'In2.Cu', (7.40, 42.60, 7.40, 43.40)), ('track', 'USB_VBUS_RAW', 'In2.Cu', (7.40, 43.40, 7.25, 43.55)),
    ('track', 'USB_VBUS_RAW', 'In2.Cu', (7.25, 43.55, 7.25, 47.40)),
    ('via', 'USB_VBUS_RAW', (7.25, 46.60)), ('track', 'USB_VBUS_RAW', 'F.Cu', (7.25, 47.40, 7.25, 46.60)),
    ('via', 'USB_VBUS_RAW', (7.25, 47.40)), ('track', 'USB_VBUS_RAW', 'F.Cu', (6.18, 47.40, 7.25, 47.40)),
    ('via', 'GND', (6.90, 48.20)), ('track', 'GND', 'F.Cu', (6.18, 48.20, 6.90, 48.20)),
    ('via', 'GND', (7.20, 49.35)), ('track', 'GND', 'F.Cu', (7.92, 49.35, 7.20, 49.35)),
    ('via', 'GND', (8.60, 46.95)), ('track', 'GND', 'F.Cu', (8.60, 47.70, 8.60, 46.95)),
    ('via', 'GND', (8.75, 45.02)), ('track', 'GND', 'F.Cu', (8.75, 44.11, 8.75, 45.02)),
]
