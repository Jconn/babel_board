# Babel IR daughter board — revision B schematic draft

Adapted from Adafruit's MLX90632 breakout, with attribution and circuit changes
documented in [ADAPTATION.md](ADAPTATION.md).
The whole daughter project is open hardware under **CC BY-SA 3.0**; see [LICENSE](LICENSE). Original Eagle files and license
are retained in `hardware/reference/adafruit-mlx90632`.

Open **babel-ir-daughter.kicad_pro** in KiCad 10, then open its schematic.
For immediate review, use [the PDF](babel-ir-daughter.pdf).
The project-local `Babel_IR.kicad_sym` and `sym-lib-table` travel with the project;
no external symbol library is needed to open or check the schematic.

This is an editable electrical design, not a finished PCB. No routed board,
Gerbers, or fabrication release is included.

The [native PCB seed](babel-ir-daughter.kicad_pcb) is ready for placement/routing
under the [shared layout contract](../LAYOUT-PLAN.md): 30 x 35 mm envelope,
two layers, card-edge tongue. Prototypes are a standard 1.6 mm ENIG build with
no bevel; hand-chamfer the tip and check the thickness (see LAYOUT-PLAN.md).
The hard-gold/bevel spec is deferred. Sensor, card edge and asymmetric carrier
holes are anchored.

## Circuit

- U1: MLX90632SLD-DCB-000-RE, the 3.3 V I/O variant used by Adafruit.
  Pin 1 SDA, 2 supply, 3 ground, 4 SCL, 5 ADDR, 6 exposed ground pad.
  R6 pulls ADDR low through 10k for address 0x3A. Temperature calculations run
  in the host driver. The sensor bus and calibration algorithm differ from rev A.
- U2: 24LC256-I/SN, provisional 32 KiB driver storage. A0–A2 low select 0x50;
  pins 6/5 are NVM SCL/SDA, 7 is WP, 8 supply, 4 ground.
- The sensor and EEPROM use physically separate buses. R1 holds WP high by
  default; the host pulls it low only during programming.
- C1/C2 are local 100 nF bypass capacitors, C3 is 1 uF at the port. Use ceramic
  capacitors with adequate voltage rating; exact purchasing parts remain open.
- R2–R5 are **not populated**. The normal host supplies connector-side bus
  pull-ups to switched daughter power. These pads allow bench pull-ups if needed.
- J2 is a 2x4 0.1 in through-hole bench header (replaced the seven test pads).
  It brings out power, ground, both buses and write protection, so a dev board can
  drive the daughter with Dupont jumpers. See [Bench header](#bench-header-j2).
- J1 pin 8 is the host's active-low presence signal, grounded on the daughter.
  VDD is on contacts 3 and 18 (tied), so either insertion direction powers it; the
  host mirrors contact n onto 21-n. Contact 4 (IRQ) and 11-17 are no-connect.

Pin assignments checked against the
[Melexis datasheet, revision 13](https://www.melexis.com/-/media/files/documents/datasheets/mlx90632-datasheet-melexis.pdf)
and [Microchip DS20001203Y](https://ww1.microchip.com/downloads/aemDocuments/documents/MPD/ProductDocuments/DataSheets/24AA256-24LC256-24FC256-256K-I2C-Serial-EEPROM-DS20001203.pdf).
Custom schematic symbols are functional representations, not footprint drawings.

## Bench header (J2)

For interim bring-up without the radio, wire J2 to any 3.3 V microcontroller
board (for example an ESP32 dev board). Pin 1 is bottom-left, marked by the silk
corner; the pinout is also printed on the board beside the header.

| Pin | Signal | Pin | Signal |
| --- | --- | --- | --- |
| 1 | GND | 2 | VDD_DAUGHTER, 3.3 V in |
| 3 | SENSOR_SCL (S.SCL) | 4 | SENSOR_SDA (S.SDA) |
| 5 | NVM_SCL (E.SCL) | 6 | NVM_SDA (E.SDA) |
| 7 | NVM_WP (E.WP) | 8 | GND (spare) |

Pin 2 takes 3.3 V only, with no protection on the daughter: power everything off
before connecting or disconnecting. The buses have no pull-ups unless R2-R5
(4.7k) are fitted or the host provides them; the ESP32's internal ~45k pull-ups
are too weak. Sensor 0x3A, EEPROM 0x50; the two buses can share one host I2C
port. R1 holds WP high (writes blocked): drive pin 7 low to write the EEPROM.

**Bench boards only.** A fitted header does not fit the host boot or carrier.
Leave J2 unfitted on boards that mate with the radio.

## Host dependencies

The host must provide current-limited, switched power, signal isolation, bus
pull-ups, controlled write-protect access, and hot-swap detection/recovery.
Presence grounded on a normal connector does not establish contact ordering.
Do not test powered insertion until that hardware is designed and verified.
The two power flags simply tell ERC that supply and ground come from the host.

Before hardware release, check supply ramp requirements, rail tolerance/noise,
bus rise times and sink currents, sensor startup delay, and power-off leakage.
The fitted WP resistor also connects to the switched daughter rail.

## Layout approach and unresolved decisions

Target a simple two-layer PCB, sensor at the exposed end and connector at the
opposite end. Place C1 immediately beside U1 supply/ground and keep the sensor
away from main-board heat and mechanical structures that obstruct its aperture.
Keep memory and test access closer to the connector. No exact outline or mounting
hole positions have been selected yet.

J1 now uses the shared MEC1 NP twenty-contact card-edge footprint, mating with
the radio's MEC1-110-02-L-D-NP-A socket. See
[mechanical contract](../radio/MECHANICAL.md) for front/back numbering, board
thickness and the prototype-versus-release finger finish. The card may be inserted
either way round. Physical mating and carrier retention remain unverified. Turn system power OFF before changes.
U1 has a local Adafruit-derived footprint; review its stencil and assembly
requirements before release. Standard footprint libraries are supplied in AppDir;
all assigned patterns still require dimensional review before fabrication.

The EEPROM must fit the measured Wasm module and manifest. Its selection is not
frozen. The BOM is a schematic review list, not an order-ready procurement BOM.

## Checks and reproduction

Validated with the supplied KiCad 10.0.7 CLI. `erc-report.txt` records the result.
No electrical errors or warnings remain, with no project-specific exclusions.
KiCad's default ignored checks are listed in the report. Passing ERC does not
validate mechanical fit, hot swapping, timing, or real hardware behavior.

From the repository root:

```sh
squashfs-root/bin/kicad-cli sch erc hardware/ir-daughter/babel-ir-daughter.kicad_sch --exit-code-violations -o hardware/ir-daughter/erc-report.txt
squashfs-root/bin/kicad-cli sch export netlist hardware/ir-daughter/babel-ir-daughter.kicad_sch --format kicadxml -o hardware/ir-daughter/babel-ir-daughter.net.xml
python3 hardware/ir-daughter/tools/verify_netlist.py
squashfs-root/bin/kicad-cli sch export pdf hardware/ir-daughter/babel-ir-daughter.kicad_sch -o hardware/ir-daughter/babel-ir-daughter.pdf
```

`tools/generate_schematic.py` creates the schematic, local libraries, and BOM,
using the pinned Adafruit source to translate the sensor footprint. It overwrites
those files: after hand edits, use the schematic as the source
of truth and do not regenerate without reconciling changes. The independent
netlist verifier checks every connected component pin, no-connects, and DNPs.
