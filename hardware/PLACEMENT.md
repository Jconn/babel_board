# Placement pass — 2026-10-19

**Later update: debug access was expanded and radio routing has started with
user authorization. See [ROUTING.md](ROUTING.md) for current status. The text
and placement exports below describe the earlier unrouted placement. Do not
reapply the placement table to the routed radio board.**

Both boards now have every electrical component placed inside its outline,
top side only, with **no tracks, vias or pours**. This is a placement for
review before routing, not a routed or fabrication-ready layout.

Source of truth until routing starts: `tools/place_boards.py` (one table per
board). Re-apply with `AppDir/bin/python3.11 hardware/tools/place_boards.py radio`
(or `daughter`); it refuses to run once a board has tracks. After the first
track is laid, KiCad becomes the source of truth and the script retires.
Pre-placement seeds are archived in `archive/layout-seeds-pre-placement/`.

Reviews: `radio/layout-placement.svg`, `radio/layout-placement-ratsnest.png`
(courtyards, pads coloured GND/other, ratsnest without GND),
`ir-daughter/layout-placement.svg`, and `*/layout-placement-drc.json`.

## Radio block map (x, y in mm from top-left)

| Block | Where | Notes |
| --- | --- | --- |
| Daughter ESD U30..U36 | row y=15, x 21..40 | Directly under J1 contact columns, just outside the boot envelope (y>13). |
| Daughter pull-ups R31..R38 | x 17..24, y 16.5..22.7 | Daughter side, clear of the H7 standoff. |
| Isolation U12 / U13 / U14 | (30.1,20.3) / (39.3,24.1) / (51.5,21.5), rot 90 | B (daughter) pins face J1, A (host) pins face U1. U13 is lowered so it clears the H8 standoff. |
| Daughter supply U11 block | top-left, x 0..10, y 15..22 | VDD_DAUGHTER reaches J1 pins 3/4 on an inner layer (~20 mm, 100 mA). TP14/TP15 are beside it. |
| Port enable logic U5..U10, R21..R28 | x 25..46, y 29..41 | Under OLED; slow signals. |
| USB entry, CC, data path | beside J4, x 7.3..26, y 32..53 | F1 next to VBUS pins, D3 after the fuse, U2 ESD on the D+/D- pins, then U19. U15/U24 are at the CC end. |
| Charger U3 | (22,51) | See deviation 1. C6 (VBAT) left, C7 (SYS_RAW) right, C5 (IN) above. |
| Charge guard U20/U22/U23 | x 28..44, y 42..53 | U21 battery-OK block is right of U1 at x 44..51, y 62..78. |
| Regulator U4/L1 | (49,46) / (53.2,46) | C11/C15 (0603) sit on the VIN/VOUT pins. Input bulk above, output bulk below, FB divider left. |
| Host passives | right of U1, x 40..43 | R8/R9 by the USB pins; R1/C1 (EN), C2/C3 (3V3) by pins 2..3; R120..R123 above the U1 top row. |
| J3 UART | pin 1 at (12.2,64), vertical | Left of U1, clear of SW1/SW2 and H9. |
| Test pads | left x<8, y 51..61 (10); top-left (2); right x=57.6 (4) | All outside the OLED footprint, so they're probe-reachable with the display fitted. |

## Deviations from LAYOUT-PLAN.md (please review)

1. **Charger is not at the left edge.** The strip between J4 and the OLED edge
   is about 5 mm wide, and the USB protection/CC/data parts fill it. U3 sits at
   (22,51), under the OLED footprint (14 mm air gap above) and above the battery
   region (on the far side of the board). Linear charge loss is ~0.25 W at
   166 mA. DPPM/power-path loss at full system load could approach 0.5 W.
   Stitch the EP to inner GND generously. Measure board temperature over U3
   and the pack during charge qualification.
2. **U11 daughter power switch is top-left, not right beside J1.** The boot
   envelope blocks parts near J1. The VDD_DAUGHTER run must be an inner-layer
   trace or pour, at least 0.3 mm wide.
3. **U21 battery-OK comparator sits beside the WROOM module side** (not in the
   antenna keepout). VBAT reaches it from J5 over ~30 mm. Treat this as a
   high-impedance sense line: route on an inner layer away from L1 and the
   module RF edge.
4. **PACK_NTC also runs ~15 mm from J5 into the guard.** Keep it away from the
   L1/U4 switch nodes.

## Checks run on the placed boards

- `check_layout_seeds.py`: pad/net/value/FPID/DNP/UUID parity PASS (both).
- `check_placement.py` (new): boot/antenna envelopes, r = 2.6 mm OLED standoff
  and corner-screw bodies, test-pad probe access, daughter sensor-zone
  exclusivity and carrier-hole clearance, single-sided assembly, and
  through-hole pad mask openings. PASS.
- KiCad DRC, radio: **0 errors** of type clearance, short, courtyard or
  library mismatch. Remaining: 383 unconnected (expected before routing) and
  silkscreen-only items (92 overlap, 161 over copper, 5 edge). Daughter:
  43 unconnected; silkscreen only otherwise.

## Defect found and fixed: through-hole pads lacked soldermask openings

The seven "library mismatch" warnings in the seed were real. 39 through-hole
pads (J2, J3, J4 shell, J5, SW4, J1/SW4 NPTH, WROOM thermal vias) and all
mounting holes had lost their `*.Mask` layers, so pins would have been
covered by soldermask. Pad layer sets were restored from the library copies,
and the library mismatch warnings are gone. The WROOM 0.2 mm thermal vias
correctly stay bottom-tented, as the library specifies. A fresh load/save
does not reproduce the loss, so the cause (some earlier processing step)
is not identified. `check_placement.py` now fails if it recurs.

## Next: routing order

1. Pour In1 as solid GND and keep it unbroken under USB and the regulator.
2. USB: J4 → F1 → D3, U18, U3 power path on F.Cu/In2 with wide copper; the
   D3 GND return goes straight to In1 vias.
3. Regulator hot loops (C11/U4/L1/C15) on F.Cu only, PGND vias at C11, C15
   and U4 pin 10. Kelvin FB taken from C15.
4. USB D+/D-: U2 → U19 → R8/R9 → U1, F.Cu only, 0.30/0.15 reservation, about
   40 mm (within the <50 mm budget).
5. J1 top-row contacts: escape with vias just above each pad (1 mm pitch
   allows a 0.6 mm via, 0.43 mm from the pad and inside the 0.3 mm edge
   rule), then run under the connector on In2/B.Cu to the ESD row.
6. Everything else, then silkscreen cleanup (reference size/placement,
   module-edge and card labels) once vias exist.
