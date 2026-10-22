# Babel IR daughter board — revision A schematic draft

Open **babel-ir-daughter.kicad_pro** in KiCad 10, then open its schematic.
For immediate review, use [the PDF](babel-ir-daughter.pdf).
The project-local `Babel_IR.kicad_sym` and `sym-lib-table` travel with the project;
no external symbol library is needed to open or check the schematic.

This is an editable electrical design, not a finished PCB. No routed board,
Gerbers, or fabrication release is included.

## Circuit

- U1: MLX90614ESF-BCC-000-TU, 3 V family, 35° field of view. Pins 1/2 are
  sensor SCL/SDA, 3 is supply, and 4 is ground. Operates from the proposed
  switched 3.3 V rail, within the Bxx 2.6–3.6 V operating range. Supply-related
  temperature bias still needs characterization.
- U2: 24LC256-I/SN, provisional 32 KiB driver storage. A0–A2 low select 0x50;
  pins 6/5 are NVM SCL/SDA, 7 is WP, 8 supply, 4 ground.
- The sensor and EEPROM use physically separate buses. R1 holds WP high by
  default; the host pulls it low only during programming.
- C1/C2 are local 100 nF bypass capacitors, C3 is 1 uF at the port. Use ceramic
  capacitors with adequate voltage rating; exact purchasing parts remain open.
- R2–R5 are **not populated**. The normal host supplies connector-side bus
  pull-ups to switched daughter power. These pads allow bench pull-ups if needed.
- Seven test pads expose power, ground, both buses, and write protection.
- J1 pin 8 is the host's active-low presence signal, grounded on the daughter.
  Unused SPI/UART/IRQ/reset contacts are explicitly marked no-connect.

Pin assignments checked against the
[Melexis datasheet, revision 021](https://www.melexis.com/-/media/files/documents/datasheets/mlx90614-datasheet-melexis.pdf)
and [Microchip DS20001203Y](https://ww1.microchip.com/downloads/aemDocuments/documents/MPD/ProductDocuments/DataSheets/24AA256-24LC256-24FC256-256K-I2C-Serial-EEPROM-DS20001203.pdf).
Custom schematic symbols are functional representations, not footprint drawings.

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

J1 is a **logical 20-contact port**, not a chosen production connector. Its
numbering must be reconciled with actual mating views and contact sequencing.
U1 and J1 deliberately have no assigned footprint until their mechanical drawings
are reviewed. Other footprint names are standard-library candidates; the supplied
AppImage does not include the full footprint library, so they still need to be
installed/vendored and checked before board layout.

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

`tools/generate_schematic.py` created the initial schematic, local library, and
BOM. It overwrites those files: after hand edits, use the schematic as the source
of truth and do not regenerate without reconciling changes. The independent
netlist verifier checks every connected component pin, no-connects, and DNPs.
