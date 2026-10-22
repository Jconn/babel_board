"""Check assigned local-library footprint existence and pad-number sets.

Does NOT verify dimensions, manufacturing suitability, or part orientation.
Blank footprints are reported as explicit remaining layout blockers.
"""
from pathlib import Path
import csv
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT.parent.parent/'AppDir/share/kicad/footprints'
xml = ET.parse(ROOT/'babel-radio.net.xml')
pins = {}
for net in xml.findall('./nets/net'):
    for node in net.findall('node'):
        pins.setdefault(node.attrib['ref'],set()).add(node.attrib['pin'])
checked, blanks = 0, []
for part in csv.DictReader((ROOT/'bom.csv').open()):
    ref, fp = part['Reference'], part['Footprint']
    if not fp:
        blanks.append(ref)
        continue
    library, name = fp.split(':')
    base = ROOT.parent/'Babel.pretty' if library=='Babel' else LIB/(library+'.pretty')
    path = base/(name+'.kicad_mod')
    assert path.is_file(), (ref,path)
    pads=set(re.findall(r'\(pad\s+"([^"]+)"',path.read_text()))
    assert pins[ref] == pads, (ref, 'symbol pads', pins[ref], 'footprint pads', pads)
    checked += 1
print(f'PASS: {checked} assigned footprints exist and have matching pad-number sets.')
print('OPEN footprint selections: '+', '.join(blanks))
assert not blanks, 'Prototype requires every radio footprint assigned'
