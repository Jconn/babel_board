"""Place front reference designators on F.Silkscreen clear of pads, holes, component bodies,
other silk and the board outline. Probe-pad grids get number-only board labels; references
that cannot fit at 0.8 mm are hidden (they remain on F.Fab). Mounting-hole references are hidden.

usage (repo root): BOARD=radio/babel-radio.kicad_pcb AppDir/bin/python3.11 hardware/tools/place_silk.py [save]
Without 'save' it only reports, or writes to $OUT if set (a scratch copy). 'save' writes the
native board through routing_io.save_routed_board. Rerunnable: it replaces its own number labels.
"""
import sys, os, math, collections, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'autoroute'))
from rt import *

save = sys.argv[1:] == ['save']
b = load()
# drop probe-number labels from a previous run before indexing obstacles
for d in list(b.GetDrawings()):
    if isinstance(d, k.PCB_TEXT) and d.GetLayer() == k.F_SilkS and re.fullmatch(r'\d+', d.GetText()):
        b.RemoveNative(d)
EDGE = 0.35      # silk to board edge
PADCLR = 0.12    # silk to exposed copper / holes
SILKCLR = 0.12   # silk to silk
SIZES = [(1.0, 0.15, SILKCLR), (0.8, 0.12, 0.06)]   # height, stroke, silk-to-silk clearance
BUCKET = MM(2)

ebb = b.GetBoardEdgesBoundingBox()
EX0, EY0, EX1, EY1 = ebb.GetX(), ebb.GetY(), ebb.GetRight(), min(ebb.GetBottom(), MM(80))


