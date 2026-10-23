# Babel IR TH daughter board — revision A (hand-solder)

A version of the [IR daughter](../ir-daughter/README.md) that can be built with
a soldering iron. Same host interface, outline, carrier holes and bench header;
the sensor is a through-hole MLX90614 in a TO-39 can, and every other part has
iron-friendly pads. Routed, DRC 0/0. OSH Park zip:
[`../fab/oshpark/babel-ir-th-daughter-revA-oshpark.zip`](../fab/oshpark/).

Open hardware under **CC BY-SA 3.0**, as an adaptation of the IR daughter; see
[LICENSE](LICENSE).

## What's the same as the IR daughter (rev C)

- J1 card edge, pinout and outline: VDD on contacts 3 and 18, GND on 1, 2, 8,
  19, 20; NVM bus on 5/6/7; sensor bus on 9/10. Reversible in the radio.
- J2 2x4 bench header, same pinout and position (see the IR daughter README).
- 24LC256 EEPROM at 0x50 with WP held high by R1; R2-R5 bus pull-ups DNP.
- 2 mm rounded body corners, chamfered tongue shoulders, carrier holes H1/H2.

## What's different

| | IR daughter rev C | IR TH daughter rev A |
| --- | --- | --- |
| Sensor | MLX90632 (3 x 3 mm leadless, bottom pad) | MLX90614ESF-BCC-000-TU (TO-39, 4 leads) |
| Sensor address | 0x3A | 0x5A (SMBus, 100 kHz max) |
| Accuracy | about ±0.2 °C (medical range) | about ±0.5 °C |
| Field of view | about 50° | 35° |
| Host maths | Host computes temperature from calibration data | Sensor reports object/ambient temperature directly |
| Passives | 0603 | 0805 hand-solder pads |
| ADDR resistor (R6) | Yes | None (address is in sensor EEPROM) |

The host must use an MLX90614 driver for this card; the MLX90632 driver does
not work with it. The sensor bus pins are unchanged, so the radio needs no
change.

## Circuit

- U1: MLX90614ESF-BCC-000-TU, 3 V part (2.6-3.6 V), gradient compensated,
  35° field of view. TO-39 pins (Melexis datasheet rev 021, figure 1): 1 SCL,
  2 SDA, 3 VDD, 4 VSS. The can connects only to VSS internally; nothing else
  touches it. KiCad `TO-39-4` pad numbers match the datasheet with the tab at
  the upper left, as silkscreened.
- C1 100 nF beside U1 pins 3/4 (Melexis recommends 100 nF close to the sensor).
- U2 24LC256 (SOIC-8, 1.27 mm pitch: easy with an iron), C2 at its supply pin,
  C3 1 µF at the port, R1 10k WP pull-up.

## Assembly by hand

1. Start with the smallest parts: U2 (tack one corner pin, check alignment,
   then the rest), then the 0805 passives. Leave R2-R5 off unless this card
   will run on a bench host without pull-ups.
2. U1 last on the front: insert with the tab matching the silk notch, keep
   the can square to the board, solder from the back, and trim the leads flush
   (under 1 mm). The carrier's 10 mm relief hole sits behind the leads.
3. J2 only on bench cards; it does not fit the host boot or carrier.

Power from a current-limited 3.3 V supply first. An I2C scan should show 0x5A
(sensor) and 0x50 (EEPROM).

## Mechanical notes

- The TO-39 can stands about 4-5 mm off the front face (a can, not a flat
  package). Keep it clear of anything in front of the card and keep the 35°
  field of view open.
- Through-hole leads come out on the back inside the carrier's sensor relief.
- The boot-slot interference with U2/R1/C3 noted in `../ROUTING.md` applies to
  this board too (same positions).

## Checks and reproduction

```sh
K=squashfs-root/bin/kicad-cli; D=hardware/ir-th-daughter
python3 $D/tools/generate_schematic.py
$K sch erc $D/babel-ir-th-daughter.kicad_sch --exit-code-violations -o $D/erc-report.txt
$K sch export netlist $D/babel-ir-th-daughter.kicad_sch --format kicadxml -o $D/babel-ir-th-daughter.net.xml
python3 $D/tools/verify_netlist.py
$K pcb drc --schematic-parity --severity-error --severity-warning --format json \
    -o $D/layout-routing-drc.json $D/babel-ir-th-daughter.kicad_pcb
```

DRC: 0 violations, 0 unconnected, with the same two excluded J2 silk-corner
markers as the IR daughter. Schematic parity lists H1/H2 as board-only
footprints (carrier holes), as on the IR daughter.

Not tested: fabrication, hand assembly, sensor readings, carrier fit with the
TO-39 can.
