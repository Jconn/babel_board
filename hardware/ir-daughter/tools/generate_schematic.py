"""Generate the initial, self-contained schematic. Overwrites generated files.

Use only before hand editing the schematic, or review generated differences.
Symbols are project-specific, with pin numbers taken from manufacturer datasheets.
"""
from pathlib import Path
import csv
import json
import uuid
import xml.etree.ElementTree as ET

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
sensor = [(4,"SCL","input",-12.7,2.54,0),
          (1,"SDA","bidirectional",-12.7,-2.54,0),
          (2,"VDD","power_in",0,10.16,270),
          (3,"GND","power_in",-2.54,-10.16,90),
          (6,"EP","power_in",2.54,-10.16,90),
          (5,"ADDR","input",12.7,-2.54,180)]
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
header = [(n,str(n),"passive",-7.62 if n % 2 else 7.62,
           3.81-((n-1)//2)*2.54,0 if n % 2 else 180) for n in range(1,9)]
passive = [(1,"~","passive",0,3.81,270),(2,"~","passive",0,-3.81,90)]
definitions = {}
pins = {}


def symbol(name, reference, pinlist, body):
    pins[name] = pinlist
    pintext = ''.join(f'''(pin {typ} line (at {x} {y} {angle}) (length {0 if name == 'PWR_FLAG' else 2.54})
        (name {Q(label)} {effects()}) (number {Q(num)} {effects()}))'''
        for num,label,typ,x,y,angle in pinlist)
    definitions[name] = f'''(symbol {Q(name)} (pin_names (offset 0.508) {'(hide yes)' if name in ('PORT_20','HEADER_2x4') else ''})
      (in_bom yes) (on_board yes)
      {prop('Reference',reference)} {prop('Value',name)}
      {prop('Footprint','',hidden=True)} {prop('Datasheet','',hidden=True)}
      (symbol {Q(name+'_0_1')} {body})
      (symbol {Q(name+'_1_1')} {pintext}))'''


def rect(x,y):
    return f'(rectangle (start {-x} {y}) (end {x} {-y}) (stroke (width 0.254) (type default)) (fill (type background)))'


symbol('MLX90632','U',sensor,rect(10.16,7.62))
symbol('24LC256','U',memory,rect(10.16,10.16))
symbol('PORT_20','J',connector,rect(12.7,15.24))
symbol('R','R',passive,rect(1.016,1.27))
symbol('C','C',passive,''.join(f'(polyline (pts (xy -2.54 {y}) (xy 2.54 {y})) (stroke (width 0.254) (type default)) (fill (type none)))' for y in [-1.27,1.27]))
symbol('HEADER_2x4','J',header,rect(5.08,5.08))
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
    # Global labels keep net names unprefixed (GND, not /GND), matching the radio and PCB.
    items.append(f'(global_label {Q(net)} (shape bidirectional) (at {x} {y} {180 if leftward else 0}) (effects (font (size 1 1)) (justify {"right" if leftward else "left"})) (uuid {Q(UID("label"+str(counter)))}))')


def text(value,x,y,size=1.1):
    items.append(f'(text {Q(value)} (at {x} {y} 0) (effects (font (size {size} {size})) (justify left top)) (uuid {Q(UID("text"+str(x)+str(y)))}))')


def place(kind,ref,value,x,y,nets,dnp=False,footprint='',datasheet=''):
    instance=UID(ref)
    # Keep power names hidden; draw them with explicitly connected net labels.
    properties=prop('Reference',ref,x+4,y-1.5,ref.startswith('#'),True)+prop('Value',value,x+4,y+1.5,ref.startswith('#'),True)
    if kind in ('MLX90632','24LC256','PORT_20'):
        properties=prop('Reference',ref,x,y-26)+prop('Value',value,x,y-23)
    if kind == 'HEADER_2x4':
        properties=prop('Reference',ref,x,y-6.5)+prop('Value',value,x,y+6.5)
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


MLX='https://www.melexis.com/-/media/files/documents/datasheets/mlx90632-datasheet-melexis.pdf'
EEP='https://ww1.microchip.com/downloads/aemDocuments/documents/MPD/ProductDocuments/DataSheets/24AA256-24LC256-24FC256-256K-I2C-Serial-EEPROM-DS20001203.pdf'
V='VDD_DAUGHTER'
G='GND'
text('BABEL / IR DAUGHTER / REV B - ADAFRUIT MLX90632 ADAPTATION',12,14,1.8)
text('3.3 V from protected host port. No local MCU. Portable Wasm stored in separate EEPROM.',12,19)
text('01 / HOST PORT',15,26,1.3)
text('02 / IR SENSOR',115,26,1.3)
text('03 / DRIVER MEMORY',210,26,1.3)
place('PORT_20','J1','MEC1 NP / 20 GOLD FINGERS',50.8,62.23,
      {1:G,2:G,3:V,5:'NVM_SCL',6:'NVM_SDA',7:'NVM_WP',8:G,9:'SENSOR_SCL',10:'SENSOR_SDA',18:V,19:G,20:G},
      footprint='Babel:MEC1_110_02_NP_Card')
place('MLX90632','U1','MLX90632SLD-DCB-000-RE',139.7,60.96,
      {1:'SENSOR_SDA',2:V,3:G,4:'SENSOR_SCL',5:'SENSOR_ADDR',6:G},
      footprint='Babel_IR:MLX90632_Adafruit',datasheet=MLX)
place('R','R6','10k / ADDR',182.88,63.5,{1:'SENSOR_ADDR',2:G},
      footprint='Resistor_SMD:R_0603_1608Metric')
place('24LC256','U2','24LC256-I/SN / 32 KiB',228.6,60.96,
      {1:G,2:G,3:G,4:G,5:'NVM_SDA',6:'NVM_SCL',7:'NVM_WP',8:V},
      footprint='Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',datasheet=EEP)
text('Pin 8 = PRESENT_N, strapped to GND. VDD on 3 and 18.\nHost mirrors n/21-n: works either way round.\nPin 4 (host SENSOR_IO2) and 11-17 unused here.\nMEC1 NP: odd front / even back; 1.57mm PCB.\nPower OFF to swap. See radio/MECHANICAL.md.',15,86)
text('I2C address 0x3A; ADDR pulled low by R6.\n50 deg FOV; preserve optical clearance.\nPlace C1 close to U1 pins 2/3. EP to GND.\nTemperature calculations run in host Wasm driver.',115,86)
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
text('06 / BENCH HEADER',15,160,1.3)
place('HEADER_2x4','J2','2x4 2.54mm / bench',40.64,167.64,
      {1:G,2:V,3:'SENSOR_SCL',4:'SENSOR_SDA',5:'NVM_SCL',6:'NVM_SDA',7:'NVM_WP',8:G},
      footprint='Connector_PinHeader_2.54mm:PinHeader_2x04_P2.54mm_Vertical')
text('J2: 0.1 in header for wiring an external I2C host (bench bring-up).\nPin 2 takes 3.3 V only. Fit R2-R5 or host-side pull-ups.\nBench boards only: leave J2 unfitted when mated to the radio.',75,162)
place('PWR_FLAG','#FLG01','PWR_FLAG',243.84,158.75,{1:V})
place('PWR_FLAG','#FLG02','PWR_FLAG',269.24,158.75,{1:G})
text('Host owns current limiting, signal isolation and safe hot-swap sequencing.\nPower flags document external supply; they are not protection devices.',15,190,1)
text('Sensor circuit adapted from Adafruit / Limor Fried (CC BY-SA 3.0).\nBabel modifications: 3.3 V only, card edge, separate driver EEPROM.\nDRAFT: NOT FOR FABRICATION; see ADAPTATION.md.',15,181,1)

lib='(kicad_symbol_lib (version 20241209) (generator "babel")\n'+ '\n'.join(definitions.values())+'\n)\n'
(ROOT/'Babel_IR.kicad_sym').write_text(lib)
cached='\n'.join(s.replace('(symbol '+Q(n), '(symbol '+Q('Babel_IR:'+n),1) for n,s in definitions.items())
sheet=f'''(kicad_sch (version 20250114) (generator "eeschema") (uuid {Q(UID('sheet'))})
 (paper "A4") (title_block (title "Babel IR daughter - Adafruit adaptation") (date "2026-10-17") (rev "B-draft"))
 (lib_symbols {cached})
 {''.join(items)})\n'''
(ROOT/(NAME+'.kicad_sch')).write_text(sheet)
(ROOT/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "Babel_IR") (type "KiCad") (uri "${KIPRJMOD}/Babel_IR.kicad_sym") (options "") (descr "Babel IR project symbols")))\n')
with (ROOT/'bom.csv').open('w') as f:
    writer=csv.writer(f)
    writer.writerow(['Reference','Value','Assembly','Footprint','Datasheet'])
    writer.writerows(components)
(ROOT/'expected-nets.json').write_text(json.dumps(expected,indent=2)+'\n')

# Translate only the upstream sensor footprint. Eagle Y is up, KiCad Y is down.
# Preserve copper dimensions, mask, and the three explicit EP paste apertures.
upstream=ROOT.parent/'reference'/'adafruit-mlx90632'
eagle=ET.parse(upstream/'Adafruit MLX90632 FIR Remote Temperature Sensor.sch')
package=eagle.find('.//library[@name="adafruit_sensor"]/packages/package[@name="MLX90632"]')
assert package is not None
fp=['(footprint "MLX90632_Adafruit" (version 20241229) (generator "pcbnew") (layer "F.Cu") (attr smd)',
    '(descr "Adapted from Adafruit MLX90632, CC BY-SA 3.0; see ADAPTATION.md")',
    '(fp_text reference "REF**" (at 0 -3) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))',
    '(fp_text value "MLX90632" (at 0 3) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))']
layers={'21':'F.SilkS','51':'F.Fab','39':'F.CrtYd'}
for pad in package.findall('smd'):
    a=pad.attrib
    paste=' "F.Paste"' if a.get('cream') != 'no' else ''
    shape='roundrect' if a.get('roundness') else 'rect'
    ratio=f'(roundrect_rratio {float(a["roundness"])/200})' if shape=='roundrect' else ''
    fp.append(f'(pad {Q(a["name"])} smd {shape} (at {a["x"]} {-float(a["y"])}) (size {a["dx"]} {a["dy"]}) (layers "F.Cu" "F.Mask"{paste}) {ratio})')
for w in package.findall('wire'):
    a=w.attrib
    if a['layer'] not in layers or max(float(a['x1']),float(a['x2']))>3:
        continue  # Omit upstream's separate explanatory drawing to the right.
    fp.append(f'(fp_line (start {a["x1"]} {-float(a["y1"])}) (end {a["x2"]} {-float(a["y2"])}) (stroke (width {a["width"]}) (type default)) (layer {Q(layers[a["layer"]])}))')
for c in package.findall('circle'):
    a=c.attrib
    if a['layer'] in layers:
        fp.append(f'(fp_circle (center {a["x"]} {-float(a["y"])}) (end {float(a["x"])+float(a["radius"])} {-float(a["y"])}) (stroke (width {a["width"]}) (type default)) (fill none) (layer {Q(layers[a["layer"]])}))')
for r in package.findall('rectangle'):
    a=r.attrib
    if a['layer']=='31':
        fp.append(f'(fp_rect (start {a["x1"]} {-float(a["y1"])}) (end {a["x2"]} {-float(a["y2"])}) (stroke (width 0) (type default)) (fill solid) (layer "F.Paste"))')
fp.append(')')
(ROOT/'Babel_IR.pretty').mkdir(exist_ok=True)
(ROOT/'Babel_IR.pretty'/'MLX90632_Adafruit.kicad_mod').write_text('\n'.join(fp)+'\n')
(ROOT/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "Babel_IR") (type "KiCad") (uri "${KIPRJMOD}/Babel_IR.pretty") (options "") (descr "Adafruit-derived sensor footprint")) (lib (name "Babel") (type "KiCad") (uri "${KIPRJMOD}/../Babel.pretty") (options "") (descr "Shared card edge")))\n')
print('Generated schematic, local symbols/footprint, BOM, and expected connectivity.')
