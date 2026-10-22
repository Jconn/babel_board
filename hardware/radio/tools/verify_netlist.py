"""Check KiCad export plus independent critical pin and connector requirements.

The generated manifest detects dropped/misjoined schematic wires. The hardcoded
checks below are independent of the generator and guard the electrical contract.
This is not a circuit simulator, footprint check, or proof of hot-swap safety.
"""
from pathlib import Path
import json
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
xml=ET.parse(ROOT/'babel-radio.net.xml')
actual, nc={},set()
for net in xml.findall('./nets/net'):
    for node in net.findall('node'):
        key=f"{node.attrib['ref']}.{node.attrib['pin']}"
        assert key not in actual and key not in nc,key
        if 'no_connect' in node.attrib.get('pintype',''): nc.add(key)
        else: actual[key]=net.attrib['name'].lstrip('/')
manifest=json.loads((ROOT/'expected-nets.json').read_text())
expected={k:v for k,v in manifest['connected'].items() if not k.startswith('#')}
assert actual==expected, f'Export mismatch: {set(actual.items()) ^ set(expected.items())}'
assert nc==set(manifest['nc']),f'NC mismatch: {nc ^ set(manifest["nc"])}'

def pin(ref,number,net):
    assert actual.get(f'{ref}.{number}')==net,(ref,number,net,actual.get(f'{ref}.{number}'))
def mapping(ref,pins):
    for number,net in pins.items(): pin(ref,number,net)

mapping('U1',{1:'GND',2:'V3V3',3:'CHIP_EN',40:'GND',41:'GND',
    4:'H_NVM_SCL',5:'H_NVM_SDA',6:'H_NVM_WP',7:'H_SENSOR_SCL',12:'H_SENSOR_SDA',
    8:'H_SENSOR_IRQ_N',
    10:'PWR_REQ',11:'NVM_REQ',23:'SENSOR_REQ',38:'PRESENT_N',31:'PORT_FAULT_N',
    13:'USB_DM_MCU',14:'USB_DP_MCU',15:'STRAP3_LOW',26:'STRAP45_LOW',27:'BOOT_N',
    32:'LCD_SCK',33:'LCD_MOSI',34:'LCD_CS_N',35:'LCD_DC',24:'LCD_RESET_N',
    39:'BUTTON_N',25:'USB_PGOOD_N',36:'DEBUG_RX',37:'DEBUG_TX'})
# GPIO9-14/16 freed when the SPI/UART/RESET contacts left the connector.
assert {f'U1.{x}' for x in [16,28,29,30, 9,17,18,19,20,21,22]} <= nc
port=['GND','GND','VDD_DAUGHTER','SENSOR_IRQ_N','NVM_SCL','NVM_SDA','NVM_WP',
      'PRESENT_N','SENSOR_SCL','SENSOR_SDA','SENSOR_SDA','SENSOR_SCL','PRESENT_N',
      'NVM_WP','NVM_SDA','NVM_SCL','SENSOR_IRQ_N','VDD_DAUGHTER','GND','GND']
mapping('J1',dict(enumerate(port,1)))
# Reversible insertion: a reversed card puts its contact n on socket contact 21-n.
assert all(port[n-1]==port[20-n] for n in range(1,21))
# Selected Jauch 251555 pack drawing: red / yellow NTC / black.
mapping('J5',{1:'VBAT',2:'PACK_NTC',3:'GND'})
# Babel adapter header, NOT the module's physical pin numbering.
mapping('J2',{1:'V3V3_OLED',2:'GND',3:'LCD_SCK',4:'LCD_MOSI',5:'LCD_CS_N',6:'LCD_DC',7:'LCD_RESET_N'})
assert 'J2.8' in nc
# Compare current daughter export: presence is deliberately grounded there.
daughter=ET.parse(ROOT.parent/'ir-daughter/babel-ir-daughter.net.xml')
for net in daughter.findall('./nets/net'):
    for node in net.findall('node'):
        if node.attrib['ref']!='J1' or 'no_connect' in node.attrib.get('pintype',''): continue
        number=int(node.attrib['pin']); want='GND' if number==8 else port[number-1]
        assert net.attrib['name'].lstrip('/')==want,(number,want)

mapping('U3',{1:'CHG_TS_FIXED',2:'VBAT',3:'VBAT',4:'CHARGE_DISABLE',5:'USB_ALLOW',6:'GND',
    7:'USB_PGOOD_N',8:'GND',9:'CHG_N',10:'SYS_RAW',11:'SYS_RAW',12:'CHG_ILIM',13:'USB_CHG_IN',14:'CHG_TMR',15:'GND',16:'CHG_ISET',17:'GND'})
mapping('U4',{1:'REG_PS',2:'REG_PG',3:'REG_AUX',4:'GND',5:'REG_FB',7:'V3V3_REG',8:'V3V3_REG',
    9:'REG_L2',10:'GND',11:'REG_L1',12:'SYS_RAW',13:'SYS_RAW',14:'REG_EN',15:'GND'})
