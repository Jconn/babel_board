# Babel radio/main board — revision B draft

Baseline selected by the user: **ESP32-S3-WROOM-1-N8R8**. Alif excluded;
STM32N6 is not the current implementation. This board owns BLE, WAMR, display,
USB programming, power management, and one daughter port. No routing or
fabrication release is included.

Open [babel-radio.kicad_pro](babel-radio.kicad_pro) in KiCad 10, then its root
schematic. [PDF review copy](babel-radio.pdf), [review BOM](bom.csv), and
[GPIO allocation](gpio-map.csv) accompany the native files. Symbols are embedded
and also provided in the project-local library. Footprint names are provisional
and require dimensional validation before PCB work. The generated fp-lib-table
uses the supplied AppDir footprint libraries; assigned pad-number sets are checked.
Blank footprints are deliberate release blockers, not missing electrical pins.

## Sheets

1. Overview and release blockers.
2. Host: WROOM, EN delay, boot/reset/user buttons, 3.3 V SPI display-module header,
   and UART recovery header. GPIO35/36/37 are unavailable on the R8 module.
3. USB-C USB2 device input, USB data ESD, BQ24079 4.1 V charger/power path,
   and protected battery/NTC connector.
4. TPS63070 3.3 V buck-boost, reference-topology filter, feedback and system switch.
5. TPS2553 daughter power limit and hardware presence/request gating.
6. Card edge, dedicated NVM isolation, sensor isolation and switched-rail pull-ups.
7. Autonomous USB-C permission detection, gated power input and USB data switch.
8. Hardware charge-temperature window, timer and battery-startup supervision.

J1 contact numbers match the existing IR daughter electrical contract, but are
not a final physical connector order. SENSOR_TX means host TX, daughter RX.
H_ prefixes are MCU-side nets; unprefixed sensor/NVM names are connector-side.
Net labels connect across sheets. An NC cross is intentional, not an unfinished wire.

## Power and battery precautions

### Selected battery and integration status

User selection: **Jauch LP523450JU+PCM+JST PHR-3 70MM**, Jauch number
**251555**, protected 1S pouch pack, 3.7 V nominal, 4.2 V maximum, 1000 mAh typical.
The [pack specification](https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/5702/LP523450JU%20251555.pdf)
specifies 53 x 34.5 x 5.4 mm at delivery, up to 5.8 mm thick after cycling,
and a 10k NTC (B3435). Allow additional enclosure/retention clearance.

