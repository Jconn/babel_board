# Prototype layout entry contract — 2026-10-19

This permits **PCB placement and routing work**, not manufacture, charging or
hot-swap operation. Hardware tests cannot be completed before layout exists.
The initial operating restriction remains power OFF for module changes and
R90 absent until the charger has passed bench qualification.

## Frozen PCB interfaces

| Item | Radio | IR daughter |
| --- | --- | --- |
| Outline | 60 x 80 mm rectangle | 30 x 35 mm body/tongue envelope |
| Layers/thickness | Four copper layers, 1.60 mm | Two copper layers, 1.57 +/-0.15 mm |
| Stack intent | Components/signals, solid GND, power/slow signals, signals/GND | Components/signals, mostly solid GND |
| Daughter connection | MEC1 NP socket at (30,7), vertical | 11.77 mm tongue, tip at (20,45) in seed |
| Mechanical datum | Top-left outline corner (0,0), top copper z=0 | Tongue tip centered x=0, upward distance z |
| Assembly | Single-sided electrical components initially | Sensor and electronics front; carrier behind |

Do not silently move locked interface anchors. Unplaced circuit components are
staged outside the board; these files are starting points, not a completed layout.
`tools/build_layout_seeds.py` refuses to overwrite a board by default. Its explicit
replacement flag is only for these generated seeds, NEVER after manual layout.

## Mechanical stack and antenna

OLED breakout occupies x12.22..47.78, y15..61.99, on 14 mm female/female M2
standoffs. Hole centers are in DISPLAY-INTEGRATION.md and the native board.
This deliberately leaves connector/cable room. Use short screws from below the
host into those standoffs; no metal may project below z=-3.5 mm in the pack area.

Battery occupies x12.75..47.25, y10..63 **below** the board. Reserve 6 mm pack
thickness plus clearance, top at z=-6 and bottom no lower than z=-12. Use a rigid
insulating tray/barrier at z=-5.5..-4.5, so the pouch cannot reach solder joints,
standoff screws or vias. No bottom components in this region. Provide strain
relief and extra room at the pack lead exit; never clamp or compress the pouch.
The resulting stack is a prototype envelope, not a measured enclosure drawing.

WROOM origin (30,72.25), rotated 180 degrees, puts its antenna at the lower end
and overhanging the PCB by about 5 mm. Native keepout covers x6..54, y79..100
on all four copper layers. No ground plane, traces, vias, battery, display, metal
fasteners or cable crossing in this region. OLED ends at y61.99 and battery at
y63, leaving more than 15 mm to the antenna region. Plastic housing and the user's
hand still need RF testing. Follow Espressif's module keepout, not a chip-RF layout.

## Carrier and retention

`mechanical/daughter_carrier.scad` defines the host boot and daughter carrier.
Host boot envelope is x9..51, y1..13 on the radio, mounted at (12,7)/(48,7).
The carrier key leads the daughter tip by 0.5 mm and enters a boot key slot before
the tip reaches the socket. The boot has mirrored slots on both faces: the J1
pinout is symmetric, so the card may go in either way round. Fully inserted, the
key bottoms 0.491 mm above the host, not on the PCB.
Carrier mounting holes are asymmetrical: (-10,23) and (10,27) relative to the
card tip, preventing the carrier being attached reversed. No copper near them.
Use the M2 nylon clamp screw on the key's side for prototype retention; select its length so it
only bears on the plastic key, never the daughter PCB. The connector sets seating
depth; the boot is not a depth stop. Print a mating coupon before fabrication to
check tolerances, full seating in both orientations and clamp retention.
No enclosure/guide material may obstruct the front 50-degree sensor field of view.

## Placement and routing order

1. Keep the locked mechanical interfaces, antenna keepout and mounting clearances.
   Fit a printable 1:1 mechanical check before completing dense placement.
2. USB J4 -> F1 -> D3 return loop -> U18 -> U3: at left edge. Place CC controller,
   USB data ESD and U19 close to J4. Keep ESD returns short, direct to ground vias.
   Do not route unprotected VBUS alongside the protected side. F1 is not a surge
   clamp or a guarantee that a current-limited supply clears a sustained fault.
3. Charger U3 on left side, away from sensor, battery and OLED; solid thermal GND
   connections and stitched copper to inner GND. EP17 is GND, 1.6 mm square.
   Use filled/tented thermal vias or outboard vias with short copper; no open
   via-in-paste unless the assembler approves the solder-loss risk.
4. U4/L1/C11/C15 at right-center. Place small 0603 C11/C15 immediately at VIN/VOUT
   and PGND; place the 0805 bulk bank next. Minimize both switch-node loops;
   no signal routes beneath L1/L2 switch copper. Feedback away from switching
   nodes, Kelvin-sensed from the output capacitor. Add multiple ground vias.
5. U11 current limiter and U12..U14 isolation near J1, followed by connector-side
   ESD. Pull-ups reference switched daughter power. Route NVM and sensor I2C
   separately; preserve host TX -> daughter RX interpretation.
6. Bring-up test pads must remain probe-accessible after assembly. Place TP1/TP7
   ground beside supply probes; avoid USB data and switching-node probe stubs.
