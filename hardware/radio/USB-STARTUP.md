# USB-only startup review

2026-10-19. Revision D implementation; not yet qualified on physical hardware.
Requirement: USB-C power and programming with the pack absent or depleted,
as well as battery-only operation. Native ESP32 USB is the current data path.

## Two separate startup cases

| Source | Permission before enumeration | Design consequence |
| --- | --- | --- |
| Type-C advertising 1.5 A or 3 A | Advertised Type-C current, after valid detection | Supported target: hardware admits power and data before host boot |
| Type-C default-current / legacy USB-A data port | No higher-current grant | Unsupported: input power and data remain disconnected |
| Legacy charging-only adapter | No Type-C higher-current grant | Unsupported; no charging |
| Battery only | No USB input | Supported target: USB power and data remain disconnected |

## Implemented direction

The user committed to USB-C-only. Revision D deliberately does not implement
legacy-port enumeration within 100 mA. USB-C connector shape alone is insufficient:
the source must advertise at least 1.5 A. A USB-C PC port/hub with that advertisement
and a data cable is needed for programming; a charging brick cannot program Babel.

U16 TPS70933 supplies V3V3_CC from VBUS before main power starts. U15 TUSB320LAI
is strapped sink-only, GPIO mode, enabled; its internal dead-battery Rd replaces
R6/R7. OUT1 high means not approved; OUT1 low identifies medium/high current.
U17 inverts OUT1 to USB_ALLOW. Pull-ups use only V3V3_CC to avoid back-powering U15.

U18 TPS22810 gates fused/TVS-protected VBUS into the charger; unsupported sources do not power the
charger/main load even if a charged battery is installed. U3 EN1 is grounded and
EN2 follows USB_ALLOW. R13 limits charger input to 976 mA maximum; CC/control
draw is additional and separately budgeted. GPIO3/45 are no longer power controls.

U19 TS3USB221A disconnects USB data unless OUT1 is low. It is powered from the CC
rail, with powered-off isolation, so even ROM USB pull-ups cannot attach on a
battery-only or unsupported-source connection. Native ESP32 USB is retained.

U21 checks battery voltage; D1/D2 OR battery-good with USB_ALLOW to SW4/main EN.
With no pack, rejected USB sources leave the main rail off. With a usable pack,
the device may run on battery but still rejects that USB connection. Losing a
valid USB source can transfer to battery or turn the device off; uninterrupted
transfer is a bench-test requirement, not a schematic guarantee.

U20/U22/U23 permit charging only with acceptable pack temperature AND USB_ALLOW,
and only once R90 is fitted after qualification. The CC detector does not negotiate
USB PD, detect BC1.2 charging ports, enumerate USB, or supply overvoltage protection.

## Required bench evidence before closing the blocker

1. Use the selected N8R8 module or matching development hardware. Separate its
   supply from any dev-board USB-UART/regulator load that would invalidate results.
2. Measure VBUS input current, 3.3 V rail and CHIP_EN during cold boot with no pack.
   Include peak/inrush and sustained current, not only a handheld meter average.
3. Test both normal boot and BOOT-held ROM programming, including a blank flash.
4. Test rejection of USB-A/default-current sources, acceptance of 1.5 A/3 A,
   both Type-C orientations, no pack, depleted pack and charged pack.
5. Exercise enumeration failure, suspend/resume, reset, unplug/replug, loss of
   current advertisement, and display/daughter/BLE activation after permission.
6. Verify advertised USB power matches the allowed load; current-limit tolerances,
   regulator efficiency and charging must fit inside the granted input budget.
7. Confirm no VBUS backfeed and no USB pull-up attachment on battery alone.

Pass criteria: no over-budget operation, repeated brownout or unsafe charging;
successful battery-free programming on supported data ports. If a source cannot
support the full load, stay within its allowance with controlled behavior.

## References

- [TI TUSB320LAI datasheet](https://www.ti.com/lit/ds/symlink/tusb320lai.pdf), sink/GPIO modes and power-off handling.
- [TI BQ2407x family datasheet](https://www.ti.com/lit/ds/symlink/bq24074.pdf), including selected BQ24079.
- [Espressif schematic checklist](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/schematic-checklist.html), supply and reset requirements.
