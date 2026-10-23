# OSH Park bare-board order (2026-10-21)

Upload-ready Gerber zips, regenerated from the native boards on 2026-10-22
(reversible connector). Bare boards only: no assembly, no stencil.

The daughter zip is **rev C**. Rev B (one-way pinout) was ordered 2026-10-21 from
the commit d1dbffc files; see `../../ir-daughter/README.md` for how the two differ
and the firmware rule for using rev B cards in the current radio. Rev C also has
2 mm rounded body corners (outline and bottom pour changed); mask, drill and the
rest of the copper are unchanged.

The IR TH daughter (`../../ir-th-daughter`) is a separate hand-solder board with
the same host interface and outline; it uses the same OSH Park rules (DRC 0/0)
and adds 0.7 mm plated holes for the TO-39 sensor leads.

| File | Board | OSH Park service | Size | Order |
| --- | --- | --- | --- | --- |
| `babel-radio-oshpark.zip` | Radio, 4 layers | 4 Layer Prototype | 60 x 80 mm (7.44 sq in) | 6 (multiples of 3) |
| `babel-ir-daughter-revC-oshpark.zip` | IR daughter rev C, 2 layers | 2 Layer Prototype | 30 x 35 mm bounding box | 6 (multiples of 3) |
| `babel-ir-th-daughter-revA-oshpark.zip` | IR TH daughter rev A (hand-solder, MLX90614), 2 layers | 2 Layer Prototype | 30 x 35 mm bounding box | 6 (multiples of 3) |

Zip contents use OSH Park's extensions: GTL/GBL copper, G2L = In1 (GND plane),
G3L = In2 (3.3 V plane), GTS/GBS mask, GTO/GBO silk, GKO outline, XLN drill
(plated and non-plated holes in one file).

## How to order

1. Go to oshpark.com, sign in, and upload each zip separately.
2. Check the layer previews OSH Park generates before checking out: outline,
   card-edge tongue on the daughter, the U1 antenna overhang on the radio
   (the module overhangs the board edge by design; the board itself ends at
   y = 80 mm), and that the radio shows two inner layers.
3. Leave OSH Park's default stack: 1.6 mm, ENIG finish (both services).
   ENIG is what the daughter's card-edge fingers need for prototypes.

## Rule check against OSH Park

Both boards pass KiCad DRC with OSH Park's published minimums applied
(2-layer: 6 mil trace/space, 10 mil drill, 5 mil ring; 4-layer: 5 mil
trace/space, 10 mil drill, 4 mil ring; 15 mil copper-to-edge). To get there:

- Project copper-to-edge rule raised from 0.30 to 0.40 mm on both boards;
  pours refilled. Radio LCD_DC and H_NVM_SDA edge runs moved 0.05 mm inboard.
- Daughter ground-pour clearance raised from 0.15 to 0.16 mm (OSH Park 2-layer
  spacing is 0.1524 mm).
- Radio U1 thermal-via drills enlarged from 0.20 to 0.30 mm on the board copy
  of the module footprint (pads unchanged). Native DRC therefore reports one
  expected `lib_footprint_mismatch` warning on U1. kicad-cli does not apply
  project exclusions to that check, so it stays visible.

## Notes

- The radio stack differs from the JLC04161H-7628 stack the USB widths were
  planned on. The ESP32-S3 USB is full speed (12 Mb/s), which tolerates this.
- Daughter: measure tongue thickness on arrival (reject over 1.72 mm) and
  hand-chamfer the tip; see `../../LAYOUT-PLAN.md`, Fabrication sourcing.
- Open before assembly, not before bare-board ordering: the host boot slot vs
  daughter U2/R1/C3 finding in `../../ROUTING.md`.
