# Drawing provenance — layout-entry review, 2026-10-19

Local manufacturer references for dimensional review. Retain their original
copyright notices; these are reference drawings, not Babel-authored assets.

| Local file | Original source / use |
| --- | --- |
| mec1-footprint.pdf | [Samtec footprint rev R](https://suddendocs.samtec.com/prints/mec1-1xx-xx-xx-d-xx-xx-footprint.pdf): socket pad centers, A holes, card fingers, thickness/bevel/hard gold |
| mec1-mated.pdf | [Samtec mated drawing](https://suddendocs.samtec.com/prints/mec1%20mated%20document-mkt.pdf): 0.991 mm fully seated card-tip height |
| tps63070.pdf | [TI TPS63070](https://www.ti.com/lit/ds/symlink/tps63070.pdf): RNM0015A land pattern, PS/SYNC resistor, reference capacitor MPNs |
| bq2407x.pdf | [TI BQ2407x](https://www.ti.com/lit/ds/symlink/bq24074.pdf): BQ24079 uses RGT0016B; charging/current/timer limits |
| rgt0016b-reference.pdf | [TI CDCLVP2102](https://www.ti.com/lit/ds/symlink/cdclvp2102.pdf): exact RGT0016B drawing 4219033/A, 1.6 mm EP (latest BQ family appendix shows a different RGT-C pattern) |

Dimensional screen and native parser checks are complete for the custom patterns;
solderability, fabricated tolerances and mating still require physical checks.
Radio stack baseline comes from [JLCPCB](https://jlcpcb.com/impedance),
JLC04161H-7628. Manufacturer thickness/impedance confirmation precedes fabrication.
