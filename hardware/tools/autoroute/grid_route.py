"""Two-layer (F/B) grid A* router with through vias. Proposes routes only;
pcbnew re-validates every segment/via exactly before anything is kept.

usage: grid_route.py geom.json out.json [net,net,...] [--width-override net=w,...]
"""
import json, sys, heapq, math
import numpy as np

import os
G = float(os.environ.get("GRID", "0.1"))  # grid pitch, mm
CLR = float(os.environ.get("CLR", "0.17"))  # copper clearance used for planning (rule 0.15)
QE = G * 0.71                 # quantisation slack
VIA_R = 0.3
VIA_COST = int(3.0 / G)    # via cost = 3 mm of track
LAYERS = os.environ.get('LAYERS', 'F,B').split(',')

geom = json.load(open(sys.argv[1]))
W, H = geom['W'], geom['H']
NX, NY = int(round(W / G)), int(round(H / G))
xs = (np.arange(NX) + 0.5) * G
ys = (np.arange(NY) + 0.5) * G

net_ids = {'': 0}
def nid(n):
    if n not in net_ids:
        net_ids[n] = len(net_ids)
    return net_ids[n]

KEEP = -1
occ = {l: np.zeros((NY, NX), np.int32) for l in ['F', 'In2', 'B']}
item_cells = {}               # id -> list of (layer, iy array, ix array)


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
    # also mark cells whose centre is within half a cell of the outline (thin shapes)
    for (ax, ay), (bx, by) in zip(p, q):
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy or 1e-12
        t = np.clip(((X - ax) * dx + (Y - ay) * dy) / L2, 0, 1)
        d = np.hypot(X - (ax + t * dx), Y - (ay + t * dy))
        inside |= d <= G * 0.5
    jj, ii = np.nonzero(inside)
    sj, si = np.nonzero(strict)
    return jj + j0, ii + i0, sj + j0, si + i0


for it in geom['items']:
    l = it['layer']
    n = KEEP if it['net'] in ('#NPTH', '') else nid(it['net'])
    cells = []
    for poly in it['polys']:
        r = raster_poly(poly)
        if r is None:
            continue
        jj, ii, sj, si = r
        cur = occ[l][jj, ii]
        occ[l][jj, ii] = np.where((cur == 0) | (cur == n), n, KEEP)
        cells.append((l, sj, si))
    item_cells.setdefault(it['id'], []).extend(cells)
for poly in geom['keep']:
    r = raster_poly(poly)
    if r is not None:
        for l in occ:
            occ[l][r[0], r[1]] = KEEP

# component bodies: F.Cu keepout except a corridor round the part's own pads
body_via = np.zeros((NY, NX), bool)
for bd in geom.get('bodies', []):
    x0, y0, x1, y1 = bd['rect']
    i0, i1 = max(int(x0 / G), 0), min(int(math.ceil(x1 / G)), NX)
    j0, j1 = max(int(y0 / G), 0), min(int(math.ceil(y1 / G)), NY)
    m = np.zeros((NY, NX), bool); m[j0:j1, i0:i1] = True
    if bd["ref"] not in os.environ.get("VIA_UNDER", "").split(","):
        body_via |= m
    near = np.zeros((NY, NX), bool)
    X, Y = np.meshgrid(xs[i0:i1], ys[j0:j1])
    for px, py in bd['pads']:
        near[j0:j1, i0:i1] |= np.hypot(X - px, Y - py) < 0.9
    occ['F'][m & ~near & (occ['F'] == 0)] = KEEP

# board edge: keep 0.3 mm copper-to-edge
edge = np.zeros((NY, NX), bool)
e = int(math.ceil(0.3 / G))
edge[:e, :] = edge[-e:, :] = True
edge[:, :e] = edge[:, -e:] = True

holes = np.zeros((NY, NX), bool)
for x, y, r in geom['holes']:
    holes[min(int(y / G), NY - 1), min(int(x / G), NX - 1)] = True


def disk(r):
    R = int(math.ceil(r / G))
    return [(dy, dx) for dy in range(-R, R + 1) for dx in range(-R, R + 1) if math.hypot(dx, dy) * G <= r]


def dilate(mask, r):
    out = np.zeros_like(mask)
    for dy, dx in disk(r):
        src = mask[max(-dy, 0):NY - max(dy, 0), max(-dx, 0):NX - max(dx, 0)]
        out[max(dy, 0):NY - max(-dy, 0), max(dx, 0):NX - max(-dx, 0)] |= src
    return out


