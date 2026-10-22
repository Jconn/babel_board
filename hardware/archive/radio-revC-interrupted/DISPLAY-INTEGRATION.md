# OLED module integration

Use the complete Adafruit 4741 breakout, configured for SPI by cutting its J1/J2
jumpers. Babel J2 is a JST B8B-PH-K-S header with PHR-8 mating housing; this is a
custom seven-wire cable, NOT a straight-through cable or direct module socket.
Identify pin 1 from each actual connector/drawing, not wire colors or viewing side.

| Babel J2 | Signal | Adafruit JP2 pad |
| --- | --- | --- |
| 1 | 3.3 V supply to Vin | 7 VCC |
| 2 | Ground | 8 GND |
| 3 | SPI clock | 2 SCL |
| 4 | SPI MOSI | 1 SDA |
| 5 | Chip select | 5 CS |
| 6 | Data/command | 3 DC/SA0 |
| 7 | Reset | 4 RST |
| 8 | No connection | None |

Leave module JP2 pad 6 (3Vo) disconnected: it is the module regulator's OUTPUT.
Check cable continuity and absence of shorts before connecting either board.
The module header has 2.54 mm pitch; the Babel connector has 2.00 mm pitch.

## CAD-derived envelope

Authoritative source: [Adafruit OLED PCB repository](https://github.com/adafruit/Adafruit-Grayscale-1.5-inch-128x128-OLED-PCB),
commit `a48daa304b9d13a8d1f4ab29866c116abd44727d`, preserved with its license in
`hardware/reference/adafruit-oled-4741`. No circuit artwork is copied here.

The Eagle board outline is 35.56 x 46.99 mm including mounting tabs. Four mounting
holes have 2.5 mm drills, on a 30.48 x 41.91 mm rectangular pattern. Relative to
the lower-left outline corner, hole centers are (2.54, 2.54), (33.02, 2.54),
(2.54, 44.45), (33.02, 44.45), in mm. These dimensions describe the breakout PCB,
not a verified enclosure opening, display viewing area or assembled stack height.

Before layout release, verify a physical module against the CAD revision, measure
the display/connector stack height, choose standoffs and cable strain relief,
and check battery clearance plus the WROOM antenna keepout. Do not place screws,
solder joints or connector pins against the pouch. Measure worst-case OLED power
with a bright full-screen pattern and concurrent radio operation.