J5 now matches the pack's 1 red positive, 2 yellow NTC, 3 black negative.
The mating header is JST B3B-PH-K-S; verify its physical pin-1 orientation
against the actual harness before connection.
R12 is now 5.36k 1%: approximately 166 mA nominal, at most 184 mA using
TI's maximum 975 A-ohm factor and minimum resistor tolerance. This is below
190 mA (0.2C using the pack's minimum 950 mAh capacity) for its cold-temperature
charge-current limit. U20 now provides a separate hardware temperature window.
Keep R90 DNP until physical qualification.

The original direct-NTC connection failed margin screening and has been replaced.
Run `python3 hardware/radio/tools/audit_charge_limits.py` for current, voltage,
timer and temperature checks. The new window cuts off nominally below 10.7 C
or above 40.0 C. Screened cutoff corners are 7.1..13.7 C and 37.2..43.3 C,
including an ASSUMED +/-5% beta spread. The actual pack curve, thermal lag,
startup and fault behavior must still be qualified; this is not certification.

Provide a mechanically protective battery compartment with an insulating
barrier from solder joints, screw tips and hot components. Protection electronics
do not prevent puncture or external heating. Disconnect and remove the pack
during soldering/rework. Initial electrical bring-up should use a current-limited
supply without the pack, using a valid USB-C current advertisement.

**Charging is disabled in the default BOM: R90 is DNP.** Do not fit R90 until the
cell, its protection, permitted charge current, connector polarity, NTC curve,
charging temperature limits, and board thermals have been reviewed. R90 is a
hardware assembly option, not a firmware control. Never use an unprotected cell.
The charger is not battery overcurrent/undervoltage protection. The selected pack
is a protected 1S 4.2 V Li-ion, 1000 mAh typical, with a 10k NTC connected to
pack negative. A two-wire pack is not a drop-in replacement. The NTC is measured
by U20, independently of the processor, and controls charger CE through U22/U23.
The charger's original TS input has a fixed 10k bias because it no longer performs
pack-temperature sensing. Never bypass U20 or connect R90 directly to ground.

- BQ24079 replaces BQ24074: nominal 4.1 V charging (maximum 4.141 V) leaves
  margin below the pack's 4.2 V limit. This deliberately reduces usable capacity.
  It is NOT the voltage-based-TS BQ24079T variant. CE is pin 4; SYSOFF pin 15 is low.
- R108 = 71.5k 0.1% sets nominal 9.53-hour fast-charge and 57.2-minute precharge
  timers. Fast-charge tolerance is 7.14..11.93 hours before dynamic extensions.
  Current taper and actual pack capacity need bench testing for completion.
  Timer expiry is a fault, not permission to repeatedly restart charging.
  External-temperature CE cycling resets the timer; this is NOT a cumulative
  wall-clock charge watchdog. Firmware should report faults and avoid retries.
- USB-C-only policy: require 5 V and advertised 1.5 A or 3 A. U15/U16 run before
  the main rail; U18 gates input power and U19 gates data. R13 sets nominal
  904 mA charger input, at most 976 mA, leaving margin for the CC circuitry.
  Default-current USB-C and USB-A adapters are unsupported and cannot charge.
  Native USB programming additionally needs a data-capable C-to-C connection.
  See [USB-STARTUP.md](USB-STARTUP.md). No USB PD negotiation or USB host mode.
- GPIO3/45 now remain pulled-low reserved straps, disconnected from charger
  control. GPIO48 still senses accepted charger input via USB_PGOOD_N.
- U21 screens battery voltage before main-rail startup; USB permission can start
  the main rail with no battery. The battery threshold is approximately 3.33 V,
  with hysteresis but no removal/undervoltage latch. Test near-empty cycling.
- System switch SW4 disables the buck-boost, not charging. Off is not a physical
  battery disconnect. The pack must protect against deep discharge.
- TPS63070 feedback: 0.8*(1+470/150) = 3.307 V nominal. Regulator transient and
  thermal margins are not yet measured. Capacitor DC-bias derating matters.
- Daughter power: 226k 1% on TPS2553 gives TI's nominal 120 mA setting, with
  documented 101.3–142.1 mA limits; continuous daughter budget stays 100 mA.
- J3 VTREF is for a 3.3 V UART adapter's voltage reference, not a second power
  input. Do not backfeed the rail or connect RS-232-level signals.

## Port sequencing and limitations

Hardware equations:

```
PORT_EN     = !PRESENT_N && PWR_REQ
NVM_OE_N    = !(PORT_EN && NVM_REQ)
SENSOR_OE_N = !(PORT_EN && SENSOR_REQ)
```

All requests have pulldowns; switch OEs have pull-ups. The MCU resets with the
port isolated and unpowered. Removal detection forces these gates off without
waiting for the Wasm driver. This is not a guarantee of early removal detection:
the exact card-edge contact lengths, ground-first behavior, bounce and partial
insertion must still be designed and tested. Firmware must clear requests on
presence loss before a new attachment; the gates are not a removal latch.

Boot/attach: keep requests low and GPIOs high impedance, debounce presence,
enable power, wait for validated settling, enable NVM only, validate the image,
configure the selected sensor peripheral, then enable sensor isolation.
Removal/fault: clear sensor/NVM requests and power, cancel transactions, invalidate
readings, and require a fresh attachment/retry sequence. Disable internal MCU
pull-ups before disconnecting. WP and reset controls are open-drain.

Revision B retains all sensor signals behind one enable (U13/U14); unused sensor
interfaces are high impedance at the MCU but **not individually disconnected**
while the selected bus operates. This is the prototype policy, not the earlier
per-interface isolation proposal. Firmware must own/configure every pin and keep
unused interfaces high impedance. EEPROM isolation remains independent.

The switches do not recover a stuck I2C bus. Host transactions need deadlines
and recovery; EEPROM isolation is independent of sensor isolation. The rail's
10k bleeder gives passive discharge, not an active discharge or power-good check.
TPS2553 fault reporting is to firmware; no fault latch is provided. Verify
auto-retry, voltage collapse, signal back-powering and removal transients.

USB data, CC and all fourteen card-edge signal contacts now have ESD devices.
VBUS transient protection and physical ESD return-path review remain open.
IC ratings do not constitute system-level ESD qualification. R120..R123 are
populated 0-ohm source-series tuning sites for host-driven SPI/UART signals.

## Selected display and mechanical integration

User selection: **[Adafruit 4741](https://www.adafruit.com/product/4741)**,
1.5-inch 128x128 OLED, SSD1327, 16-level grayscale (not color), using SPI.
Use the complete breakout with its onboard regulator and OLED boost converter,
not a bare panel. A full 4-bit framebuffer occupies 8192 bytes. Include idle
display blanking in firmware to reduce OLED wear.

The [Adafruit pinout guide](https://learn.adafruit.com/adafruit-grayscale-1-5-128x128-oled-display/pinouts)
requires cutting the breakout's J1 and J2 jumper traces to select SPI; these
jumper names are unrelated to Babel's connector references. It ships in I2C mode.

Babel J2 is a keyed JST PH adapter header, not a pin-for-pin module connector:
1 power (to module Vin), 2 ground, 3 clock, 4 MOSI, 5 CS,
6 D/C, 7 reset, 8 reserved NC. No touchscreen, MISO, or PWM brightness control is
allocated. OLED needs no backlight; schematic notes now identify the selected
module. Existing LCD_* net names are retained to avoid needless renaming.
The source CAD outline, mounting pattern and exact cable mapping are recorded in
[DISPLAY-INTEGRATION.md](DISPLAY-INTEGRATION.md). Physical stack height, cable
clearance and measured power budget still need checking before layout.

J4 is GCT USB4105-GF-A, with SH shield pads mapped to ground; J5 is selected above.
J1, switches, regulator and L1 footprints still need final selection. All
assigned footprints still need pad/dimension review. The WROOM antenna needs
Espressif's keepout and suitable placement away from battery/display metal.

## Verification and reproduction

See [PRE-LAYOUT.md](PRE-LAYOUT.md) for the ordered release checklist and progress.
See [FEATURES.md](FEATURES.md) for supported design paths and qualification limits.

Run from repository root with the supplied KiCad CLI:

```sh
python3 hardware/radio/tools/generate_schematic.py
squashfs-root/bin/kicad-cli sch erc hardware/radio/babel-radio.kicad_sch --exit-code-violations -o hardware/radio/erc-report.txt
squashfs-root/bin/kicad-cli sch export netlist hardware/radio/babel-radio.kicad_sch --format kicadxml -o hardware/radio/babel-radio.net.xml
python3 hardware/radio/tools/verify_netlist.py
python3 hardware/radio/tools/audit_charge_limits.py
python3 hardware/radio/tools/check_power_policy.py
python3 hardware/radio/tools/check_footprints.py
squashfs-root/bin/kicad-cli sch export pdf hardware/radio/babel-radio.kicad_sch -o hardware/radio/babel-radio.pdf
```

The generator overwrites the schematic, library, BOM and generated manifest;
reconcile manual edits first. Existing project settings are preserved. The checker
compares exported connectivity with the manifest and independently checks key IC
pin maps, reserved GPIOs, charge-disable assembly, isolation paths and the existing
IR daughter's J1. ERC uses normal KiCad defaults, with no project-specific waivers.
Neither test proves analog behavior, footprint correctness, battery safety, RF
performance or successful hot swapping. WAMR/BLE hardware bring-up remains undone.

## Design references

- [Espressif module datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf), pin table and R8 restrictions.
- [Espressif schematic guidance](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/schematic-checklist.html), EN and USB.
- [BQ2407x family including BQ24079](https://www.ti.com/lit/ds/symlink/bq24074.pdf), pin table and charge settings.
- [TPS3700](https://www.ti.com/lit/ds/symlink/tps3700.pdf), comparator limits and hysteresis.
- [TPS709](https://www.ti.com/lit/ds/symlink/tps709.pdf), always-on CC/NTC supply.
- [TUSB320LAI](https://www.ti.com/lit/ds/symlink/tusb320lai.pdf), sink-only GPIO mode and internal Rd.
- [TPS22919](https://www.ti.com/lit/ds/symlink/tps22919.pdf), input gating.
- [TS3USB221A](https://www.ti.com/lit/ds/symlink/ts3usb221a.pdf), data disconnect and powered-off leakage.
- [TPD2E2U06](https://www.ti.com/lit/ds/symlink/tpd2e2u06.pdf), 3-pin DCK variant, connector protection.
- [TPS63070](https://www.ti.com/lit/ds/symlink/tps63070.pdf), pin table and adjustable-output reference BOM. RNM has 15 numbered pads; do not invent a generic extra exposed pad.
- [TPS2553](https://www.ti.com/lit/ds/symlink/tps2553.pdf), DBV pinout and Table 2 current-limit tolerances.
- [SN74CB3Q3245](https://www.ti.com/lit/ds/symlink/sn74cb3q3245.pdf), isolation and powered-off behavior;
  [TI pin diagram](https://www.ti.com.cn/document-viewer/cn/SN74CB3Q3245/datasheet).
- [SN74LVC1G08](https://www.ti.com/lit/ds/symlink/sn74lvc1g08.pdf), [SN74LVC1G04](https://www.ti.com/lit/ds/symlink/sn74lvc1g04.pdf), DBV pin tables.
- [USBLC6-2](https://www.st.com/resource/en/datasheet/usblc6-2.pdf), SC6 pin diagram.

The WROOM stock check from the preceding evaluation supports small-quantity
prototype sourcing, not a lifetime supply guarantee. The complete supporting BOM
has not yet been stock-qualified. Do not order from this review BOM as a kit.