mapping('L1',{1:'REG_L1',2:'REG_L2'})
mapping('R124',{1:'SYS_RAW',2:'REG_PS'})
mapping('U11',{1:'V3V3_PORT_IN',2:'GND',3:'PORT_EN',4:'PORT_FAULT_N',5:'PORT_ILIM',6:'VDD_DAUGHTER'})
mapping('U5',{2:'PRESENT_N',4:'PRESENT'})
mapping('U6',{1:'PRESENT',2:'PWR_REQ',4:'PORT_EN'})
mapping('U7',{1:'PORT_EN',2:'NVM_REQ',4:'NVM_ENABLE'})
mapping('U8',{2:'NVM_ENABLE',4:'NVM_OE_N'})
mapping('U9',{1:'PORT_EN',2:'SENSOR_REQ',4:'SENSOR_ENABLE'})
mapping('U10',{2:'SENSOR_ENABLE',4:'SENSOR_OE_N'})
for ref in ['U5','U6','U7','U8','U9','U10']: mapping(ref,{3:'GND',5:'V3V3'})
for ref,oe,names in [('U12','NVM_OE_N',port[4:7]),('U13','SENSOR_OE_N',['SENSOR_SCL','SENSOR_SDA','SENSOR_IRQ_N'])]:
    mapping(ref,{10:'GND',19:oe,20:'V3V3'})
    for i,name in enumerate(names): mapping(ref,{i+2:'H_'+name,18-i:name})
    assert f'{ref}.1' in nc
for ref,net in [('R31','NVM_SCL'),('R32','NVM_SDA'),('R33','SENSOR_SCL'),('R34','SENSOR_SDA'),
                ('R35','NVM_WP'),('R37','SENSOR_IRQ_N')]:
    mapping(ref,{1:'VDD_DAUGHTER',2:net})
assert {f'U13.{n}' for n in [5,6,7,8,9,11,12,13,14,15]} <= nc
mapping('R8',{1:'USB_DP_LINK',2:'USB_DP_MCU'});mapping('R9',{1:'USB_DM_LINK',2:'USB_DM_MCU'})
mapping('U2',{1:'USB_DP',2:'USB_DM',3:'GND'})
mapping('F1',{1:'USB_VBUS_RAW',2:'USB_5V'})
mapping('D3',{1:'USB_5V',2:'GND'})
for num in ['A1','A12','B1','B12','SH']: pin('J4',num,'GND')
for num in ['A4','A9','B4','B9']: pin('J4',num,'USB_VBUS_RAW')
mapping('J4',{'A5':'CC1','B5':'CC2','A6':'USB_DP','B6':'USB_DP','A7':'USB_DM','B7':'USB_DM'})
mapping('U15',{1:'CC1',2:'CC2',3:'GND',4:'CC_VBUS_DET',7:'CC_HIGH_N',10:'GND',11:'GND',12:'V3V3_CC'})
assert {f'U15.{n}' for n in [5,6,8,9]} <= nc
mapping('U16',{1:'USB_5V',2:'GND',5:'V3V3_CC'})
assert {'U16.3','U16.4'} <= nc  # TPS709 EN may float high; NOT another LDO variant.
mapping('U17',{2:'CC_HIGH_N',3:'GND',4:'USB_ALLOW',5:'V3V3_CC'})
mapping('U18',{1:'USB_5V',2:'GND',3:'USB_ALLOW',4:'USB_SLEW',5:'USB_CHG_IN',6:'USB_CHG_IN'})
mapping('C109',{1:'USB_SLEW',2:'GND'})
mapping('U19',{1:'USB_DP_LINK',2:'USB_DM_LINK',5:'GND',6:'CC_HIGH_N',7:'USB_DM',8:'USB_DP',9:'GND',10:'V3V3_CC'})
assert {'U19.3','U19.4'} <= nc
mapping('U21',{1:'BAT_OK',2:'GND',3:'BAT_SENSE',4:'GND',5:'SYS_RAW'})
mapping('U20',{1:'TEMP_OK',2:'GND',3:'TEMP_HOT_SENSE',4:'TEMP_COLD_SENSE',5:'V3V3_CC',6:'TEMP_OK'})
mapping('U22',{1:'TEMP_OK',2:'USB_ALLOW',3:'GND',4:'CHARGE_ALLOWED',5:'V3V3_CC'})
mapping('U23',{2:'CHARGE_ALLOWED',3:'GND',4:'GUARD_DISABLE',5:'V3V3_CC'})
for ref,a,b in [('R14','SYS_RAW','CHARGE_DISABLE'),('R90','CHARGE_DISABLE','GUARD_DISABLE'),
    ('R103','V3V3_CC','PACK_NTC'),('R104','PACK_NTC','TEMP_HOT_SENSE'),
    ('R105','TEMP_HOT_SENSE','GND'),('R106','PACK_NTC','TEMP_COLD_SENSE'),
    ('R107','TEMP_COLD_SENSE','GND'),('R108','CHG_TMR','GND'),
    ('R109','CHG_TS_FIXED','GND'),('R110','V3V3_CC','TEMP_OK')]: mapping(ref,{1:a,2:b})
