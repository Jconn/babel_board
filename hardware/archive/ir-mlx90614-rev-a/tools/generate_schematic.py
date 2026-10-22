"""Generate the initial, self-contained schematic. Overwrites generated files.

Use only before hand editing the schematic, or review generated differences.
Symbols are project-specific, with pin numbers taken from manufacturer datasheets.
"""
from pathlib import Path
import csv
import json
import uuid

ROOT = Path(__file__).resolve().parents[1]
NAME = "babel-ir-daughter"
UID = lambda key: str(uuid.uuid5(uuid.NAMESPACE_URL, "babel/ir-daughter/" + key))
Q = lambda text: json.dumps(str(text))


def effects(size=1.0, hidden=False):
    return f'(effects (font (size {size} {size})) {"(hide yes)" if hidden else ""})'


def prop(name, value, x=0, y=0, hidden=False, left=False):
    style=effects(1.0, hidden)
    if left:
        style=style[:-1]+' (justify left))'
    return f'(property {Q(name)} {Q(value)} (at {x} {y} 0) {style})'


# Pin: number, name, electrical type, local x/y, orientation.
sensor = [(1,"SCL","input",-12.7,2.54,0),
          (2,"SDA/PWM","bidirectional",-12.7,-2.54,0),
          (3,"VDD","power_in",0,10.16,270),
          (4,"VSS","power_in",0,-10.16,90)]
memory = [(1,"A0","input",-12.7,5.08,0),
          (2,"A1","input",-12.7,0,0),
          (3,"A2","input",-12.7,-5.08,0),
          (4,"VSS","power_in",0,-12.7,90),
          (5,"SDA","bidirectional",12.7,0,180),
          (6,"SCL","input",12.7,5.08,180),
          (7,"WP","input",12.7,-5.08,180),
          (8,"VCC","power_in",0,12.7,270)]
