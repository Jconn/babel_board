# Layout-entry review — 2026-10-19

**Ready to begin placement and routing, not fabrication or charging.** The
[shared layout contract](../LAYOUT-PLAN.md) supersedes the historical checklist
below. Both native PCB seeds contain all schematic components and assigned nets;
locked interfaces are anchored, other circuit parts are staged outside outlines.

Resolved since the checklist was written:

- Defined 60 x 80 mm radio / 30 x 35 mm daughter envelopes, OLED standoffs,
  insulated below-board pack space and antenna exclusion region.
- Defined asymmetric keyed-carrier/retention CAD and checked analytical
  clearances. Physical print/mating qualification remains pending.
- Screened custom land patterns against manufacturer drawings; corrected
  BQ24079 to the RGT0016B 1.6 mm exposed pad. Verified native footprint parsing
  and all numbered pads against both exported netlists.
- Added regulator PS/SYNC series resistor, exact reference power-capacitor
  MPNs/body sizes and sixteen radio bring-up test pads.
- Set four-layer radio stack baseline, USB routing corridor, two-layer daughter,
  native routing constraints, mounting holes and keepouts.
- Recorded static VBUS coordination in PROTECTION-REVIEW.md, bus-speed limits
  and separate USB/battery load budgets. No system ESD/surge rating is claimed.

Next work is placement, routing, ground/thermal review, test access and silkscreen.
Before fabrication: clear DRC/parity, confirm supplier impedance and BOM, print
the mechanical coupon, check actual hardware fit, approve stencil/thermal holes,
and order daughter prototypes as standard ENIG (hard gold/bevel deferred).
No supplier acceptance or stock reservation has been obtained.

Before fitting R90: current-limited battery/NTC simulation, real NTC curve,
open/short faults, thermal lag, temperature corners, timer expiry/completion and
source-removal tests. Beta tolerance remains an explicit calculation assumption.
Power OFF for prototype daughter changes; hot-swap and RF/USB/runtime behavior
require assembled-system qualification. See VALIDATION.md for exact test scope.

## Historical checklist — superseded by the status above

Started 2026-10-18. This checklist distinguishes schematic edits from verified
hardware behavior. No PCB routing or fabrication release is authorized by a
passing ERC alone.

## 1. Battery and display integration — in progress

- Done: Jauch 251555 J5 logical pin order corrected to positive / NTC / negative.
- Done: R12 reduced to 5.36k 1%, nominal 166 mA, calculated maximum 184 mA.
  Independent checker asserts pack polarity, current value and cold-current margin.
- Done: Adafruit 4741 OLED identified in schematic; SPI jumper instructions added;
  independent J2 signal mapping check added. This is an adapter header, not a
  pin-compatible direct module socket.
- Done: replaced direct NTC sensing with a TPS3700 hardware window, including
  open/short detection; nominal charge window approximately 11..40 C. Calculated
  corner cutoff range stays inside pack limits with an assumed +/-5% beta spread.
  Run `python3 hardware/radio/tools/audit_charge_limits.py` to reproduce.
- Done: BQ24079 4.1 V variant selected for charge-voltage margin; 71.5k 0.1%
  timer resistor sets nominal 9.53-hour timeout (tolerance 7.14..11.93 h).
- Open physical qualification: actual NTC curve, thermal lag, electrical startup,
  fault handling, charge completion/taper at timer corners. No cumulative watchdog.
- Done: selected JST battery header and GCT USB receptacle with matching pad names.
- Done: keyed JST PH OLED header, cable mapping and CAD-derived mounting pattern
  recorded in DISPLAY-INTEGRATION.md. Open: physical stack height and clearance.
- Open: protective battery compartment, cycling expansion allowance and antenna
  clearance. Battery disconnected/removed during rework.
- R90 remains DNP: charging is NOT enabled by these edits.

## 2. Card-edge mechanical contract — open

Selected MEC1-110-02-L-D-NP-A with shared host/daughter footprints. Manufacturer
dimensions and limitations are in MECHANICAL.md. Procurement is not confirmed.
External keying/retention, custom-footprint review and physical mating remain open.
Power OFF for prototype module changes; equal-length contacts are not sequenced.
Evaluate ground-first and presence-last insertion / presence-first removal;
do not assume ordinary equal-length contacts provide this sequencing. Check
partial insertion, bounce and whether a removal latch is required. Update BOTH
boards and their independent contract checks together when assigning geometry.

## 3. USB-only startup and power policy — open, release blocker

Implemented in rev D; physical qualification remains a release blocker.
[USB-STARTUP.md](USB-STARTUP.md) records the USB-C-only policy: require advertised
1.5 A/3 A, reject default/legacy sources. TUSB320LAI, TPS70933, TPS22810 and
TS3USB221A provide autonomous power/data gating. Native USB programming retained.
Independent checker covers part pins, current limit, absence of duplicate Rd,
and removal of MCU strap pins from current policy. Test both ROM and firmware.

## 4. Signal integrity and connector protection — open

Set explicit I2C capacitance/rise-time and SPI/UART speed limits for the port.
Include switch and ESD capacitance, host and daughter traces and device inputs.
Done: four 0-ohm source tuning sites and TPD2E2U06 protection for CC and fourteen
daughter signals. Grouped sensor isolation is the prototype policy; unused GPIOs
must remain high impedance. VBUS fuse/TVS and higher-voltage input switch added;
protection coordination and actual ESD return paths remain open. IC ratings are
not system ESD qualification. Scope-test insertion/removal.

## 5. Footprints, placement and release checks — open

Verify every exact package/pad map against manufacturer drawings, especially
TPS63070 RNM, charger exposed pad, USB shell contacts and card edge. Vendor needed
libraries and models; inspect a 1:1 mechanical mock-up with OLED, battery and
daughter inserted. Define stackup, power loops, antenna keepout and test points.
Re-run both boards' ERC/netlist checks and review rendered PDFs after each change.
Then perform placement review before routing; bench qualification follows assembly.
All radio footprints are now assigned, including switches and L1. The pad-number
checker is not a substitute for dimensional review of the custom patterns.

## References

- [Jauch selected pack specification](https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/5702/LP523450JU%20251555.pdf)
- [BQ24074 datasheet](https://www.ti.com/lit/ds/symlink/bq24074.pdf)
- [OLED module pinout and SPI configuration](https://learn.adafruit.com/adafruit-grayscale-1-5-128x128-oled-display/pinouts)
