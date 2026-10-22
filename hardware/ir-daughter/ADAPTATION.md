# Adafruit MLX90632 adaptation — Babel revision B

2026-10-17. This is a Babel adaptation of **Adafruit MLX90632 FIR Remote Thermal
Temperature Sensor - Medical Grade STEMMA QT / Qwiic PCB**, designed by
Limor Fried/Ladyada for Adafruit Industries. It is not an Adafruit-manufactured
or endorsed product.

Original source:
https://github.com/adafruit/Adafruit-MLX90632-FIR-Remote-Thermal-Temperature-Sensor-PCB

Pinned commit: `928c728704680ccfc11515f2ec7113c8cb7d4224`.

The unmodified Eagle schematic, board layout, full README attribution, and
CC BY-SA 3.0 license are retained in
[the reference directory](../reference/adafruit-mlx90632/README.md).
Because the board incorporates the adapted circuit and footprint, the **entire
`hardware/ir-daughter` project** is licensed under CC BY-SA 3.0; see
[LICENSE](LICENSE), which contains the full legal text and attribution notice.
Keep LICENSE and this file with redistributions, and license further adaptations
under CC BY-SA. This license covers only the daughter project. The radio board
and Babel software are licensed separately.

## What is reused

- MLX90632 sensor pin connections, grounded exposed pad, and 100 nF bypass.
- A 10 kohm ADDR pulldown (upstream R2, Babel R6).
- Sensor footprint copper pads and split exposed-pad paste openings translated
  from Eagle into a project-local KiCad footprint. Y coordinates are inverted
  between formats; pad numbers are preserved. Extra illustrative artwork beside
  the footprint is omitted. Stencil/assembly review remains required.
- The DCB, 3.3 V I/O sensor variant specified in Adafruit's guide. The Eagle
  symbol itself has a generic MLX90632 value and a BCB-named internal symbol;
  the guide identifies the actual breakout's DCB variant. Babel's BOM explicitly
  selects `MLX90632SLD-DCB-000-RE`.

## Babel modifications

| Upstream feature | Babel treatment |
| --- | --- |
| STEMMA QT connectors and breakout header | Replace with the draft card-edge port J1; geometry and physical socket still pending. |
| AP2127K-3.3 regulator, input/output capacitors | Omit regulator stage because Babel supplies regulated, switched 3.3 V. Retain local sensor bypass and a provisional 1 uF port capacitor. |
| BSS138 level shifting and 10k pull-up array | Omit level shifting for the 3.3 V-only bus. Host supplies normal bus pull-ups; daughter R2/R3 remain optional DNP bench pads. |
| Address-select jumper/header | Omit, retaining 10k pulldown for default address 0x3A. Only one daughter board is attached. |
| Power LED and enable jumper | Omit to avoid unnecessary power/heat. Host reports attachment state. |
| Driver storage | Add U2 EEPROM at 0x50 on the separate NVM bus, default write protection, decoupling, and a bench header (J2). |

This is an adaptation of the sensor circuit and footprint, not a completed
conversion of the entire routed Adafruit PCB. Their board layout remains
available as a reference for placement. New connector geometry and routing must
still be reviewed and tested. The original MLX90614 draft is preserved in
`hardware/archive/ir-mlx90614-rev-a`.

## Firmware consequences

The sensor now uses I2C address 0x3A instead of the earlier MLX90614's 0x5A and
has a different register map. The previous SMBus/PEC driver notes no longer apply.
Temperature conversion uses calibration coefficients and raw readings; port the
appropriate manufacturer or Adafruit algorithm behind Babel's Wasm bus API.
The Arduino/CircuitPython libraries do not run unchanged in WAMR. Review their
software licenses separately when actually importing code.

The sensor's internal calibration EEPROM is **not** the added driver EEPROM.
Preserve factory calibration and select calculation/measurement mode for the
exact DCB variant. The new driver size must be measured before freezing U2's
32 KiB capacity. This draft makes no claim of medical instrument accuracy.

References: [Adafruit guide](https://learn.adafruit.com/adafruit-mlx90632-fir-remote-thermal-temperature-sensor/overview),
[Melexis datasheet](https://www.melexis.com/-/media/files/documents/datasheets/mlx90632-datasheet-melexis.pdf).