assert 'U21.6' in nc
for ref, a, b in [('R100','USB_5V','CC_VBUS_DET'),('R101','V3V3_CC','CC_HIGH_N'),
    ('R102','USB_ALLOW','GND'),
    ('R111','VBAT','BAT_SENSE'),('R112','BAT_SENSE','GND'),('R113','VBAT','BAT_OK'),
    ('R114','POWER_AVAILABLE','GND')]: mapping(ref,{1:a,2:b})
mapping('D1',{1:'POWER_AVAILABLE',2:'BAT_OK'});mapping('D2',{1:'POWER_AVAILABLE',2:'USB_ALLOW'})
mapping('SW4',{1:'POWER_AVAILABLE',2:'REG_EN',3:'GND'})
mapping('U24',{1:'CC1',2:'CC2',3:'GND'})
for i,pair in enumerate([('NVM_SCL','NVM_SDA'),('NVM_WP','PRESENT_N'),('SENSOR_SCL','SENSOR_SDA')]):
    mapping(f'U{30+i}',{1:pair[0],2:pair[1],3:'GND'})
mapping('U33',{1:'SENSOR_IRQ_N',3:'GND'}); assert 'U33.2' in nc
parts={c.attrib['ref']:c for c in xml.findall('./components/comp')}
assert 'R6' not in parts and 'R7' not in parts  # No duplicate CC pulldowns.
# Retired with the SPI/UART/RESET contacts; their numbers stay unused.
assert not {'U14','C26','R36','R38','R120','R121','R122','R123','U34','U35','U36'} & set(parts)
assert parts['U3'].findtext('value')=='BQ24079RGTR / 4.1V'
assert parts['U18'].findtext('value')=='TPS22810DBVR'
assert parts['U23'].findtext('value')=='SN74LVC1G06DBVR'  # Open drain, not push-pull.
for ref,value in {'U20':'TPS3700DDCR','U22':'SN74LVC1G08DBVR',
                  'U16':'TPS70933DBVR'}.items():
    assert parts[ref].findtext('value')==value,(ref,value)
for ref,value in {'R103':'10k 0.1%','R104':'200k 0.1%','R105':'100k 0.1%',
    'R106':'412k 0.1%','R107':'100k 0.1%','R108':'71.5k 0.1%',
    'R109':'10k / external NTC guard used','R14':'10k / disable default'}.items():
    assert parts[ref].findtext('value')==value,(ref,value)
for ref,value in {'R13':'1.78k 1% / 904mA','R111':'732k 0.1%','R112':'100k 0.1%'}.items():
    assert parts[ref].findtext('value')==value,(ref,value)
dnps={ref for ref,c in parts.items() if any(p.attrib.get('name')=='dnp' for p in c.findall('property'))}
assert dnps=={'R90'},dnps
assert parts['R29'].findtext('value')=='226k 1%'
assert parts['R12'].findtext('value')=='5.36k 1% / 166mA'
# TI maximum current factor and minimum 1% resistor, conservatively using
# the pack's MINIMUM 950mAh capacity for its cold-temperature 0.2C limit.
assert 975 / (5360 * 0.99) < 0.2 * 0.950
assert parts['R17'].findtext('value')=='470k 1%'
assert parts['R18'].findtext('value')=='150k 1%'
assert len(xml.findall('./design/sheet'))==10
print(f'PASS: {len(actual)} connected pads, {len(nc)} intentional NCs, {len(parts)} components; critical pin maps and IR J1 agree.')

# Debug access is an independently asserted contract, not only manifest parity.
for ref, a, b in [('R125','V3V3_REG','V3V3'), ('R126','V3V3','V3V3_OLED'),
                  ('R127','V3V3','V3V3_PORT_IN')]:
    mapping(ref,{1:a,2:b})
    assert parts[ref].findtext('value') == '0R / removable current link'
for ref in ('C12','C13','C14','C15'): mapping(ref,{1:'V3V3_REG',2:'GND'})
mapping('R17',{1:'V3V3_REG',2:'REG_FB'})
mapping('C4',{1:'V3V3_OLED',2:'GND'})
mapping('C22',{1:'V3V3_PORT_IN',2:'GND'})
for i,net in enumerate(['GND','USB_5V','USB_CHG_IN','VBAT','SYS_RAW','CHG_N',
    'GND','V3V3','REG_EN','REG_PG','PACK_NTC','TEMP_OK','CHARGE_DISABLE',
    'VDD_DAUGHTER','PORT_EN','USB_ALLOW','H_NVM_SCL','H_NVM_SDA','H_NVM_WP',
    'H_SENSOR_SCL','H_SENSOR_SDA','NVM_OE_N','SENSOR_OE_N','PORT_FAULT_N',
    'PRESENT_N','GND','V3V3_CC','CC_HIGH_N','USB_PGOOD_N','BAT_OK',
    'POWER_AVAILABLE','GND','GND','GND','V3V3_REG','GND','GND','GND'],1):
    pin(f'TP{i}',1,net)
assert len(parts)==168
print('PASS: 38 radio probe pads and three removable power links; regulator FB remains upstream.')
