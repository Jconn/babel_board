# Prototype debug access — 2026-10-19

The radio now has **38 exposed 1 mm probe pads** (22 added) and three fitted
removable zero-ohm links. The radio remains **60 x 80 mm** and the daughter
outline is unchanged. No new headers or mounting holes were added. Existing
connectors, switches and component positions are retained; additions occupy
unused front-side space outside the OLED footprint and keyed boot.

The daughter's seven test pads became a 2x4 0.1 in bench header, J2 (see the
[daughter README](../ir-daughter/README.md#bench-header-j2)). Its two I2C buses and
write-protect pin provide the downstream comparison for the host-side pads.

## Where to probe

Exact net names and board coordinates are in [debug-access.csv](debug-access.csv).
Use the native PCB or [current routing view](layout-routing.svg); the older
placement PNG predates these additions. Probe pads in grids are labelled
on silkscreen by number only ("19" = TP19); standalone pads keep "TPnn".

| Radio pads | Purpose |
| --- | --- |
| TP1–TP16 | Existing rail, charging, temperature guard, regulator and port-enable probes |
| TP17–TP19 | Host EEPROM SCL, SDA and WP, upstream of U12 |
| TP20–TP21 | Host sensor SCL and SDA, upstream of U13 |
| TP22–TP23 | NVM_OE_N and SENSOR_OE_N isolation controls |
| TP24–TP25 | PORT_FAULT_N and PRESENT_N |
| TP27–TP29 | V3V3_CC, CC_HIGH_N and USB_PGOOD_N |
| TP30–TP31 | BAT_OK and POWER_AVAILABLE |
| TP35 | Converter output before the removable main-load link |
| TP26, TP32–TP34, TP36–TP38 | Seven additional ground pads distributed around the board |

All nine radio ground probe pads now have short tracks to adjacent ground vias.
For switching ripple, use a ground spring at the relevant capacitor's ground
pad; an edge test pad and long ground lead are not a substitute for a local
measurement. There are no new stubs on USB data, CC pins, feedback or switching
nodes. Fine wires can be soldered to the exposed pads for a logic analyzer.

J3 remains the independent 3.3 V UART recovery interface: GND, voltage reference,
TX, RX, reset and boot. Its voltage reference is sense-only. BOOT and RESET
buttons remain accessible below the OLED. No new dedicated JTAG header is added.

## Power links

| Link | Size | Source → load | Use |
| --- | --- | --- | --- |
| R125 | 0805 | V3V3_REG → V3V3 | Disconnect all main 3.3 V loads from the converter or measure total load current |
| R126 | 0603 | V3V3 → V3V3_OLED | Separate OLED supply current; includes local display capacitor and pull-ups |
| R127 | 0603 | V3V3 → V3V3_PORT_IN | Separate daughter power-switch input current; includes its input capacitor |

All three are fitted as zero-ohm links in normal assembly. Select procurement
parts rated at least 1 A continuous for R125 and 0.25 A for R126/R127, with
maximum resistance at most 50 milliohms. Exact purchasing MPNs remain to be
selected. They are not fuses. Power down and disconnect the battery before
removing a link or installing a meter connection. Account for meter burden
voltage when investigating brownouts and transient behavior.

The regulator's feedback divider and all four output capacitors remain on
V3V3_REG, upstream of R125, so removing the load link does not open the feedback
loop. TP35 observes the converter side; TP8 observes the load side.

These links interrupt supply paths, not every signal path. For OLED isolation,
unplug the cable or hold its host interface low/high-impedance. For daughter
isolation, remove the daughter and keep power/bus requests low. Do not interpret
a removed power link as proof that connected signal pins cannot back-power a
device. For standalone daughter measurements, disconnect it from the host and
use its existing power, ground and bus pads.

## Suggested bring-up sequence

1. Check resistance to ground and assembly with all sources disconnected.
2. Leave R90 absent. Check USB_5V, V3V3_CC, CC_HIGH_N, USB_ALLOW and USB_CHG_IN
   to locate power-permission failures before investigating firmware.
3. Check SYS_RAW, REG_EN, V3V3_REG, V3V3 and REG_PG. If the rail collapses,
   isolate loads with the links and compare converter-side and load-side voltage.
4. Recover or log over J3 if USB does not enumerate. Confirm BOOT/reset behavior.
5. Check PRESENT_N, PORT_EN, PORT_FAULT_N and VDD_DAUGHTER. Compare host I2C
   pads with daughter I2C pads while watching the two isolation-enable probes.
6. Reconnect the OLED and daughter separately and measure their supply current.
   Charging qualification remains a separate step before fitting R90.

Routing is incomplete. Mechanical checks confirm nominal pad/courtyard access
outside the OLED and boot; physical probe, cable and enclosure fit still needs
the assembly mock-up. These features improve fault localization, not proof that
placement, signal integrity or charging behavior is correct.