class Index:
    def __init__(self):
        self.cells = collections.defaultdict(list)

    def add(self, bbox, obj):
        for i in range(bbox.GetX() // BUCKET, bbox.GetRight() // BUCKET + 1):
            for j in range(bbox.GetY() // BUCKET, bbox.GetBottom() // BUCKET + 1):
                self.cells[(i, j)].append((bbox, obj))

    def near(self, bbox, m):
        seen = set()
        for i in range((bbox.GetX() - m) // BUCKET, (bbox.GetRight() + m) // BUCKET + 1):
            for j in range((bbox.GetY() - m) // BUCKET, (bbox.GetBottom() + m) // BUCKET + 1):
                for bb, o in self.cells.get((i, j), ()):
                    if id(o) in seen:
                        continue
                    seen.add(id(o))
                    if bb.GetX() - m <= bbox.GetRight() and bbox.GetX() - m <= bb.GetRight() and \
                       bb.GetY() - m <= bbox.GetBottom() and bbox.GetY() - m <= bb.GetBottom():
                        yield o


hard = Index()   # (shape, clearance, owner-footprint or None)
soft = Index()   # vias: tented, allowed but penalised
crt = []         # (footprint, polyset)

for f in b.GetFootprints():
    for p in f.Pads():
        if p.IsOnLayer(k.F_Mask) or p.IsOnLayer(k.F_Cu):
            sh = p.GetEffectiveShape(k.F_Cu)
            hard.add(p.GetBoundingBox(), (sh, PADCLR, None))
        if p.GetDrillSizeX() > 0:
            hs = p.GetEffectiveHoleShape()
            hard.add(p.GetBoundingBox(), (hs, PADCLR, None))
    for g in f.GraphicalItems():
        if g.GetLayer() == k.F_SilkS and not isinstance(g, k.PCB_TEXT):
            hard.add(g.GetBoundingBox(), (g.GetEffectiveShape(k.F_SilkS), SILKCLR, None))
    # component body = F.Fab outline extent (text under a body is unreadable after assembly)
    xs, ys = [], []
    for g in f.GraphicalItems():
        if g.GetLayer() == k.F_Fab and not isinstance(g, k.PCB_TEXT):
            gb = g.GetBoundingBox(); xs += [gb.GetX(), gb.GetRight()]; ys += [gb.GetY(), gb.GetBottom()]
    if not xs and not f.GetReference().startswith('TP'):   # bare test pads have no body
        c = f.GetCourtyard(k.F_CrtYd)
        if c.OutlineCount():
            bb = c.BBox(); xs = [bb.GetX(), bb.GetRight()]; ys = [bb.GetY(), bb.GetBottom()]
    if xs:
        body = k.BOX2I(k.VECTOR2I(min(xs), min(ys)), k.VECTOR2L(max(xs) - min(xs), max(ys) - min(ys)))
        hard.add(body, (k.SHAPE_RECT(body), 0, f))
OUTLINE = k.SHAPE_POLY_SET()
b.GetBoardPolygonOutlines(OUTLINE, False)
for d in b.GetDrawings():
    if d.GetLayer() == k.Edge_Cuts:
        hard.add(d.GetBoundingBox(), (d.GetEffectiveShape(k.Edge_Cuts), EDGE, None))
    if d.GetLayer() == k.F_SilkS:
        hard.add(d.GetBoundingBox(), (d.GetEffectiveShape(k.F_SilkS), SILKCLR, None))
for t in b.GetTracks():
    if t.GetClass() == 'PCB_VIA':
        soft.add(t.GetBoundingBox(), t.GetEffectiveShape(k.F_Cu))

holes = [f for f in b.GetFootprints() if f.GetReference().startswith('H')]
for f in holes:
    f.Reference().SetVisible(False)

parts = [f for f in b.GetFootprints() if f not in holes]


def fp_box(f):
    # anchor labels to the body (F.Fab) and pads, not the courtyard (U1's spans the antenna clearance)
    xs, ys = [], []
    for g in list(f.GraphicalItems()) + list(f.Pads()):
        if isinstance(g, k.PAD) or (g.GetLayer() == k.F_Fab and not isinstance(g, k.PCB_TEXT)):
            gb = g.GetBoundingBox(); xs += [gb.GetX(), gb.GetRight()]; ys += [gb.GetY(), gb.GetBottom()]
    return min(xs), min(ys), max(xs), max(ys)


def candidates(f, h):
    x0, y0, x1, y1 = fp_box(f)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    out = []
    w = len(f.GetReference()) * h * 0.85 + 0.2   # rough text length in mm
    for gap in (-0.25, -0.1, 0.05, 0.2, 0.4, 0.65, 0.95, 1.3, 1.8, 2.4):
        g = MM(gap); hh = MM(h / 2 + 0.1); ww = MM(w / 2)
        for s in (0, -0.25, 0.25, -0.5, 0.5, -1, 1):
            sx = MM(s * w); sy = MM(s * h * 1.5)
            # above / below, horizontal text
            out += [(cx + sx, y0 - g - hh, 0, gap, abs(s)), (cx + sx, y1 + g + hh, 0, gap, abs(s))]
            # left / right, horizontal text
            out += [(x0 - g - ww, cy + sy, 0, gap + 0.1, abs(s)), (x1 + g + ww, cy + sy, 0, gap + 0.1, abs(s))]
            # left / right, vertical text
            out += [(x0 - g - hh, cy + sx, 90, gap + 0.3, abs(s)), (x1 + g + hh, cy + sx, 90, gap + 0.3, abs(s))]
    return out


def collide(f, ref, silkclr):
    bb = ref.GetBoundingBox()
    if bb.GetX() < EX0 + MM(EDGE) or bb.GetY() < EY0 + MM(EDGE) or bb.GetRight() > EX1 - MM(EDGE) or bb.GetBottom() > EY1 - MM(EDGE):
        return True
    if not all(OUTLINE.Contains(k.VECTOR2I(x, y)) for x in (bb.GetX(), bb.GetRight()) for y in (bb.GetY(), bb.GetBottom())):
        return True
    sh = ref.GetEffectiveShape(k.F_SilkS)
    for shape, clr, owner in hard.near(bb, MM(0.2)):
        if owner is not None:
            # bodies: any overlap (own included) hides the text
            rect = k.SHAPE_RECT(bb)
            if shape.Collide(rect, 0):
                return True
            continue
        if shape.Collide(sh, MM(silkclr if clr == SILKCLR else clr)):
            return True
    return False


def via_hits(ref):
    bb = ref.GetBoundingBox()
    return sum(1 for v in soft.near(bb, 0) if v.Collide(k.SHAPE_RECT(bb), 0))


def difficulty(f):
    x0, y0, x1, y1 = fp_box(f)
    n = sum(1 for _ in hard.near(k.BOX2I(k.VECTOR2I(x0 - MM(2), y0 - MM(2)), k.VECTOR2L(x1 - x0 + MM(4), y1 - y0 + MM(4))), 0))
    return (0 if f.GetReference().startswith('TP') else 1, -n)


# Probe-pad grids (TP with another TP within 3.2 mm): "TPnn" is wider than the 2.6 mm pitch, so the
# reference is hidden and a board-level number label sits beside each pad (below, else above/right/left).
tps = [f for f in parts if f.GetReference().startswith('TP')]
grid = [f for f in tps if any(g is not f and (g.GetPosition() - f.GetPosition()).EuclideanNorm() < MM(3.2) for g in tps)]
numbered, unnumbered = [], []
for f in sorted(grid, key=lambda f: (f.GetPosition().y, f.GetPosition().x)):
    f.Reference().SetVisible(False)
    t = k.PCB_TEXT(b)
    t.SetText(f.GetReference()[2:]); t.SetLayer(k.F_SilkS)
    t.SetTextSize(k.VECTOR2I(MM(0.8), MM(0.8))); t.SetTextThickness(MM(0.12))
    t.SetHorizJustify(k.GR_TEXT_H_ALIGN_CENTER); t.SetVertJustify(k.GR_TEXT_V_ALIGN_CENTER)
    p = f.GetPosition(); ok = False
    pr = mm(list(f.Pads())[0].GetBoundingBox().GetWidth()) / 2 + 0.26   # pad radius + its silk ring
    nw = 0.45 * len(t.GetText()) + 0.1                                    # half number width, 0.8 mm text
    offs = [(0, pr + 0.53), (0, -pr - 0.53), (pr + 0.06 + nw, 0), (-pr - 0.06 - nw, 0)]
    for dx, dy in offs + [(x * 1.15, y * 1.15) for x, y in offs]:
        t.SetPosition(k.VECTOR2I(p.x + MM(dx), p.y + MM(dy)))
        if not collide(f, t, 0.06):
            ok = True; break
    if ok:
        b.Add(t); hard.add(t.GetBoundingBox(), (t.GetEffectiveShape(k.F_SilkS), SILKCLR, None)); numbered.append(f.GetReference())
    else:
        unnumbered.append(f.GetReference())
parts = [f for f in parts if f not in grid]
print('probe grid numbers', len(numbered), 'unlabelled', unnumbered)

placed, hidden, sizes = [], [], collections.Counter()
for f in sorted(parts, key=difficulty):
    ref = f.Reference()
    ref.SetVisible(True)
    ref.SetLayer(k.F_SilkS)
    ref.SetHorizJustify(k.GR_TEXT_H_ALIGN_CENTER)
    ref.SetVertJustify(k.GR_TEXT_V_ALIGN_CENTER)
    ref.SetKeepUpright(True)
    best = None
    for si, (h, th, sclr) in enumerate(SIZES):
        ref.SetTextSize(k.VECTOR2I(MM(h), MM(h)))
        ref.SetTextThickness(MM(th))
        for x, y, ang, gap, off in candidates(f, h):
            ref.SetTextAngleDegrees(ang)
            ref.SetPosition(k.VECTOR2I(int(x), int(y)))
            if collide(f, ref, sclr):
                continue
            score = gap + 0.4 * off + 0.5 * via_hits(ref)
            if best is None or score < best[0]:
                best = (score, x, y, ang)
        if best:
            sizes[h] += 1
            break
    if best is None:
        ref.SetVisible(False)
        hidden.append(f.GetReference())
        continue
    _, x, y, ang = best
    ref.SetTextAngleDegrees(ang)
    ref.SetPosition(k.VECTOR2I(int(x), int(y)))
    hard.add(ref.GetBoundingBox(), (ref.GetEffectiveShape(k.F_SilkS), SILKCLR, None))
    placed.append(f.GetReference())

print('placed', len(placed), dict(sizes), 'hidden', len(hidden), sorted(hidden))
print('mounting-hole refs hidden', len(holes))
if save:
    print('saved', save_routed_board(b))
elif os.environ.get('OUT'):
    k.SaveBoard(os.environ['OUT'], b)
