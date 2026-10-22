# Review: rev C external-charging pivot — read before continuing

Date: 2026-10-18. Written by a reviewing agent at the user's request, after the
previous radio-board session paused mid-way through the rev B → rev C change.

## Recommendation

**Restore on-board charging (rev B behavior).** The user asked for this
recommendation after discussing their concern about on-board charging. Confirm
with the user before rebuilding, then record the decision and rationale in
[architecture-notes.md](../../architecture-notes.md).

Keep the rev B release posture: charging stays disabled in the default
assembly (R90 DNP) until bench qualification of charge current, the hardware
temperature window, timers and pack thermals.

### Rationale

- Rev B already covered the electrical charge risks conservatively: 4.1 V
  target (max 4.141 V) under the pack's 4.2 V, ~0.17C charge current,
  independent hardware temperature window (U20) with open/short-NTC inhibit,
  enabled safety timers, protected pack, and a DNP enable resistor.
- Rev C does not remove battery risk. The pack is still inside the device and
  still discharges; puncture, crush, short and heat-exposure risks are
  mechanical and are identical in both revisions.
- Rev C moves charging to an uncontrolled external charger. Generic chargers
  often ignore the pack NTC, and typically use 2-pin JST PH leads with
  vendor-inconsistent polarity, so an adapter to the 3-pin Jauch harness is
  likely — a reverse-polarity hazard.
- Routine unplugging of J5 (JST PH) from an internal pouch cell wears a
  connector not intended for frequent mating and stresses the cell leads.

## Rev B source is mostly lost — rebuild carefully

The archive at [../archive/radio-revB-charging/](../archive/radio-revB-charging/)
holds only README, FEATURES, VALIDATION and audit_charge_limits.py. The rev B
`generate_schematic.py` and sheets were overwritten by the rev C generation,
and the project is not under version control.

- `../archive/radio-revB-charging/babel-radio-revB.pdf` is a copy of the last
  rev B PDF export (made 21:35, before rev C generation). It is the only
  complete record of the rev B charge circuit (U20, U22, U23, R90, R103,
  R108, R109, NTC wiring to J5 pin 2, CE control, TS 10k bias, TMR resistor).
  Do not delete it.
- `radio/babel-radio.pdf` is that same rev B export; it does not match the
  current rev C schematic. Re-export it only after restoring rev B.
- Recommend `git init` and a commit before further generator changes.

Restore plan: reintroduce the rev B charge-guard parts in
`tools/generate_schematic.py` using the archived README and PDF, remove
`R90`, `U20`, `U22`, `U23`, `R103`, `R108`, `R109` from the forbidden-parts
assertion in `tools/verify_netlist.py` (line ~112) and restore rev B checks,
update `tools/check_power_policy.py` (currently asserts charging is never
enabled), then regenerate and rerun the full README pipeline.

## Inconsistencies found in the current (rev C) tree

Verification status at review time: generator, ERC (0 errors/warnings),
netlist verification, power-policy and footprint checks all pass, and
regeneration reproduces the committed schematic, BOM and manifest exactly.
The problems are documentation and leftovers, not connectivity.

1. **Docs describe rev B, schematic is rev C.** `README.md`, `FEATURES.md`,
   `VALIDATION.md`, `PRE-LAYOUT.md` and `../../architecture-notes.md` still
   reference R90 DNP, U20 temperature window, 166 mA charging and the 9.53 h
   timer. The archive copies are byte-identical to the live files; the live
   files were never rewritten. (Moot if rev B is restored, but each doc must
   match whatever the schematic is.)
2. **Stale PDF.** See above.
3. **`tools/audit_charge_limits.py` is misleading in rev C.** It recomputes
   hard-coded rev B values without reading the netlist and prints
   `PASS ... R90 remains DNP`. Under rev B it is valid again; under rev C it
   must be removed from `tools/` and from the README command list.
4. **Decision not recorded.** Nothing documents who chose rev C or why. Record
   the user's confirmed decision on charging instead.
5. **Rev C leftovers on the schematic** (irrelevant if rev B is restored):
   R12 labelled "166mA" though nothing charges; CHG_N has a pull-up but goes
   nowhere; the sheet file is still `charge_guard`.
6. **Footprint checker vs README.** `check_footprints.py` prints an empty
   `OPEN footprint selections:` line, while the README says J1, switches and
   L1 still need final selection. Reconcile which is true.

## Unchanged in either revision

Bring-up without the pack on a current-limited supply; first charges attended
on a non-flammable surface; protective insulated battery compartment; the
U21 startup supervisor has no undervoltage latch and needs near-empty testing.