def blocked_for(net, w):
    n = net_ids.get(net, -99)
    blk = {}
    for l in LAYERS:
        o = occ[l]
        foreign = (o != 0) & (o != n)
        blk[l] = dilate(foreign, CLR + w / 2 + QE) | edge
    vfor = np.zeros((NY, NX), bool)
    for l in ['F', 'In2', 'B']:
        o = occ[l]
        vfor |= (o != 0) & (o != n)
    vb = dilate(vfor, CLR + VIA_R + QE) | dilate(holes, 0.8) | dilate(edge, VIA_R) | dilate(body_via, VIA_R + 0.1)
    return blk, vb


def own_cells(ids):
    s = {l: set() for l in LAYERS}
    for i in ids:
        for l, jj, ii in item_cells.get(i, []):
            if l in s:
                s[l].update(zip(jj.tolist(), ii.tolist()))
    return s


MOVES = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
         (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]


def astar(src, dst, blk, vb, window, cheap=None):
    j0, j1, i0, i1 = window
    targets = dst
    tl = [(j, i) for l in LAYERS for j, i in targets[l]]
    if not tl:
        return None
    tj = np.array([t[0] for t in tl]); ti = np.array([t[1] for t in tl])

    def h(j, i):
        return float(np.min(np.hypot(tj - j, ti - i))) * 0.999

    # coarse heuristic: distance to target bbox is cheap & admissible
    tj0, tj1, ti0, ti1 = tj.min(), tj.max(), ti.min(), ti.max()

    def hb(j, i):
        dj = max(tj0 - j, 0, j - tj1); di = max(ti0 - i, 0, i - ti1)
        return math.hypot(dj, di)

    openl = []
    g = {}
    prev = {}
    for li, l in enumerate(LAYERS):
        for (j, i) in src[l]:
            st = (li, j, i, -1)
            g[st] = 0.0
            heapq.heappush(openl, (hb(j, i), 0.0, st))
    tset = [targets[l] for l in LAYERS]
    n_exp = 0
    while openl:
        f, gc, st = heapq.heappop(openl)
        if g.get(st, 1e18) < gc:
            continue
        li, j, i, d = st
        if (j, i) in tset[li] and gc > 0:
            path = [st]
            while st in prev:
                st = prev[st]; path.append(st)
            return path[::-1]
        n_exp += 1
        if n_exp > int(os.environ.get("MAXEXP", "600000")):
            return None
        cands = []
        for di, (dj, dii, c) in enumerate(MOVES):
            nj, ni = j + dj, i + dii
            if not (j0 <= nj < j1 and i0 <= ni < i1):
                continue
            if blk[LAYERS[li]][nj, ni] and (nj, ni) not in tset[li]:
                continue
            if c > 1.2 and (blk[LAYERS[li]][j, ni] or blk[LAYERS[li]][nj, i]) and (nj, ni) not in tset[li]:
                continue
            turn = 0.0 if d in (-1, di) else 0.3
            if cheap is not None and cheap[li][nj, ni]:
                c *= 0.55
            cands.append(((li, nj, ni, di), c + turn))
        if not vb[j, i]:
            ol = 1 - li
            if not blk[LAYERS[ol]][j, i] or (j, i) in tset[ol]:
                cands.append(((ol, j, i, -1), VIA_COST))
        for ns, c in cands:
            ng = gc + c
            if ng < g.get(ns, 1e18):
                g[ns] = ng; prev[ns] = st
                heapq.heappush(openl, (ng + hb(ns[1], ns[2]), ng, ns))
    return None


def to_geometry(path):
    """cell path -> list of (layer, [pts]) and via points; collinear runs merged."""
    tracks, vias = [], []
    cur_l = path[0][0]; pts = [path[0][1:3]]
    for a, b in zip(path, path[1:]):
        if b[0] != a[0]:
            vias.append(a[1:3])
            tracks.append((LAYERS[cur_l], pts)); cur_l = b[0]; pts = [b[1:3]]
            continue
        pts.append(b[1:3])
    tracks.append((LAYERS[cur_l], pts))
    out = []
    for l, p in tracks:
        if len(p) < 2:
            continue
        simp = [p[0]]
        for k_ in range(1, len(p) - 1):
            d1 = (p[k_][0] - simp[-1][0], p[k_][1] - simp[-1][1])
            d2 = (p[k_ + 1][0] - p[k_][0], p[k_ + 1][1] - p[k_][1])
            if d1[0] * d2[1] - d1[1] * d2[0] != 0:
                simp.append(p[k_])
        simp.append(p[-1])
        out.append((l, [[(i + 0.5) * G, (j + 0.5) * G] for j, i in simp]))
    return out, [[(i + 0.5) * G, (j + 0.5) * G] for j, i in vias]


