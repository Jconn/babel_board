"""Check KiCad-exported connectivity against the reviewed circuit requirements.

Export a fresh kicadxml netlist before running this check. Expected IC pin
assignments below are independent of the schematic generator.
"""
from pathlib import Path
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[1]
xml = ET.parse(root / 'babel-ir-th-daughter.net.xml')
actual = {}
unconnected = set()
for net in xml.findall('./nets/net'):
    for node in net.findall('node'):
        key = f"{node.attrib['ref']}.{node.attrib['pin']}"
        assert key not in actual, f'Duplicate pin: {key}'
        if 'no_connect' in node.attrib.get('pintype', ''):
            unconnected.add(key)
        else:
            actual[key] = net.attrib['name'].lstrip('/')

expected = {}
def require(net, *nodes):
    for node in nodes:
        assert node not in expected
        expected[node] = net

require('GND', 'U1.4', 'U2.1', 'U2.2', 'U2.3', 'U2.4',
        'J1.1', 'J1.2', 'J1.8', 'J1.19', 'J1.20', 'C1.2', 'C2.2', 'C3.2', 'J2.1', 'J2.8')
require('VDD_DAUGHTER', 'U1.3', 'U2.8', 'J1.3', 'J1.18',
        'C1.1', 'C2.1', 'C3.1', 'R1.1', 'R2.1', 'R3.1', 'R4.1', 'R5.1', 'J2.2')
require('SENSOR_SCL', 'U1.1', 'J1.9', 'R2.2', 'J2.3')
require('SENSOR_SDA', 'U1.2', 'J1.10', 'R3.2', 'J2.4')
require('NVM_SCL', 'U2.6', 'J1.5', 'R4.2', 'J2.5')
require('NVM_SDA', 'U2.5', 'J1.6', 'R5.2', 'J2.6')
require('NVM_WP', 'U2.7', 'J1.7', 'R1.2', 'J2.7')
assert actual == expected, f'Connectivity mismatch:\nactual={actual}\nexpected={expected}'
assert unconnected == {'J1.4'} | {f'J1.{pin}' for pin in range(11, 18)}
dnps = {c.attrib['ref'] for c in xml.findall('./components/comp')
        if any(p.attrib.get('name') == 'dnp' for p in c.findall('property'))}
assert dnps == {'R2', 'R3', 'R4', 'R5'}, f'Unexpected DNP set: {dnps}'
print(f'PASS: {len(expected)} connected pins across 7 nets, 8 intentional NC pins, 4 DNP pull-ups.')
