# Prototype feature contract — radio revision D

These are the capabilities implemented in the schematic or targeted by firmware,
not claims of tested hardware. No PCB is routed and no fabrication release exists.

| Feature | Prototype behavior / limit | Status |
| --- | --- | --- |
| Processor | ESP32-S3-WROOM-1-N8R8; 8 MB flash, 8 MB PSRAM | Schematic |
| Portable daughter drivers | WAMR executes EEPROM-supplied Wasm on the main processor | Firmware target, not demonstrated |
| Wireless | BLE connection to Android | Firmware target, not demonstrated |
| Display | Adafruit 4741, 1.5-inch 128x128, 16-level grayscale OLED, SPI | Keyed cable mapping and mounting pattern documented; physical fit pending |
| Wired power | 5 V USB-C source advertising 1.5 A or 3 A | Autonomous permission/input gating implemented; bench tests pending |
| Battery-free programming | Native ESP32 USB through same receptacle, including BOOT/reset recovery | Supported design path; requires approved data-capable C-to-C source |
| Unsupported USB sources | USB-A and default-current USB-C do not power, charge or attach data | Hardware rejection path |
| Battery | Jauch 251555, protected 1000 mAh pouch with separate NTC | Connector mapped; protective compartment required |
| Charging | 166 mA nominal; 4.1 V target, maximum specified 4.141 V | Circuit implemented; R90 DNP until qualification |
| Charge temperature | Hardware window, nominal roughly 11..40 C; open/short NTC inhibits charge | Static corner checks pass; real pack/thermal tests pending |
| Safety timer | Nominal 9.53 h fast charge, 57.2 min precharge; neither disabled | Tolerances/dynamic extensions documented; completion tests pending |
| Main power switch | Turns main rail/display/radio off; charging can remain active | Schematic; not a physical battery disconnect |
| Low battery | Main-rail startup supervised at roughly 3.33 V | No latched cutoff; near-empty behavior requires testing |
| Daughter port | Samtec MEC1-110-02-L-D-NP-A; 20 contacts, mirrored so a card works either way round; 3.3 V, 100 mA continuous | Mating patterns and reversible carrier/boot CAD defined; physical fit pending |
| Discovery | Separate EEPROM I2C and write protection | Schematic; host firmware pending |
| Sensor interfaces | Three general sensor lines (SENSOR_IO0-2): I2C + IRQ, UART, or 3-wire/read-only SPI; no 4-wire SPI | Grouped isolation; protocol set by firmware |
| Daughter changes | Hardware removal gating retained; turn SW4 OFF before changing modules | Hot swapping is a future qualification target, not yet supported |
| First daughter | Adafruit-derived MLX90632 IR sensor plus EEPROM | Daughter schematic checked; not routed |
| Protection | Daughter current limit, USB data/CC and daughter-signal ESD, VBUS fuse/TVS | Static coordination documented; system tests pending |

Not included: USB PD/higher input voltages, USB host/OTG, USB-A fallback,
color/touch display, per-interface sensor hardware isolation, a fuel gauge,
guaranteed real-time Wasm execution, or a cumulative charging-time watchdog.

## Prototype bus limits

Start EEPROM and sensor I2C at 100 kHz. Qualify 400 kHz only when the full
bus capacitance/rise time is measured; 4.7k pull-ups at 1% allow roughly 75 pF
for a 300 ns RC rise-time budget (including switch, ESD and all traces/devices).
This is a design budget, not a measured board value. Faster operation needs
waveform and driver qualification.
Never advertise the switch's analog bandwidth as a guaranteed protocol rate.

## Release gates

The default assembly cannot charge: R90 deliberately remains absent. First test
power/temperature circuits with current-limited supplies, simulated NTC resistances
and suitable battery simulation, before connecting the actual pack for charging.
Do not bypass the temperature guard or defeat timer faults.

Both native PCB seeds are ready for placement/routing; the shared LAYOUT-PLAN.md
defines anchors, mechanical stack, routing constraints and power allocations.
Physical fit checks precede manufacture (daughter prototypes: standard ENIG);
startup, charging, RF and hot-swap qualification follow assembly. See
PRE-LAYOUT.md and USB-STARTUP.md. Sixteen radio test pads support bring-up.
