"""Rasterise export_pf.py geometry into the binary grid read by pf.cpp.

usage: prep_pf.py geom.json grid.bin names.json
Layers in the grid: 0 = F, 1 = B, 2 = In2 (fixed copper only).
"""
import json, sys, math, os, struct
import numpy as np

G = float(os.environ.get('GRID', '0.05'))
geom = json.load(open(sys.argv[1]))
W, H = geom['W'], geom['H']
NX, NY = int(round(W / G)), int(round(H / G))
xs = (np.arange(NX) + 0.5) * G
ys = (np.arange(NY) + 0.5) * G
LI = {'F': 0, 'B': 1, 'In2': 2}
KEEP = -1

net_ids = {'': 0}
def nid(n):
    if n not in net_ids:
        net_ids[n] = len(net_ids)
    return net_ids[n]


def raster_poly(poly):
    p = np.asarray(poly)
    x0, y0 = p.min(0); x1, y1 = p.max(0)
    i0, i1 = max(int(x0 / G) - 1, 0), min(int(x1 / G) + 2, NX)
    j0, j1 = max(int(y0 / G) - 1, 0), min(int(y1 / G) + 2, NY)
    if i0 >= i1 or j0 >= j1:
        return None
    X, Y = np.meshgrid(xs[i0:i1], ys[j0:j1])
    inside = np.zeros(X.shape, bool)
    q = np.roll(p, -1, 0)
    for (ax, ay), (bx, by) in zip(p, q):
        cond = (ay > Y) != (by > Y)
        with np.errstate(divide='ignore', invalid='ignore'):
            xi = (bx - ax) * (Y - ay) / (by - ay) + ax
        inside ^= cond & (X < xi)
    strict = inside.copy()
    for (ax, ay), (bx, by) in zip(p, q):
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy or 1e-12
        t = np.clip(((X - ax) * dx + (Y - ay) * dy) / L2, 0, 1)
        inside |= np.hypot(X - (ax + t * dx), Y - (ay + t * dy)) <= G * 0.5
    jj, ii = np.nonzero(inside)
    sj, si = np.nonzero(strict)
    return jj + j0, ii + i0, sj + j0, si + i0


lab = np.zeros((3, NY, NX), np.int32)
item_cells = {}
for it in geom['items']:
    l = LI[it['layer']]
    n = KEEP if it['net'] in ('#NPTH', '') else nid(it['net'])
    for poly in it['polys']:
        r = raster_poly(poly)
        if r is None:
            continue
        jj, ii, sj, si = r
        if len(sj) == 0:   # thin item: use its outline cells
            sj, si = jj, ii
        # label strict-interior cells only; pf.cpp adds a half-cell diagonal plus polygon error for the edge position
        cur = lab[l][sj, si]
        lab[l][sj, si] = np.where((cur == 0) | (cur == n), n, KEEP)
        item_cells.setdefault(it['id'], []).append((l, sj, si))
for poly in geom['keep']:
    r = raster_poly(poly)
    if r is not None:
        lab[:, r[0], r[1]] = KEEP

viaforbid = np.zeros((NY, NX), np.uint8)
for bd in geom['bodies']:
    x0, y0, x1, y1 = bd['rect']
    i0, i1 = max(int(x0 / G), 0), min(int(math.ceil(x1 / G)), NX)
    j0, j1 = max(int(y0 / G), 0), min(int(math.ceil(y1 / G)), NY)
    m = np.zeros((NY, NX), bool); m[j0:j1, i0:i1] = True
    X, Y = np.meshgrid(xs[i0:i1], ys[j0:j1])
    near = np.zeros((NY, NX), bool)
    for px, py in bd['pads']:
        near[j0:j1, i0:i1] |= np.hypot(X - px, Y - py) < 0.9
    lab[0][m & ~near & (lab[0] == 0)] = KEEP
    # no vias under the body (plus via radius)
    R = int(math.ceil(0.4 / G))
    viaforbid[max(j0 - R, 0):j1 + R, max(i0 - R, 0):i1 + R] = 1
# hole-to-hole: via centre at least 0.8 mm from any drilled hole centre (as rt.via_ok)
for x, y, r in geom['holes']:
    rr = 0.8 + max(r - 0.15, 0)
    R = int(math.ceil(rr / G)) + 1
    j, i = int(y / G), int(x / G)
    for dj in range(-R, R + 1):
        for di in range(-R, R + 1):
            if math.hypot((i + di + 0.5) * G - x, (j + dj + 0.5) * G - y) <= rr + 0.005 and 0 <= j + dj < NY and 0 <= i + di < NX:
                viaforbid[j + dj, i + di] = 1

names = list(geom['nets'])
out = open(sys.argv[2], 'wb')
out.write(struct.pack('<iid', NX, NY, G))
out.write(lab.astype('<i4').tobytes())
out.write(viaforbid.tobytes())
out.write(struct.pack('<i', len(names)))
for n in names:
    info = geom['nets'][n]
    out.write(struct.pack('<idi', nid(n), info['width'], len(info['clusters'])))
    for cl in info['clusters']:
        cells = set()
        for i_ in cl:
            for l, sj, si in item_cells.get(i_, []):
                if l == 2:
                    continue
                cells.update((l * NY * NX + sj * NX + si).tolist())
        cells = sorted(cells)
        out.write(struct.pack('<i', len(cells)))
        out.write(np.asarray(cells, '<i4').tobytes())
out.close()
json.dump(names, open(sys.argv[3], 'w'))
print('grid', NX, NY, 'nets', len(names))
