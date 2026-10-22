# Layout shift summary — 2026-10-20

> **Fourth shift — current checkpoint:** radio **20 -> 6 unconnected**; DRC
> otherwise only 283 silkscreen warnings (the dangling H_NVM_SCL escape via is
> gone). Daughter stays at zero. No footprint moved, no outline growth. Key
> change: the VBAT 1.2 mm B.Cu run above the module moved to In2, which opened
> B.Cu out of U1; new targeted rip-up scripts did the rest. Remaining LCD_DC,
> LCD_MOSI, PORT_FAULT_N (2), PWR_REQ, USB_ALLOW and next steps are in
> [hardware/ROUTING.md](hardware/ROUTING.md#fourth-shift-2026-1020-21).
> Nothing from the third or fourth shift is committed yet.

> **Third shift (historical):** radio **46 -> 20 unconnected**, with
> 283 silkscreen warnings and one reserved H_NVM_SCL dangling escape via.
> Daughter stays at zero unconnected. No outline growth or footprint movement.
> Corrected four router geometry assumptions, added rejection diagnostics and
> regression coverage, and completed additional power/control/signal routing.
> All saved candidates passed exact checks and native DRC; remaining work and
> the local C2/C3 supply-feed change are detailed in
> [hardware/ROUTING.md](hardware/ROUTING.md#third-shift-2026-10-20-historical).
> Start from the native boards and re-export routing geometry. Expansion is
> authorized if necessary. Earlier shift notes below are historical.

> **Next-shift starting checkpoint:** reviewed the second-shift handoff. All
> existing board, router and documentation changes are already committed in
> `3cab2bc` (radio: 46 unconnected; daughter: 0). Generated Python caches are
> excluded from version control. Continue with exact-check rejection diagnosis
> and the rebuilt router’s strict reroute phase, as ordered in ROUTING.md.
> Keep subsequent routing changes separate for the end-of-shift commit.

> **Second shift update:** radio unconnected 224 -> 46; DRC otherwise only
> silkscreen (289 warnings). The V3V3 In2 plane, V3V3_CC, the USB LINK/MCU
> pairs and the USB-C fan-out are routed (U2, U19 and C104 moved; R8/R9
> rotated, then R8/R9 moved to free U1.12). Daughter nets are now unprefixed
> (`GND`, not `/GND`). A rip-up/reroute router (`hardware/tools/autoroute`) is
> built but not yet applied; its handoff list is in
> [hardware/ROUTING.md](hardware/ROUTING.md) "Rip-up and reroute". The
> sections below record the first shift.

## Saved result

The daughter board now has **zero unconnected items**. Its EEPROM, sensor buses,
address strap, debug pads and ground returns are routed. DRC reports only 26
silkscreen warnings (19 over copper, 7 overlaps). The board outline and component
placement were not enlarged or moved in this continuation.

Radio unconnected items dropped **244 → 224** during this continuation. Added
OLED supply routing, port-switch input/bypass routing, the switched daughter
supply to both connector contacts and all eight pull-ups, TP14 and the port
current-limit resistor. Radio DRC reports 287 silkscreen warnings and the 224
remaining connections, with no other violations. There are 344 segments/158
vias on radio and 140 segments/36 vias on daughter.

Earlier in the routing shift, the regulator feedback/bulk-capacitor network,
USB power paths, battery/system/3.3 V trunks and radio ground stitching were
added. Those updates were already saved when this continuation resumed; the
old ROUTING.md still described the initial 41-segment radio pass and is now
updated to the actual state.

## Checks and problems resolved

- Repaired the daughter EEPROM clearance conflict and removed a ground strap
  whose copper had been reassigned to NVM_SDA across a crossing.
- Added explicit copper UUID/net checks during routing saves. New persistent
  helper `hardware/tools/routing_io.py` also detects project-rule changes and
  rolls back the PCB/project together. Regression checks verify a normal save
  and byte-for-byte rollback after injected copper-net and project corruption.
- Restored the three added radio supply nets to the Power net class. The new
  project-settings guard caught the missing assignments.
- Electrical/netlist, footprint, charge-limit, 320-case power-policy,
  PCB/schematic parity, frozen-anchor, exclusion-zone and placement checks pass.
  Five negative layout guard tests pass. Current copper previews were exported
  and visually inspected; silkscreen is visibly crowded and remains unfinished.

## Resume here

Use the native boards, not seed generators or retired placement tables. Read
[hardware/ROUTING.md](hardware/ROUTING.md) for current reports/previews and editing
precautions. The temporary routing scripts are not required to resume and must
not be rerun over newer work. All changes remain uncommitted.

Next priority is remaining radio power distribution (29 V3V3 gaps, 17 V3V3_CC),
then enable/status/USB policy/charge controls and USB/host/sensor/display signals.
There are no radio GND gaps in the current report. Review charger thermal paths,
power widths and sensor thermal isolation before release. Finish silkscreen and
physical mating/assembly review, then obtain complete DRC/ERC. R90 remains DNP;
no charging qualification or fabrication release is implied.

The requested 5%-remaining-compute-credit threshold is not observable in this
session. This is a verified checkpoint summary, not a claim that the threshold
was reached.
