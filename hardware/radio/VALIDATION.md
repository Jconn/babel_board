# Revision D design checks — 2026-10-19

This is a schematic review result, not a fabrication release or hardware test.

- KiCad 10.0.7 radio ERC: zero violations, nine sheets.
- Exported radio netlist: 154 components, 484 connected pads, 47 intentional NCs.
  Independent critical-pin checks and the existing daughter J1 contract pass.
- Charging audit: current/voltage margins and static temperature corners pass.
  Thermistor beta spread is an explicit assumption; see the script and README.
- Power-policy model: all 320 steady-state cases pass. This does not simulate
  startup races, analog transients, leakage or component failure modes.
- Footprints: all 154 assigned library footprints exist with matching pad-number
  sets. No blank radio footprints. Custom RNM, RGT-B and Samtec patterns have
  been screened against manufacturer dimensions and parsed by native KiCad.
  Critical dimensions are independently checked; physical mating is not tested.
- Generator repeatability: checked schematic/library/BOM/manifests/GPIO map and
  shared footprint files on both boards are byte-identical after regeneration.
- IR daughter ERC rerun: zero violations.
- Native PCB seeds: all 154 radio / 19 daughter electrical footprints match
  exported pad nets, values, FPIDs, DNP flags and schematic UUID paths. Four/two
  layers respectively; zero tracks. Interface anchors and mounting holes exist;
  remaining components are staged outside the outlines.
- Seed DRC: radio has 383 unconnected items and 9 warnings (7 library-copy
  mismatch warnings, 2 module silkscreen/edge warnings). Daughter has 43
  unconnected items and 2 card-reference silkscreen/mask warnings. No clearance,
  shorting, drill-range or keepout errors remain. These are NOT DRC-clean boards.
  Reports are retained as layout-entry-drc.json in each project. Library-copy
  warnings need investigation during layout; they have not been waived.
- Radio/daughter PCB exports and the new test-point sheet were visually reviewed.
  Keyed-carrier SCAD is not rendered/printed; its nominal clearance arithmetic
  passes, but that is not a full 3D collision or tolerance analysis.

Charging remains disabled by R90 DNP. Before enabling it, qualify the actual
pack/NTC curve, hot/cold and broken-sensor behavior, startup and source removal,
timer expiry, thermal behavior and charge completion. Layout-entry inputs are
recorded in ../LAYOUT-PLAN.md. Placement/routing can begin; fabrication still
requires completed DRC, physical fit and supplier process approval. Physical RF,
USB and hot-swap tests require
assembled boards. Turn power OFF before prototype module changes.

Run the commands in README.md to reproduce design checks. FEATURES.md is the
capability contract; DISPLAY-INTEGRATION.md specifies the custom OLED cable.

Additional native-board audit:
`AppDir/bin/python3.11 hardware/tools/check_layout_seeds.py` from the repository
root. This intentionally asserts zero tracks and describes the initial seeds;
update its scope once routing starts. Do not regenerate/replace boards after
manual placement. The schematic generators do not update PCB connectivity.
