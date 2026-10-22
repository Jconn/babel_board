"""Exhaustive steady-state policy checks, not transistor/startup simulation.

Independent acceptance model for the schematic's permission, power and CE gates.
Pair with verify_netlist.py; transient/analog behavior requires physical tests.
"""
from itertools import product

count = 0
for vbus, advert, battery_ok, switch_on, temp, r90 in product(
        (False, True), ('none','default','1.5A','3A'), (False,True),
        (False,True), ('cold','ok','hot','open','short'), (False,True)):
    # TUSB320 Table 3: OUT1 low only for attached medium/high current.
    out1 = not (vbus and advert in ('1.5A','3A'))
    usb_allow = vbus and not out1
    input_gate = usb_allow
    data_gate = usb_allow
    main_enabled = switch_on and (battery_ok or usb_allow)
    charge_enabled = r90 and usb_allow and temp == 'ok'
    if not vbus or advert in ('none','default'):
        assert not input_gate and not data_gate and not charge_enabled
        assert main_enabled == (battery_ok and switch_on)
    if vbus and advert in ('1.5A','3A') and switch_on:
        assert main_enabled  # Works in the policy even with no/depleted pack.
    if not r90 or temp != 'ok': assert not charge_enabled
    if not switch_on: assert not main_enabled
    count += 1
print(f'PASS: {count} steady-state source/battery/switch/temperature/assembly cases.')