ROUTED = {}
OPT = {k_: set(os.environ.get(k_, '').split(',')) - {''} for k_ in ('NOVIA', 'FONLY')}
HUG = dict(kv.split(':') for kv in os.environ.get('HUG', '').split(',') if kv)
FAT = {kv.split(':')[0]: float(kv.split(':')[1]) for kv in os.environ.get('FAT', '').split(',') if kv}
FATNEAR = float(os.environ.get('FATNEAR', '1.5'))


def route_net(net, info, width):
    clusters = [own_cells(c) for c in info['clusters']]
    blk, vb = blocked_for(net, width)
    if net in FAT:
        # reserve room for a partner trace except close to the pads
        bfat, _ = blocked_for(net, FAT[net])
        endm = np.zeros((NY, NX), bool)
        for c in clusters:
            for l in LAYERS:
                for j, i in c[l]:
                    endm[j, i] = True
        near = dilate(endm, FATNEAR)
        for l in LAYERS:
            blk[l] = np.where(near, blk[l], bfat[l])
    if net in OPT['NOVIA'] or net in OPT['FONLY']:
        vb = np.ones_like(vb)
    if net in OPT['FONLY']:
        blk['B'] = np.ones_like(blk['B'])
    cheap = None
    if net in HUG and HUG[net] in ROUTED:
        cheap = []
        pitch = width + 0.2
        for li in range(len(LAYERS)):
            pm = np.zeros((NY, NX), bool)
            for l2, j, i in ROUTED[HUG[net]]:
                if l2 == li:
                    pm[j, i] = True
            cheap.append(dilate(pm, pitch + 0.08) & ~dilate(pm, pitch - 0.08))
    results = []
    merged = clusters[0]
    rest = clusters[1:]
    while rest:
        dst = {l: set().union(*[c[l] for c in rest]) for l in LAYERS}
        allc = [p for l in LAYERS for p in merged[l] | dst[l]]
        jj = [p[0] for p in allc]; ii = [p[1] for p in allc]
        path = None
        for m in (int(6 / G), int(15 / G), 100000):
            win = (max(min(jj) - m, 0), min(max(jj) + m, NY), max(min(ii) - m, 0), min(max(ii) + m, NX))
            path = astar(merged, dst, blk, vb, win, cheap)
            if path:
                break
        if not path:
            return results, False
        end = path[-1]
        hit = next(c for c in rest if (end[1], end[2]) in c[LAYERS[end[0]]])
        rest.remove(hit)
        tr, vi = to_geometry(path)
        results.append({'tracks': tr, 'vias': vi})
        for l in LAYERS:
            merged[l] |= hit[l]
        for li, j, i, _ in path:
            merged[LAYERS[li]].add((j, i))
        # newly routed copper becomes an obstacle for later nets
        n = nid(net)
        for li, j, i, _ in path:
            occ[LAYERS[li]][j, i] = n
            ROUTED.setdefault(net, []).append((li, j, i))
    return results, True


if __name__ == '__main__':
    only = sys.argv[3].split(',') if len(sys.argv) > 3 and sys.argv[3] else None
    wov = {}
    if len(sys.argv) > 4:
        for kv in sys.argv[4].split(','):
            a, b_ = kv.split('='); wov[a] = float(b_)
    nets = geom['nets']
    order = [n for n in nets if (only is None or n in only)]

    def span(n):
        cs = [own_cells(c) for c in nets[n]['clusters']]
        pts = [p for c in cs for l in LAYERS for p in c[l]]
        return (max(p[0] for p in pts) - min(p[0] for p in pts)) + (max(p[1] for p in pts) - min(p[1] for p in pts)) if pts else 0
    if os.environ.get('ORDER') == 'given':
        order = [n for n in only if n in nets]
    else:
        order.sort(key=span)
    out = {}
    for n in order:
        w = wov.get(n, min(nets[n]['width'], 0.25) if nets[n]['class'] == 'Default' else nets[n]['width'])
        res, ok = route_net(n, nets[n], w)
        out[n] = {'width': w, 'routes': res, 'complete': ok}
        print(f"{n:20s} w={w} {'OK ' if ok else 'FAIL'} {len(res)}/{len(nets[n]['clusters'])-1}", flush=True)
    json.dump(out, open(sys.argv[2], 'w'))
