# Layout-entry protection review

This is a static component coordination check, not a tested surge/ESD rating.
The permitted source is compliant 5 V USB-C with >=1.5 A advertisement. No PD,
12 V supply or sustained overvoltage tolerance is claimed.

D3 selection is Diodes Incorporated SMBJ6.0A (unidirectional SMB), not an
arbitrary vendor's similarly named substitution. Its 6 V stand-off is above
normal VBUS; specified maximum clamp is 10.3 V at the rated pulse condition.
U18 TPS22810 input absolute maximum is 20 V. U16 TPS709 accepts 30 V input;
charger U3 input is rated 28 V absolute maximum. The 16 V input capacitors are
the lower positive-voltage ceiling. This leaves 5.7 V static margin between
the selected TVS's rated clamp and the capacitor rating, before PCB inductive
overshoot. Ratings are not normal operating targets.

Place D3 after F1 immediately at the connector-side return, short wide copper
and adjacent ground vias, before branching to U18/U16. Probe TP2/TP3 during
controlled transient tests. A preliminary <12 V positive overshoot acceptance
target reserves margin to 16 V capacitors; test with the intended cable/source
and appropriate surge equipment. Check negative excursions separately: a
unidirectional TVS forward drop does NOT by itself guarantee a -0.3 V IC limit.

F1 limits consequences of sustained shorts only when source current/time can
actually clear it. A current-limited 1.5 A source may never clear a 1.5 A fuse.
The TVS cannot absorb a sustained incorrect supply indefinitely. Neither fuse
nor the permission switch is an overvoltage disconnect. Product-grade wrong-
adapter/surge protection would require a separate fault specification and review.

USB data/CC and daughter-signal ESD devices must be at their connector entries,
with no long discharge path through logic ground. Their individual ratings
do not qualify the finished product. Inspect every protected path and return
after routing; then test powered/unpowered behavior. Keep DNP R90 until the
independent charging qualification in PRE-LAYOUT.md is complete.

Sources: [Diodes SMBJ6.0A](https://www.diodes.com/part/view/SMBJ6.0A),
[TPS22810](https://www.ti.com/lit/ds/symlink/tps22810.pdf),
[TPS709](https://www.ti.com/lit/ds/symlink/tps709.pdf),
[BQ2407x](https://www.ti.com/lit/ds/symlink/bq24074.pdf).
