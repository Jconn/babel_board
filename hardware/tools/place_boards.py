"""Apply the reviewed block placement to the radio and IR daughter boards.

Run with AppDir/bin/python3.11 from the repository root. Only moves footprints
named in the tables; locked interface anchors and holes are never touched. It
refuses to touch a board once tracks exist, because moving parts would break
routing. Edit these tables (not the boards by hand) until placement is frozen
for routing; after that, KiCad is the source of truth and this script retires.
"""
from pathlib import Path
import argparse
import pcbnew as k

HW = Path(__file__).resolve().parents[1]

# ref: (x mm, y mm, rotation deg). All top side (single-sided assembly).
RADIO = {
    # Compact debug additions; outlines and existing anchors are unchanged.
    'R125': (55.0, 53.4, 90), 'R126': (8.0, 31.2, 90), 'R127': (5.0, 13.3, 0),
    **{f'TP{i}': (x,y,0) for i,(x,y) in enumerate([
        (2,24),(5,24),(2,26.6),(5,26.6),(2,29.2),(5,29.2),
        (2,31.8),(5,31.8),(2,34.4),(5,34.4),(2,37),(5,37),
        (57.6,25),(57.6,27.6),(57.6,30.2),(57.6,32.8),
        (57.6,48.4),(57.6,51),(57.6,53.6),(7.8,10),(4,60.1),(54,38),
    ],17)},
    # --- Daughter port bus, below the J1 boot envelope (y > 13) ---
    # Connector-side ESD row, ordered to match J1 contact columns.
    'U30': (21.2, 15.0, 0), 'U31': (24.4, 15.0, 0), 'U32': (27.6, 15.0, 0),
    'U33': (30.8, 15.0, 0), 'U34': (34.0, 15.0, 0), 'U35': (37.2, 15.0, 0),
    'U36': (40.4, 15.0, 0),
    # Daughter-side pull-ups (VDD_DAUGHTER), clear of the H7 OLED standoff.
    'R31': (18.6, 18.0, 90), 'R32': (20.25, 18.0, 90), 'R33': (21.9, 18.0, 90),
    'R34': (23.55, 18.0, 90), 'R35': (17.2, 21.2, 90), 'R36': (18.85, 21.2, 90),
    'R37': (20.5, 21.2, 90), 'R38': (22.15, 21.2, 90),
    # Isolation switches: rot 90 puts daughter B pins up, host A pins down.
    # U13 drops below the H8 standoff body; C24/C25 sit at each VCC pin.
    'U12': (30.1, 20.3, 90), 'C24': (25.5, 18.6, 90),
    'U13': (39.3, 24.1, 90), 'C25': (34.75, 22.0, 90),
    'U14': (51.5, 21.5, 90), 'C26': (57.2, 19.0, 90),
    # Daughter supply switch, left of the boot; VDD_DAUGHTER runs inner layer.
    'U11': (5.0, 17.0, 0), 'R29': (5.0, 20.4, 0), 'C22': (1.6, 17.0, 90),
    'C23': (8.6, 17.0, 90), 'R30': (8.6, 20.6, 90),
    # --- Display connector support ---
    'C4': (11.0, 30.2, 0), 'R4': (18.0, 30.0, 0), 'R5': (21.6, 30.0, 0),
    # --- Port enable logic ---
    'U5': (27.2, 31.2, 0), 'C16': (30.6, 31.2, 90),
    'U6': (34.0, 31.2, 0), 'C17': (37.4, 31.2, 90),
    'U7': (40.8, 31.2, 0), 'C18': (44.2, 31.2, 90),
    'U8': (27.2, 35.0, 0), 'C19': (30.6, 35.0, 90),
    'U9': (34.0, 35.0, 0), 'C20': (37.4, 35.0, 90),
    'U10': (40.8, 35.0, 0), 'C21': (44.2, 35.0, 90),
    'R21': (28.6, 38.6, 0), 'R22': (31.8, 38.6, 0), 'R23': (35.0, 38.6, 0),
    'R24': (38.2, 38.6, 0), 'R25': (28.6, 40.3, 0), 'R26': (31.8, 40.3, 0),
    'R27': (35.0, 40.3, 0), 'R28': (38.2, 40.3, 0),
    # --- USB entry, CC policy and data path, beside J4 ---
    'U24': (9.0, 37.9, 0), 'U15': (12.0, 37.9, 0), 'C102': (12.0, 34.9, 0),
    'R101': (12.0, 32.6, 0), 'R100': (15.6, 34.9, 0),
    'F1': (8.6, 41.6, 90), 'D3': (12.4, 44.2, 270),
    'U2': (8.75, 45.0, 90), 'U19': (8.6, 48.6, 180), 'C104': (11.0, 50.5, 90),
    'U16': (17.0, 38.2, 0), 'C100': (20.3, 38.2, 90), 'C101': (20.3, 34.9, 0),
    'U18': (17.0, 42.0, 0), 'C109': (17.0, 45.0, 0),
    'U17': (21.8, 42.0, 0), 'C103': (25.1, 42.0, 90), 'R102': (25.1, 46.0, 90),
    # --- Charger ---
    'U3': (22.0, 51.0, 0), 'C5': (22.0, 47.7, 0), 'C6': (18.6, 51.0, 90),
    'C7': (25.6, 51.0, 90), 'R12': (15.5, 49.5, 0), 'R108': (15.5, 51.3, 0),
    'R109': (15.5, 53.1, 0), 'R14': (15.5, 54.9, 0), 'R90': (19.0, 54.9, 0),
    'R13': (22.4, 54.6, 0), 'R15': (25.9, 54.6, 0), 'R16': (29.2, 54.6, 0),
    # --- Charge guard (NTC window and battery-OK) ---
    'U20': (30.6, 44.0, 0), 'C105': (30.6, 47.0, 0),
    'R103': (34.0, 44.0, 90), 'R104': (35.8, 44.0, 90), 'R105': (37.6, 44.0, 90),
    'R106': (39.4, 44.0, 90), 'R107': (41.2, 44.0, 90), 'R110': (43.0, 44.0, 90),
    'U22': (30.6, 50.6, 0), 'C106': (34.0, 50.6, 90),
    'U23': (37.4, 50.6, 0), 'C107': (40.8, 50.6, 90),
    'U21': (46.6, 64.0, 0), 'C108': (46.6, 67.0, 0), 'R111': (49.6, 64.0, 90),
    'R112': (49.6, 67.4, 90), 'R113': (46.6, 69.2, 0), 'D1': (46.4, 71.6, 0),
    'D2': (46.4, 74.4, 0), 'R114': (46.4, 77.2, 0),
    # --- Regulator, right centre ---
    'U4': (49.0, 46.0, 0), 'L1': (53.2, 46.0, 270),
    # 0603 hot-loop caps directly on VIN / VOUT pins; GND pads via to In1.
    'C11': (49.8, 42.9, 0), 'C15': (49.8, 49.1, 0),
    'C9': (47.4, 40.0, 0), 'C10': (51.2, 40.0, 0),
    'C12': (47.4, 52.6, 0), 'C13': (51.2, 52.6, 0), 'C14': (47.4, 55.0, 0),
    'C8': (45.9, 46.4, 270), 'R124': (45.6, 43.3, 0),
    'R18': (45.6, 49.0, 0), 'R17': (45.6, 50.7, 0),
    'R19': (53.4, 57.0, 0), 'R20': (50.0, 57.0, 0),
    # --- Host module support ---
    'R8': (41.5, 62.9, 0), 'R9': (41.5, 64.6, 0), 'R1': (41.5, 66.5, 0),
    'C1': (41.5, 68.8, 0), 'C2': (41.5, 72.6, 0), 'C3': (41.5, 75.6, 0),
    'R2': (17.6, 64.6, 90), 'R3': (17.6, 75.6, 90),
    'R10': (37.0, 57.0, 0), 'R11': (23.0, 57.6, 0),
    'R120': (34.2, 57.1, 90), 'R121': (32.55, 57.1, 90),
    'R122': (30.9, 57.1, 90), 'R123': (29.25, 57.1, 90),
    'J3': (12.2, 64.0, 0),
    # --- Test pads: outside the OLED footprint so probes reach them ---
    'TP1': (1.4, 52.3, 0), 'TP2': (4.0, 52.3, 0), 'TP3': (6.6, 52.3, 0),
    'TP4': (1.4, 54.9, 0), 'TP5': (4.0, 54.9, 0), 'TP6': (6.6, 54.9, 0),
    'TP11': (1.4, 57.5, 0), 'TP12': (4.0, 57.5, 0), 'TP13': (6.6, 57.5, 0),
    'TP16': (1.4, 60.1, 0),
    'TP14': (2.0, 10.0, 0), 'TP15': (5.0, 10.0, 0),
    'TP7': (57.6, 38.0, 0), 'TP8': (57.6, 40.6, 0), 'TP9': (57.6, 43.2, 0),
    'TP10': (57.6, 45.8, 0),
}