7. Daughter sensor at (20,16), only its decoupler nearby. Put EEPROM/pull-ups near
   the connector side. No charger/regulator heat source near the sensor, no
   unnecessary copper thermal bridge through its optical end.

## Electrical routing constraints

- General rules: 0.15 mm minimum track/clearance; 0.3 mm finished routing-via drill,
  0.6 mm diameter; copper-to-edge 0.40 mm (raised from 0.30 for OSH Park's 15 mil keepout) except the
  documented card fingers.
  WROOM library thermal holes use 0.20 mm drills; confirm filled/tented handling
  with assembly. Radio minimum hole-to-copper clearance is 0.15 mm, accommodating
  the USB connector's 0.194 mm nominal pad-to-alignment-hole clearance.
  Fine-pitch package escape must be reviewed individually, not globally waived.
- Main supply trunks start at 0.8 mm or pours; daughter 3.3 V at least 0.3 mm.
  Verify voltage drop/thermal rise with actual copper weight and path length.
- Radio baseline: JLC04161H-7628, 1.6 mm nominal, 35 um outer / 15.2 um inner
  copper, 0.2104 mm L1-L2 dielectric (Dk 4.4), 1.065 mm core (Dk 4.6), symmetric
  bottom dielectric. L2 is uninterrupted GND under USB. This stack is encoded in
  the PCB. Start USB at 0.30 mm width / 0.15 mm gap, 90-ohm differential target;
  these are routing reservations, NOT a certified field-solver result. Confirm
  the finished width with the fabricator's impedance calculation before release;
  allow +/-0.05 mm width adjustment in the reserved corridor. Include soldermask
  (Dk 3.8, 0.01524 mm over trace / 0.03048 mm between traces). No USB routing on
  inner layers. Full-speed pair: aim <50 mm total, <1 mm within-pair mismatch,
  no branches/stubs, short narrow escapes only, avoid layer changes. P/N suffixes
  in current net names are not KiCad automatic-pair names; use manual matched
  routing or explicit pair naming during layout, preserving schematic parity.
- Start I2C at 100 kHz (the connector is I2C plus IRQ only). The 400 kHz I2C option
  requires a measured rise-time/capacitance budget (about 75 pF for 4.7k pull-ups).
- USB design allocation: 750 mA aggregate 3.3 V (500 host, 120 OLED, 100 daughter,
  30 logic), subject to measurement. Charging may reduce through DPPM.
  Battery qualification envelope: 600 mA aggregate, including peaks; firmware
  must dim/schedule display and radio work to fit the measured allocation.
  At 3.0 V pack cutoff, allowing 0.2 V power-path loss and 80% conversion
  efficiency, this is 884 mA plus housekeeping: below a conservative 950 mA
  pack limit (1C of minimum capacity). The pack specifies 1C for BOTH pulse and
  continuous discharge; its 3.1..6 A PCM trip is not an acceptable operating
  limit. Neither firmware enforcement nor efficiency is proven. Begin on a
  current-limited bench supply; qualify peaks before battery operation. Battery
  shutdown margin must avoid routine reliance on the pack's 3.0 V PCM cutoff.

## Gates after layout, not reasons to defer placement

Before fabrication: full-board DRC/netlist parity, routing/thermal/USB review,
exact BOM procurement, mechanical coupon, stencil/paste approval. Daughter
prototypes use the standard ENIG build below. Before enabling charging: NTC curve,
open/short faults, temperature corners, timer completion and thermal tests.
Before hot swapping: retention/contact sequencing, bounce, partial insertion,
back-powering and fault recovery tests. WAMR EEPROM capacity and BLE/display
firmware remain runtime qualification work; they are not demonstrated hardware.

## Fabrication sourcing

Radio stack source: [JLCPCB stackups](https://jlcpcb.com/impedance).
**Daughter prototypes (decided 2026-10-19): standard ENIG, no bevel.** Order an
ordinary two-layer board: 1.6 mm FR4, ENIG finish (not HASL, whose uneven solder
on the fingers adds thickness and wear), no gold-finger or bevel options. Keep
the finger geometry unchanged. After delivery:
- Measure the thickness at the tongue. Samtec's mating range is 1.42..1.72 mm,
  and a 1.6 mm +/-10% board can reach 1.76 mm, so reject anything over 1.72 mm.
- Lightly hand-chamfer and deburr the tip edge with a fine file or abrasive
  paper. The fingers start 1.05 mm back from the tip, so a chamfer of up to
  about 0.8 mm leaves the copper untouched. Clean off the dust before mating.
- Expect a limited number of insertions: the thin, soft ENIG gold wears through
  to nickel. Inspect the fingers for wear and replace a worn daughter rather
  than fighting intermittent contacts. Power stays OFF for every swap.

**Deferred release spec (not needed for prototypes).** Samtec's mating card is
30 microinch hard gold, 30 +/-5 degree bevel to a 0.61 mm tip, 1.57 +/-0.15 mm.
Standard bevelling needs a >=30 mm finger edge
([PCBWay](https://www.pcbway.com/blog/Engineering_Technical/Understanding_PCB_Manufacturing__Hard_Gold_Plating.html)),
so the 11.77 mm tongue would need a special-process quote with Samtec's drawing.
Revisit this only if Babel moves toward a product.
