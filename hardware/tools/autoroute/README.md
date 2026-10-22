# Autoroute tools (radio board)

Routing helpers used for the radio PCB. They **propose** copper; every segment and
via is re-checked in pcbnew at 0.152 mm before anything is kept, and the board is
only written through `hardware/tools/routing_io.save_routed_board`.

Run from the repo root. `AppDir/bin/python3.11` is KiCad's Python (pcbnew);
`prep_pf.py` and `grid_route.py` need numpy (any Python with numpy, run with `-I`).

## Negotiated-congestion router (current work)

```sh
T=hardware/tools/autoroute; W=/some/scratch/dir
g++ -O3 -march=native -fopenmp -std=c++17 -o $W/pfr $T/pf.cpp
AppDir/bin/python3.11 $T/export_pf.py $T $W/geom.json        # rips signal nets in memory
python3-with-numpy -I $T/prep_pf.py $W/geom.json $W/grid.bin $W/names.json
HOT=1 $W/pfr $W/grid.bin $W/names.json $W/routes.json 60 2> $W/pf.log
AppDir/bin/python3.11 $T/apply_pf.py $T $W/routes.json        # dry run: prints count
AppDir/bin/python3.11 $T/apply_pf.py $T $W/routes.json save   # saves only if fewer unconnected
```

- `export_pf.py`: every Default-class net except `PROTECT` (GND, CC/USB power,
  VDD_DAUGHTER, regulator and charger analog nets) is "rippable". Their copper is
  removed in memory, except hand-placed pin escapes listed in `pf/escapes.json`.
  Signals are planned at `SIGW` (default 0.2 mm), and the open power taps at 0.3 mm.
- `prep_pf.py`: rasterises fixed copper onto a 0.05 mm grid (F, B, In2 labels,
  strict-interior cells) plus a via-forbidden mask (hole spacing, J4/U1/SW4 bodies).
- `pf.cpp`: PathFinder over F/B with through vias. It uses fixed-copper blocking from
  a per-net EDT, conflict fields between nets, history costs and growing present
  costs. At the end it drops conflicting nets, then (in the current source) reroutes
  them strictly around the kept copper and emits partial trees. Env: `CLR` (0.17),
  `PF0`, `PFMUL`, `HFAC`, `SEED`, `MAXEXP`, `VERBOSE`, `ONLY=<net>`, `DIAG=1`
  (flood-fill reachability per pad cluster: finds trapped pins), `HOT=1`
  (conflict hotspots every 5 iterations).
- `apply_pf.py`: re-rips the same nets on the native board and adds complete new
  nets all-or-nothing. It then restores each other net's original copper where it
  still clears, falling back to partial new routes.

## Targeted rip-up (fourth shift)

```sh
K=10 ITERS=40 hardware/tools/autoroute/targeted_multi.sh $W python3-with-numpy [net ...]
GROUP=1 hardware/tools/autoroute/targeted_multi.sh $W python3-with-numpy NET_A NET_B
```

For each open net (default: every open net), routes it alone with all signal
nets lifted (`ONLY=net`), asks `crossings.py` which existing rippable nets that
path collides with, rips just that set (`RIP_NETS`) and renegotiates. K
variants (seeds/PFMUL/HFAC) run in parallel as dry runs; the best saves only if
the unconnected count drops. `GROUP=1` merges the crossing sets of all listed
nets into one rip-up. `targeted.sh` is the sequential single-variant version.
Do not edit these scripts while one is running (bash reads them as it goes).

## Older sequential tools

`grid_route.py` (Python A*, one net at a time), `export_geom.py` and
`apply_routes.py`: the random-net-order passes used earlier on 2026-10-20.
`rt.py` has the shared pcbnew helpers (`Router.seg_ok/via_ok`, `rip`, `gaps`).

## Incremental routing and exact-check diagnostics

Set `RIP_NETS=''` for both export and apply to preserve existing copper and add
routes only. A comma-separated `RIP_NETS` list limits rip-up to those signal
nets; unknown or protected names are rejected. Leave it unset for the original
full signal rip-up behavior. Use the same value at export and application.
Re-export after saving a batch; older proposals can collide with newly saved
copper and must pass the exact check again.

The exact checker now reports the blocking pad/track/via and its location.
The raster model blocks pads with no net (including mounting holes), uses
actual off-grid hole coordinates, includes diagonal quantization uncertainty,
and accounts for the widest proposed trace in dynamic via/track clearance.
The geometric model still proposes candidates: full native-board DRC remains
required after every accepted batch.

Run the focused geometry regression with the same NumPy Python used for prep:

```sh
python3-with-numpy -I hardware/tools/autoroute/test_geometry.py
```

It verifies that unassigned pads block routing, named pads remain valid
terminals, and every grid point violating off-grid hole spacing is forbidden.