connector = [(n,str(n),"passive",-15.24 if n % 2 else 15.24,
              11.43-((n-1)//2)*2.54,0 if n % 2 else 180) for n in range(1,21)]
passive = [(1,"~","passive",0,3.81,270),(2,"~","passive",0,-3.81,90)]
definitions = {}
pins = {}


def symbol(name, reference, pinlist, body):
    pins[name] = pinlist
    pintext = ''.join(f'''(pin {typ} line (at {x} {y} {angle}) (length {0 if name in ('TP','PWR_FLAG') else 2.54})
        (name {Q(label)} {effects()}) (number {Q(num)} {effects()}))'''
        for num,label,typ,x,y,angle in pinlist)
    definitions[name] = f'''(symbol {Q(name)} (pin_names (offset 0.508) {'(hide yes)' if name == 'PORT_20' else ''})
      (in_bom yes) (on_board yes)
      {prop('Reference',reference)} {prop('Value',name)}
      {prop('Footprint','',hidden=True)} {prop('Datasheet','',hidden=True)}
      (symbol {Q(name+'_0_1')} {body})
      (symbol {Q(name+'_1_1')} {pintext}))'''


def rect(x,y):
    return f'(rectangle (start {-x} {y}) (end {x} {-y}) (stroke (width 0.254) (type default)) (fill (type background)))'


symbol('MLX90614_BCC','U',sensor,rect(10.16,7.62))
symbol('24LC256','U',memory,rect(10.16,10.16))
symbol('PORT_20','J',connector,rect(12.7,15.24))
symbol('R','R',passive,rect(1.016,1.27))
symbol('C','C',passive,''.join(f'(polyline (pts (xy -2.54 {y}) (xy 2.54 {y})) (stroke (width 0.254) (type default)) (fill (type none)))' for y in [-1.27,1.27]))
symbol('TP','TP',[(1,'~','passive',0,0,90)],'(circle (center 0 1.27) (radius 1.27) (stroke (width 0.254) (type default)) (fill (type none)))')
symbol('PWR_FLAG','#FLG',[(1,'~','power_out',0,0,90)],'(polyline (pts (xy 0 0) (xy 0 2.54) (xy -1.27 3.81) (xy 0 5.08) (xy 1.27 3.81) (xy 0 2.54)) (stroke (width 0.254) (type default)) (fill (type none)))')

items=[]
components=[]
expected={}
counter=0


def wire(x,y,xx,yy):
    global counter
    counter+=1
    items.append(f'(wire (pts (xy {x} {y}) (xy {xx} {yy})) (stroke (width 0) (type default)) (uuid {Q(UID("wire"+str(counter)))}))')


def label(net,x,y,leftward=False):
    global counter
    counter+=1
    items.append(f'(label {Q(net)} (at {x} {y} {180 if leftward else 0}) (effects (font (size 1 1)) (justify {"right" if leftward else "left"} bottom)) (uuid {Q(UID("label"+str(counter)))}))')


def text(value,x,y,size=1.1):
    items.append(f'(text {Q(value)} (at {x} {y} 0) (effects (font (size {size} {size})) (justify left top)) (uuid {Q(UID("text"+str(x)+str(y)))}))')


def place(kind,ref,value,x,y,nets,dnp=False,footprint='',datasheet=''):
    instance=UID(ref)
    # Keep power names hidden; draw them with explicitly connected net labels.
    properties=prop('Reference',ref,x+4,y-1.5,ref.startswith('#'),True)+prop('Value',value,x+4,y+1.5,ref.startswith('#') or kind=='TP',True)
    if kind in ('MLX90614_BCC','24LC256','PORT_20'):
        properties=prop('Reference',ref,x,y-26)+prop('Value',value,x,y-23)
    properties+=prop('Footprint',footprint,x,y,True)+prop('Datasheet',datasheet,x,y,True)
    items.append(f'''(symbol (lib_id {Q('Babel_IR:'+kind)}) (at {x} {y} 0) (unit 1)
       (in_bom {'no' if ref.startswith('#') else 'yes'}) (on_board {'no' if ref.startswith('#') else 'yes'}) (dnp {'yes' if dnp else 'no'})
       (uuid {Q(instance)}) {properties}
       (instances (project {Q(NAME)} (path {Q('/'+UID('sheet'))} (reference {Q(ref)}) (unit 1)))))''')
    for n,_,_,px,py,angle in pins[kind]:
        xx,yy=round(x+px,4),round(y-py,4)
        net=nets.get(n)
        if net is None:
            items.append(f'(no_connect (at {xx} {yy}) (uuid {Q(UID(ref+str(n)+"nc"))}))')
            continue
        expected[f'{ref}.{n}']=net
        dx,dy={0:(-5.08,0),180:(5.08,0),270:(0,-3.81),90:(0,3.81)}[angle]
        endx,endy=round(xx+dx,4),round(yy+dy,4)
        wire(xx,yy,endx,endy)
        label(net,endx,endy,dx<0)
    if not ref.startswith('#'):
        components.append([ref,value,'DNP' if dnp else 'FIT',footprint,datasheet])


MLX='https://www.melexis.com/-/media/files/documents/datasheets/mlx90614-datasheet-melexis.pdf'
EEP='https://ww1.microchip.com/downloads/aemDocuments/documents/MPD/ProductDocuments/DataSheets/24AA256-24LC256-24FC256-256K-I2C-Serial-EEPROM-DS20001203.pdf'
V='VDD_DAUGHTER'
G='GND'
text('BABEL / IR DAUGHTER / REV A - SCHEMATIC REVIEW',12,14,1.8)
text('3.3 V from protected host port. No local MCU. Portable Wasm stored in separate EEPROM.',12,19)
text('01 / HOST PORT',15,26,1.3)
text('02 / IR SENSOR',115,26,1.3)
text('03 / DRIVER MEMORY',210,26,1.3)
place('PORT_20','J1','BABEL PORT / MECHANICAL TBD',50.8,62.23,
      {1:G,2:G,3:V,4:V,5:'NVM_SCL',6:'NVM_SDA',7:'NVM_WP',8:G,9:'SENSOR_SCL',10:'SENSOR_SDA',19:G,20:G})
place('MLX90614_BCC','U1','MLX90614ESF-BCC-000-TU',139.7,60.96,
      {1:'SENSOR_SCL',2:'SENSOR_SDA',3:V,4:G},datasheet=MLX)
place('24LC256','U2','24LC256-I/SN / 32 KiB',228.6,60.96,
      {1:G,2:G,3:G,4:G,5:'NVM_SDA',6:'NVM_SCL',7:'NVM_WP',8:V},
      footprint='Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',datasheet=EEP)
text('Pin 8 = PRESENT_N, strapped to GND.\nPins 11-18 unused on this sensor board.\nPin numbering is a draft electrical assignment;\nconnector footprint and mating view NOT frozen.',15,86)
text('SMBus address 0x5A; use PEC.\n35 deg FOV; keep optical aperture clear.\nPlace C1 directly at U1 pins 3/4.\n3.3 V operation: characterize supply-related bias.',115,86)
text('A0-A2 low: address 0x50.\nSeparate NVM bus; WP high protects writes.\n32 KiB is provisional until Wasm build measured.\nNo runtime data logging in driver EEPROM.',210,86)

text('04 / DECOUPLING',15,111,1.3)
for ref,val,x in [('C1','100 nF / U1',22.86),('C2','100 nF / U2',53.34),('C3','1 uF / port',83.82)]:
    place('C',ref,val,x,133.35,{1:V,2:G},footprint='Capacitor_SMD:C_0603_1608Metric')
text('05 / WRITE PROTECT + OPTIONAL BUS PULL-UPS',112,111,1.3)
for ref,val,x,net,dnp in [('R1','10k / WP',121.92,'NVM_WP',False),
                         ('R2','4.7k',152.4,'SENSOR_SCL',True),
                         ('R3','4.7k',182.88,'SENSOR_SDA',True),
                         ('R4','4.7k',213.36,'NVM_SCL',True),
                         ('R5','4.7k',243.84,'NVM_SDA',True)]:
    place('R',ref,val,x,133.35,{1:V,2:net},dnp=dnp,footprint='Resistor_SMD:R_0603_1608Metric')
text('R2-R5 DNP: host provides connector-side pull-ups to switched VDD.\nPopulate only for bench use after checking total pull-up load / rise time.',112,146)
text('06 / TEST ACCESS',15,160,1.3)
for i,net in enumerate([G,V,'SENSOR_SCL','SENSOR_SDA','NVM_SCL','NVM_SDA','NVM_WP'],1):
    place('TP',f'TP{i}',net,15.24+(i-1)*22.86,175.26,{1:net},footprint='TestPoint:TestPoint_Pad_D1.5mm')
place('PWR_FLAG','#FLG01','PWR_FLAG',243.84,158.75,{1:V})
place('PWR_FLAG','#FLG02','PWR_FLAG',269.24,158.75,{1:G})
text('Host owns current limiting, signal isolation and safe hot-swap sequencing.\nPower flags document external supply; they are not protection devices.',15,190,1)
text('DRAFT: NOT FOR FABRICATION',15,185,1.3)

lib='(kicad_symbol_lib (version 20241209) (generator "babel")\n'+ '\n'.join(definitions.values())+'\n)\n'
(ROOT/'Babel_IR.kicad_sym').write_text(lib)
cached='\n'.join(s.replace('(symbol '+Q(n), '(symbol '+Q('Babel_IR:'+n),1) for n,s in definitions.items())
sheet=f'''(kicad_sch (version 20250114) (generator "eeschema") (uuid {Q(UID('sheet'))})
 (paper "A4") (title_block (title "Babel IR daughter - schematic review") (date "2026-10-09") (rev "A-draft"))
 (lib_symbols {cached})
 {''.join(items)})\n'''
(ROOT/(NAME+'.kicad_sch')).write_text(sheet)
(ROOT/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "Babel_IR") (type "KiCad") (uri "${KIPRJMOD}/Babel_IR.kicad_sym") (options "") (descr "Babel IR project symbols")))\n')
with (ROOT/'bom.csv').open('w') as f:
    writer=csv.writer(f)
    writer.writerow(['Reference','Value','Assembly','Footprint','Datasheet'])
    writer.writerows(components)
(ROOT/'expected-nets.json').write_text(json.dumps(expected,indent=2)+'\n')
print('Generated schematic, local symbol library, BOM, and expected connectivity.')
