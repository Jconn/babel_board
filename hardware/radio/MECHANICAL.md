# Prototype mechanical and land-pattern contract

Revision D, 2026-10-19. These are design inputs, not measured hardware fit.

- Host socket: Samtec MEC1-110-02-L-D-NP-A, vertical, 1 mm pitch, twenty contacts.
  **NP is mandatory**: the polarized ten-position-per-row version removes
  contacts 13/14 for its key, conflicting with our full twenty-signal contract.
- Host pattern: two rows, 7.061 mm center spacing; pads 0.610 x 1.880 mm;
  odd numbers on the positive-Y row. Alignment holes follow the asymmetric
  A-option drawing. Do not substitute the polarized or right-angle socket.
- Daughter: odd contacts front, even contacts back at the same physical X.
  Viewed from the back, the order is mirrored. The mating tongue is 11.77 mm
  wide; first/last contact centers are 9 mm apart. The shoulders have 1 mm
  45-degree chamfers into the tongue (above the socket cavity in the boot). Pads are 0.61 x 4.45 mm,
  starting 1.05 mm back from the tip. No solder paste on fingers.
- Mating PCB thickness: 1.57 +/-0.15 mm. Samtec specifies a 30 +/-5 degree
  bevel to a 0.61 mm tip and hard-gold fingers (30 microinch specification).
  **Prototypes deliberately use standard 1.6 mm ENIG with no bevel**, plus a
  hand-chamfered tip and a thickness check (see LAYOUT-PLAN.md, Fabrication
  sourcing). That trades insertion life for a cheap, fast build. The hard-gold
  spec is deferred until Babel moves toward a product.
- The NP socket is not an orientation key or a retention latch. A keyed carrier
  must block reversed insertion before electrical contact and retain the card;
  its CAD is now in ../mechanical/daughter_carrier.scad. Analytical clearance
  checks pass; rendering/print/fit tests remain open. Do not operate loose cards.
- Equal-length contacts do not provide guaranteed ground-first/presence-last
  sequencing. Prototype module changes require system power OFF. Keep the
  hardware gating for later insertion/removal qualification.

Sources: [Samtec part](https://www.samtec.com/products/mec1-110-02-l-d-np-a),
[socket and mating-card drawing, revision R](https://suddendocs.samtec.com/prints/mec1-1xx-xx-xx-d-xx-xx-footprint.pdf).
The manufacturer page exposed quantity-one pricing but zero distributor stock
during review: procurement/lead time is NOT confirmed. No order has been placed.

Other selected patterns: Omron B3U-1000P buttons; C&K JS102011SAQN slide switch
(center pin 2 to regulator EN, pin 1 to permission, pin 3 to ground); Coilcraft
XFL4020-152MEC inductor; TI TPS63070 RNM0015A custom fifteen-pad pattern.
The RNM pattern includes mask-defined power lands and split paste apertures;
it has no invented sixteenth exposed pad. Source is the
[TI package drawing](https://www.ti.com/lit/ds/symlink/tps63070.pdf), 4222000/B.

`tools/generate_footprints.py` writes shared `hardware/Babel.pretty`; both boards
reference it. The layout-seed checker adds critical dimension checks to the
pad-identifier audit. Custom patterns have been screened against the drawings;
solderability and fabricated mating remain untested. BQ24079 now uses the exact
RGT0016B pattern with 1.6 mm exposed pad, not the RGT-C 1.68 mm pattern.
OLED cable and CAD envelope are in DISPLAY-INTEGRATION.md.
Battery needs an insulated, puncture-resistant compartment and expansion room;
the design envelope and keepouts are set in ../LAYOUT-PLAN.md and both PCB seeds.
The assembled palm-size stack and RF behavior have not yet been verified.