# Daughter: sensor/optical zone (x5..35, y10..25) holds only U1 and C1.
# EEPROM, pull-ups and port capacitor sit by the card tongue; front side only,
# carrier behind. J2 is a 2x4 bench header (pin 1 bottom-left), clear of carrier holes H1/H2.
DAUGHTER = {
    'C1': (16.6, 15.6, 270),
    'U2': (13.0, 30.0, 0), 'C2': (17.6, 28.0, 90), 'R1': (20.5, 30.6, 0),
    'C3': (20.5, 33.5, 0), 'R6': (21.2, 26.6, 0),
    # R2..R5 are DNP bench pull-ups.
    'R2': (24.0, 26.9, 90), 'R3': (25.7, 26.9, 90),
    'R4': (27.4, 26.9, 90), 'R5': (29.1, 26.9, 90),
    'J2': (25.5, 33.14, 90),
}

BOARDS = {
    'radio': (HW / 'radio' / 'babel-radio.kicad_pcb', RADIO),
    'daughter': (HW / 'ir-daughter' / 'babel-ir-daughter.kicad_pcb', DAUGHTER),
}


def apply(path, table):
    b = k.LoadBoard(str(path))
    if len(list(b.GetTracks())):
        raise SystemExit(f'{path} has tracks; placement table must not move routed parts')
    fps = {f.GetReference(): f for f in b.GetFootprints()}
    missing = [r for r, f in fps.items() if not f.IsLocked() and not r.startswith('H') and r not in table]
    for ref, (x, y, a) in table.items():
        f = fps[ref]
        assert not f.IsLocked(), f'{ref} is a locked anchor'
        f.SetOrientationDegrees(a)
        f.SetPosition(k.VECTOR2I(k.FromMM(x), k.FromMM(y)))
    k.SaveBoard(str(path), b)
    print(f'{path.name}: placed {len(table)} footprints; unplaced: {sorted(missing) or "none"}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('board', choices=sorted(BOARDS))
    ap.add_argument('--out', help='write to this board file instead (review copy)')
    args = ap.parse_args()
    path, table = BOARDS[args.board]
    if args.out:
        import shutil
        shutil.copyfile(path, args.out)
        path = Path(args.out)
    apply(path, table)
