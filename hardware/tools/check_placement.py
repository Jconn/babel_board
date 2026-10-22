"""Placement-stage rule checks for both boards (complements KiCad DRC).

Run with AppDir/bin/python3.11 from the repository root. Checks the mechanical
and accessibility rules from LAYOUT-PLAN.md that DRC cannot express: boot and
antenna envelopes, OLED standoff bodies, probe access to test pads, sensor
zone exclusivity and single-sided assembly. Courtyard overlap is left to DRC.
"""
from pathlib import Path
import math
import pcbnew as k

HW = Path(__file__).resolve().parents[1]
mm = k.ToMM
STANDOFF_R = 2.6  # M2 hex standoff / screw head body plus margin, top side
fails = []


def box(f):
    c = f.GetCourtyard(k.F_CrtYd)
    bb = c.BBox() if c.OutlineCount() else f.GetBoundingBox(False)
    return mm(bb.GetX()), mm(bb.GetY()), mm(bb.GetRight()), mm(bb.GetBottom())


def overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def hits_circle(r, cx, cy, rad):
    nx, ny = min(max(cx, r[0]), r[2]), min(max(cy, r[1]), r[3])
    return math.hypot(nx - cx, ny - cy) < rad


def check(name, cond, msg):
    if not cond:
        fails.append(f'{name}: {msg}')


def masks(name, b):
    # Seeds once lost *.Mask on through-hole pads (pins under soldermask).
    # Small-drill thermal vias (WROOM pad 41) are bottom-tented by the library.
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetAttribute() in (k.PAD_ATTRIB_PTH, k.PAD_ATTRIB_NPTH):
                tented_via = mm(p.GetDrillSize().x) <= 0.3
                check(f'{name} {f.GetReference()}', p.IsOnLayer(k.F_Mask) and (tented_via or p.IsOnLayer(k.B_Mask)),
                      f'hole pad {p.GetNumber() or "(npth)"} lacks soldermask opening')


def parts(b):
    return [f for f in b.GetFootprints() if not f.GetReference().startswith('H')]


# --- Radio ---
b = k.LoadBoard(str(HW / 'radio' / 'babel-radio.kicad_pcb'))
holes = {f.GetReference(): (mm(f.GetPosition().x), mm(f.GetPosition().y)) for f in b.GetFootprints()
         if f.GetReference().startswith('H')}
for f in parts(b):
    ref, r = f.GetReference(), box(f)
    check(ref, f.GetLayer() == k.F_Cu, 'not on top side')
    if f.IsLocked():
        continue  # interface anchors are checked by check_layout_seeds.py
    check(ref, 0 <= r[0] and 0 <= r[1] and r[2] <= 60 and r[3] <= 80, f'courtyard {r} leaves 60x80 outline')
    check(ref, not overlaps(r, (9, 1, 51, 13)), 'inside keyed boot envelope')
    check(ref, not overlaps(r, (6, 79, 54, 100)), 'inside antenna keepout')
    for h in ('H1', 'H2', 'H3', 'H4', 'H7', 'H8', 'H9', 'H10'):
        check(ref, not hits_circle(r, *holes[h], STANDOFF_R), f'within {STANDOFF_R} mm of {h} standoff/screw')
    if ref.startswith('TP'):
        check(ref, not overlaps(r, (12.22, 15, 47.78, 61.99)), 'test pad under OLED (not probe accessible)')
masks('radio', b)
print('radio placement rules checked')

# --- IR daughter ---
d = k.LoadBoard(str(HW / 'ir-daughter' / 'babel-ir-daughter.kicad_pcb'))
dh = {f.GetReference(): (mm(f.GetPosition().x), mm(f.GetPosition().y)) for f in d.GetFootprints()
      if f.GetReference().startswith('H')}
for f in parts(d):
    ref, r = f.GetReference(), box(f)
    check('daughter ' + ref, f.GetLayer() == k.F_Cu, 'not on front side')
    if ref == 'J1':
        continue
    check('daughter ' + ref, 5 <= r[0] and 10 <= r[1] and r[2] <= 35 and r[3] <= 35, f'courtyard {r} outside body')
    if ref not in ('U1', 'C1'):
        check('daughter ' + ref, not overlaps(r, (5, 10, 35, 25)), 'inside sensor thermal/optical zone')
    for h in ('H1', 'H2'):
        check('daughter ' + ref, not hits_circle(r, *dh[h], 2.5), f'copper part near carrier hole {h}')
masks('daughter', d)
print('daughter placement rules checked')

if fails:
    raise SystemExit('FAIL\n  ' + '\n  '.join(fails))
print('PASS placement rules: envelopes, standoffs, test-pad access, sensor zone, single-sided, hole-pad mask')
