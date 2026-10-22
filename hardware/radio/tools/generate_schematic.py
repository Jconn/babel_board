"""Generate Babel radio rev D, onboard charging restored. Reconcile hand edits first."""
from pathlib import Path
import csv
import json
import uuid

ROOT = Path(__file__).resolve().parents[1]
NAME = 'babel-radio'
LIB = 'Babel_Radio'
Q = lambda x: json.dumps(str(x))
UID = lambda x: str(uuid.uuid5(uuid.NAMESPACE_URL, 'babel/radio/' + x))
definitions, pinsets, components, expected, nc = {}, {}, [], {}, []
pages = {}
G, V, D = 'GND', 'V3V3', 'VDD_DAUGHTER'
TI = 'https://www.ti.com/lit/ds/symlink/'
ESP = 'https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf'

def effects(size=1, hide=False):
    return f'(effects (font (size {size} {size})) {"(hide yes)" if hide else ""})'

def prop(k, v, x=0, y=0, hide=False):
    return f'(property {Q(k)} {Q(v)} (at {x} {y} 0) {effects(1, hide)})'

def define(name, entries, ref='U'):
    """Entries are physical pad number, pin name, electrical type. Never omit pads."""
    half = (len(entries)+1)//2
    h = max(5.08, (half-1)*2.54/2+2.54)
    pins=[]
    for i,(n,label,typ) in enumerate(entries):
        side = i//half
        pins.append((str(n),label,typ, -22.86 if side==0 else 22.86,
                     round((half-1)*1.27-(i%half)*2.54,4), 0 if side==0 else 180))
    if name in ('R','C','L','SW'):
        pins=[('1','~','passive',-7.62,0,0),('2','~','passive',7.62,0,180)]
        h=2.54
    pinsets[name]=(pins,h)
    w=3.81 if name in ('R','C','L','SW') else 20.32
    body=f'(rectangle (start {-w} {h}) (end {w} {-h}) (stroke (width 0.254) (type default)) (fill (type background)))'
    if name=='C':
        body=''.join(f'(polyline (pts (xy {x} -2.54) (xy {x} 2.54)) (stroke (width 0.254) (type default)) (fill (type none)))' for x in [-1.27,1.27])
        # Lines between pin ends and plates.
        body+=''.join(f'(polyline (pts (xy {a} 0) (xy {b} 0)) (stroke (width 0.254) (type default)) (fill (type none)))' for a,b in [(-5.08,-1.27),(1.27,5.08)])
    if name=='SW':
        body='(polyline (pts (xy -5.08 0) (xy -2.54 0) (xy 2.54 2.54)) (stroke (width 0.254) (type default)) (fill (type none))) (polyline (pts (xy 2.54 0) (xy 5.08 0)) (stroke (width 0.254) (type default)) (fill (type none)))'
    if name=='FLAG':
        body='(polyline (pts (xy -20.32 0) (xy -17.78 2.54) (xy -15.24 0) (xy -20.32 0)) (stroke (width 0.254) (type default)) (fill (type none)))'
    ptext=''.join(f'(pin {t} line (at {x} {y} {a}) (length 2.54) (name {Q(l)} {effects(.85)}) (number {Q(n)} {effects(.85)}))' for n,l,t,x,y,a in pins)
    definitions[name]=f'(symbol {Q(name)} (pin_names (offset 0.508)) (in_bom yes) (on_board yes) {prop("Reference",ref)} {prop("Value",name)} (symbol {Q(name+"_0_1")} {body}) (symbol {Q(name+"_1_1")} {ptext}))'

def block(name, labels, types=None):
    types=types or {}
    define(name,[(n,l,types.get(n,'passive')) for n,l in labels.items()])

for kind,ref in [('R','R'),('C','C'),('L','L'),('SW','SW')]:
    define(kind,[(1,'~','passive'),(2,'~','passive')],ref)
gpio_by_pin={4:4,5:5,6:6,7:7,8:15,9:16,10:17,11:18,12:8,13:19,14:20,15:3,16:46,17:9,18:10,19:11,20:12,21:13,22:14,23:21,24:47,25:48,26:45,27:0,28:35,29:36,30:37,31:38,32:39,33:40,34:41,35:42,36:44,37:43,38:2,39:1}
block('WROOM',{i:('GND' if i in (1,40,41) else '3V3' if i==2 else 'EN' if i==3 else f'GPIO{gpio_by_pin[i]}') for i in range(1,42)},
      {i:('power_in' if i in (1,2,40,41) else 'input' if i==3 else 'bidirectional') for i in range(1,42)})
block('BQ24079',{1:'TS',2:'BAT',3:'BAT',4:'CE_N',5:'EN2',6:'EN1',7:'PGOOD_N',8:'VSS',9:'CHG_N',10:'OUT',11:'OUT',12:'ILIM',13:'IN',14:'TMR',15:'SYSOFF',16:'ISET',17:'EP'},
      {1:'input',4:'input',5:'input',6:'input',7:'open_collector',8:'power_in',9:'open_collector',10:'power_out',13:'power_in',15:'input',17:'power_in'})
block('TPS63070',{1:'PS_SYNC',2:'PG',3:'VAUX',4:'GND',5:'FB',6:'FB2',7:'VOUT',8:'VOUT',9:'L2',10:'PGND',11:'L1',12:'VIN',13:'VIN',14:'EN',15:'VSEL'},
      {1:'input',2:'open_collector',4:'power_in',5:'input',7:'power_out',10:'power_in',12:'power_in',13:'power_in',14:'input',15:'input'})
block('TPS2553',{1:'IN',2:'GND',3:'EN',4:'FAULT_N',5:'ILIM',6:'OUT'},
      {1:'power_in',2:'power_in',3:'input',4:'open_collector',6:'power_out'})
block('BUS8',{1:'NC',**{i+2:f'A{i+1}' for i in range(8)},10:'GND',**{18-i:f'B{i+1}' for i in range(8)},19:'OE_N',20:'VCC'},
      {**{i:'bidirectional' for i in list(range(2,10))+list(range(11,19))},10:'power_in',19:'input',20:'power_in'})
block('AND',{1:'A',2:'B',3:'GND',4:'Y',5:'VCC'},{1:'input',2:'input',3:'power_in',4:'output',5:'power_in'})
block('NOT',{1:'NC',2:'A',3:'GND',4:'Y',5:'VCC'},{2:'input',3:'power_in',4:'output',5:'power_in'})
block('ODNOT',{1:'NC',2:'A',3:'GND',4:'Y_OD',5:'VCC'},{2:'input',3:'power_in',4:'open_collector',5:'power_in'})
block('USB_ESD',{1:'IO1',2:'GND',3:'IO2',4:'IO2',5:'VBUS',6:'IO1'})
block('CC',{1:'CC1',2:'CC2',3:'PORT',4:'VBUS_DET',5:'ADDR',6:'OUT3',7:'OUT1',8:'OUT2',9:'ID',10:'GND',11:'EN_N',12:'VDD'},
      {3:'input',4:'input',5:'input',6:'open_collector',7:'open_collector',8:'open_collector',9:'open_collector',10:'power_in',11:'input',12:'power_in'})
block('LDO',{1:'IN',2:'GND',3:'EN',4:'NC',5:'OUT'},{1:'power_in',2:'power_in',3:'input',5:'power_out'})
block('WINDOW',{1:'OUTA',2:'GND',3:'INA_PLUS',4:'INB_MINUS',5:'VDD',6:'OUTB'},
      {1:'open_collector',2:'power_in',3:'input',4:'input',5:'power_in',6:'open_collector'})
block('USB_SWITCH',{1:'1D_PLUS',2:'1D_MINUS',3:'2D_PLUS',4:'2D_MINUS',5:'GND',6:'OE_N',7:'D_MINUS',8:'D_PLUS',9:'S',10:'VCC'},
      {5:'power_in',6:'input',9:'input',10:'power_in'})
block('LOAD_SWITCH',{1:'IN',2:'GND',3:'ON',4:'CT',5:'QOD',6:'OUT'},
      {1:'power_in',2:'power_in',3:'input',6:'power_out'})
block('DIODE',{1:'K',2:'A'})
block('SLIDE',{1:'ON',2:'COMMON',3:'OFF'})
block('ESD2',{1:'IO1',2:'IO2',3:'GND'},{3:'power_in'})
usb={p:p for p in ['A1','A4','A5','A6','A7','A8','A9','A12','B1','B4','B5','B6','B7','B8','B9','B12','SH']}
block('USB_C',usb)
for count in [3,6,8,20]:
    block(f'CONN{count}',{i:str(i) for i in range(1,count+1)})
block('FLAG',{1:'SUPPLY'},{1:'power_out'})
block('TP',{1:'PROBE'})

def page(name,title,notes):
    pages[name]={'title':title,'notes':notes,'parts':[]}
    return name

def add(pg,kind,ref,value,nets,fp='',ds='',dnp=False):
    assert not any(c['ref']==ref for c in components), ref
    c=dict(page=pg,kind=kind,ref=ref,value=value,nets={str(k):v for k,v in nets.items()},fp=fp,ds=ds,dnp=dnp)
    components.append(c)
    pages[pg]['parts'].append(c)
    for pin,*_ in pinsets[kind][0]:
        if c['nets'].get(pin) is None: nc.append(f'{ref}.{pin}')
        else: expected[f'{ref}.{pin}']=c['nets'][pin]

counts={'R':0,'C':0,'SW':0}
def passive(pg,kind,value,a,b,dnp=False):
    counts[kind]+=1
    ref=kind+str(counts[kind])
    fp={'R':'Resistor_SMD:R_0603_1608Metric','C':'Capacitor_SMD:C_0805_2012Metric','SW':'Button_Switch_SMD:SW_SPST_B3U-1000P'}[kind]
    add(pg,kind,ref,value,{1:a,2:b},fp,dnp=dnp)
    return ref
def r(pg,value,a,b,dnp=False): return passive(pg,'R',value,a,b,dnp)
def c(pg,value,a,b=G): return passive(pg,'C',value,a,b)
def sw(pg,value,a,b): return passive(pg,'SW','B3U-1000P / '+value,a,b)

p=page('host','PROCESSOR / DISPLAY / RECOVERY',[
    'U1 selected: ESP32-S3-WROOM-1-N8R8. GPIO35/36/37 reserved for octal PSRAM; do not route.',
    'GPIO0 boot; GPIO3/45 strap LOW, reserved. USB current permission is now autonomous hardware, not firmware.',
    'Display: Adafruit 4741 SSD1327 OLED module, 128x128 grayscale. Cut module J1/J2 jumpers for SPI.',
    'J3 is 3.3 V UART recovery; VTREF is sense only. Native USB is on GPIO19/20. Antenna keepout required.'
])
signals={0:'BOOT_N',1:'BUTTON_N',2:'PRESENT_N',3:'STRAP3_LOW',4:'H_NVM_SCL',5:'H_NVM_SDA',6:'H_NVM_WP',7:'H_SENSOR_SCL',8:'H_SENSOR_SDA',9:'H_SENSOR_SCK',10:'H_SENSOR_MOSI',11:'H_SENSOR_MISO',12:'H_SENSOR_CS_N',13:'H_SENSOR_TX',14:'H_SENSOR_RX',15:'H_SENSOR_IRQ_N',16:'H_SENSOR_RESET_N',17:'PWR_REQ',18:'NVM_REQ',19:'USB_DM_MCU',20:'USB_DP_MCU',21:'SENSOR_REQ',38:'PORT_FAULT_N',39:'LCD_SCK',40:'LCD_MOSI',41:'LCD_CS_N',42:'LCD_DC',43:'DEBUG_TX',44:'DEBUG_RX',45:'STRAP45_LOW',47:'LCD_RESET_N',48:'USB_PGOOD_N'}
for gpio in (9,10,12,13): signals[gpio]=signals[gpio].replace('H_','MCU_')
add(p,'WROOM','U1','ESP32-S3-WROOM-1-N8R8',
    {1:G,2:V,3:'CHIP_EN',40:G,41:G,**{pin:signals.get(gpio) for pin,gpio in gpio_by_pin.items()}},
    'RF_Module:ESP32-S3-WROOM-1',ESP)
r(p,'10k',V,'CHIP_EN'); c(p,'1uF / EN delay','CHIP_EN'); sw(p,'RESET','CHIP_EN',G)
r(p,'10k',V,'BOOT_N'); sw(p,'BOOT','BOOT_N',G)
r(p,'10k',V,'BUTTON_N'); sw(p,'USER / HOLD','BUTTON_N',G)
c(p,'22uF / 10V / U1',V); c(p,'100nF / U1',V)
add(p,'CONN8','J2','B8B-PH-K-S / OLED cable',{1:V,2:G,3:'LCD_SCK',4:'LCD_MOSI',5:'LCD_CS_N',6:'LCD_DC',7:'LCD_RESET_N',8:None},'Connector_JST:JST_PH_B8B-PH-K_1x08_P2.00mm_Vertical',ds='https://learn.adafruit.com/adafruit-grayscale-1-5-128x128-oled-display/pinouts')
add(p,'CONN6','J3','UART RECOVERY / 3.3V ONLY',{1:G,2:V,3:'DEBUG_TX',4:'DEBUG_RX',5:'CHIP_EN',6:'BOOT_N'},'Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical')
r(p,'10k',V,'LCD_CS_N'); r(p,'10k',V,'LCD_RESET_N'); c(p,'10uF / display',V)

p=page('usb_charge','USB-C / BATTERY POWER PATH',[
    'USB-C sink only: require 1.5A or 3A advertisement; CC logic and input gate on USB_POLICY sheet. No PD.',
    'EN1 grounded; EN2 = USB_ALLOW. Gated input prevents default-current / legacy sources powering the charger.',
    'USB-only boot is hardware-enabled after valid CC advertisement; ROM programming uses the same data path.',
    'Charge disabled by default: R90 is DNP. Fit only after battery/NTC/thermal bench qualification.',
    'Battery: Jauch 251555, 1000mAh. J5: 1=positive, 2=10k B3435 NTC, 3=negative. Verify mating footprint.',
    '166mA nominal, 4.1V target. Independent hardware NTC guard controls CE; enabled safety timers.'
])
add(p,'USB_C','J4','USB4105-GF-A',
    {**{x:G for x in ['A1','A12','B1','B12','SH']},**{x:'USB_VBUS_RAW' for x in ['A4','A9','B4','B9']},'A5':'CC1','B5':'CC2','A6':'USB_DP','B6':'USB_DP','A7':'USB_DM','B7':'USB_DM'},
    'Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal','https://gct.co/files/drawings/usb4105.pdf')
# R6/R7 retired: CC controller provides dead-battery Rd. Preserve other references.
counts['R']+=2
add(p,'ESD2','U2','TPD2E2U06DCKR',{1:'USB_DP',2:'USB_DM',3:G},'Package_TO_SOT_SMD:SOT-323_SC-70',TI+'tpd2e2u06.pdf')
add(p,'R','F1','046701.5NR / 1.5A fast fuse',{1:'USB_VBUS_RAW',2:'USB_5V'},'Fuse:Fuse_0603_1608Metric')
add(p,'DIODE','D3','SMBJ6.0A / VBUS TVS',{1:'USB_5V',2:G},'Diode_SMD:D_SMB')
r(p,'22R / near U1','USB_DP_LINK','USB_DP_MCU');r(p,'22R / near U1','USB_DM_LINK','USB_DM_MCU')
add(p,'BQ24079','U3','BQ24079RGTR / 4.1V',{1:'CHG_TS_FIXED',2:'VBAT',3:'VBAT',4:'CHARGE_DISABLE',5:'USB_ALLOW',6:G,7:'USB_PGOOD_N',8:G,9:'CHG_N',10:'SYS_RAW',11:'SYS_RAW',12:'CHG_ILIM',13:'USB_CHG_IN',14:'CHG_TMR',15:G,16:'CHG_ISET',17:G},'Babel:BQ24079_RGT0016B',ds=TI+'bq24074.pdf')
add(p,'CONN3','J5','B3B-PH-K-S / Jauch 251555',{1:'VBAT',2:'PACK_NTC',3:G},'Connector_JST:JST_PH_B3B-PH-K_1x03_P2.00mm_Vertical',ds='https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/5702/LP523450JU%20251555.pdf')
r(p,'100k','STRAP3_LOW',G);r(p,'100k','STRAP45_LOW',G)
r(p,'5.36k 1% / 166mA','CHG_ISET',G);r(p,'1.78k 1% / 904mA','CHG_ILIM',G)
r(p,'10k / disable default','SYS_RAW','CHARGE_DISABLE')
add(p,'R','R90','0R / enable guard AFTER bench test',{1:'CHARGE_DISABLE',2:'GUARD_DISABLE'},'Resistor_SMD:R_0603_1608Metric',dnp=True)
r(p,'100k',V,'CHG_N'); r(p,'100k',V,'USB_PGOOD_N')
c(p,'1uF / 16V / input','USB_CHG_IN');c(p,'4.7uF / 10V / BAT','VBAT');c(p,'4.7uF / 10V / OUT','SYS_RAW')
add(p,'FLAG','#FLG01','USB source',{1:'USB_5V'});add(p,'FLAG','#FLG02','Protected pack',{1:'VBAT'});add(p,'FLAG','#FLG03','Ground',{1:G})

p=page('regulator','3.3 V BUCK-BOOST / SYSTEM POWER',[
    'TPS63070 reference topology: 1.5uH; 470k/150k feedback gives nominal 3.307V.',
    'Inductor: Coilcraft XFL4020-152MEC, 1.5uH, exact XxL4020 land pattern selected.',
    'Input: 2x10uF plus 10uF close. Output: 3x22uF plus 10uF close. Check actual DC-bias derating.',
    'SW4 turns system rail off, NOT charging. Protected pack must prevent deep discharge.',
    'Power-save mode selected. Validate load transients, RF peaks, thermals and battery runtime on hardware.',
    'RNM 15-pad package requires its exact land pattern; do not substitute a generic QFN with extra EP.'
])
add(p,'TPS63070','U4','TPS63070RNMR',{1:'REG_PS',2:'REG_PG',3:'REG_AUX',4:G,5:'REG_FB',6:None,7:V,8:V,9:'REG_L2',10:G,11:'REG_L1',12:'SYS_RAW',13:'SYS_RAW',14:'REG_EN',15:G},'Babel:TPS63070_RNM0015A',ds=TI+'tps63070.pdf')
add(p,'R','R124','10k / PS input protection',{1:'SYS_RAW',2:'REG_PS'},'Resistor_SMD:R_0603_1608Metric')
add(p,'L','L1','1.5uH / XFL4020-152MEC',{1:'REG_L1',2:'REG_L2'},'Inductor_SMD:L_Coilcraft_XxL4020',ds='https://www.coilcraft.com/pdfs/xfl4020.pdf')
r(p,'470k 1%',V,'REG_FB');r(p,'150k 1%','REG_FB',G)
c(p,'100nF / VAUX','REG_AUX')
for value in ['10uF / 25V X7S','10uF / 25V X7S','10uF / 25V close']: c(p,value,'SYS_RAW')
for value in ['22uF / 16V X6S','22uF / 16V X6S','22uF / 16V X6S','10uF / 25V close']: c(p,value,V)
add(p,'SLIDE','SW4','JS102011SAQN / SYSTEM',{1:'POWER_AVAILABLE',2:'REG_EN',3:G},'Button_Switch_SMD:SW_SPDT_CK_JS102011SAQN')
r(p,'100k','REG_EN',G);r(p,'100k',V,'REG_PG')

p=page('port_power','DAUGHTER POWER / HARDWARE ENABLE GATING',[
    'PRESENT_N is pulled up on host and grounded on daughter. No long RC: hardware removal path stays fast.',
    'PORT_EN = PRESENT AND PWR_REQ. NVM and sensor enables additionally require their own MCU request.',
    'Loss of PRESENT forces power and all bus switches off without guest cooperation. Contact order remains TBD.',
    'TPS2553 226k 1%: nominal 120mA; TI limits 101.3..142.1mA. Daughter continuous budget stays 100mA.',
    'Bleeder discharges daughter rail; this is NOT an active discharge or a power-good detector.',
    'Firmware must verify settling and handle faults. Arbitrary partial insertion, ESD and brownouts NOT qualified.'
])
def logic(kind,ref,nets):
    part='sn74lvc1g08' if kind=='AND' else 'sn74lvc1g04'
    add(p,kind,ref,part.upper()+'DBVR',{**nets,3:G,5:V},'Package_TO_SOT_SMD:SOT-23-5',TI+part+'.pdf')
    c(p,'100nF / '+ref,V)
logic('NOT','U5',{2:'PRESENT_N',4:'PRESENT'})
logic('AND','U6',{1:'PRESENT',2:'PWR_REQ',4:'PORT_EN'})
logic('AND','U7',{1:'PORT_EN',2:'NVM_REQ',4:'NVM_ENABLE'})
logic('NOT','U8',{2:'NVM_ENABLE',4:'NVM_OE_N'})
logic('AND','U9',{1:'PORT_EN',2:'SENSOR_REQ',4:'SENSOR_ENABLE'})
logic('NOT','U10',{2:'SENSOR_ENABLE',4:'SENSOR_OE_N'})
r(p,'10k',V,'PRESENT_N')
for net in ['PWR_REQ','NVM_REQ','SENSOR_REQ','PORT_EN']: r(p,'100k',net,G)
for net in ['NVM_OE_N','SENSOR_OE_N','PORT_FAULT_N']: r(p,'10k',V,net)
add(p,'TPS2553','U11','TPS2553DBVR',{1:V,2:G,3:'PORT_EN',4:'PORT_FAULT_N',5:'PORT_ILIM',6:D},'Package_TO_SOT_SMD:SOT-23-6',TI+'tps2553.pdf')
r(p,'226k 1%','PORT_ILIM',G);c(p,'1uF / input',V);c(p,'1uF / output',D);r(p,'10k / discharge',D,G)

p=page('port_bus','CARD EDGE / SEPARATE NVM AND SENSOR BUSES',[
    'J1: MEC1-110-02-L-D-NP-A, all 20 contacts populated. NP version requires external orientation key and retention.',
    'U12 isolates NVM. U13/U14 isolate all sensor signals as one group. Unused sensor interfaces must stay high-Z.',
    'All daughter-facing pull-ups reference VDD_DAUGHTER; MCU internal pull-ups must be off before isolation.',
    'NVM_WP and SENSOR_RESET_N are open-drain host controls. IRQ_N is open-drain from daughter.',
    'Host I2C pull-ups are 4.7k. IR daughter optional pull-ups remain DNP. Qualify capacitance and rise time.',
    'TPD2E2U06 arrays protect connector signals. Stuck-bus recovery is firmware; system ESD still needs testing.'
])
port={1:G,2:G,3:D,4:D,5:'NVM_SCL',6:'NVM_SDA',7:'NVM_WP',8:'PRESENT_N',9:'SENSOR_SCL',10:'SENSOR_SDA',11:'SENSOR_SCK',12:'SENSOR_MOSI',13:'SENSOR_MISO',14:'SENSOR_CS_N',15:'SENSOR_TX',16:'SENSOR_RX',17:'SENSOR_IRQ_N',18:'SENSOR_RESET_N',19:G,20:G}
add(p,'CONN20','J1','MEC1-110-02-L-D-NP-A',port,'Babel:MEC1_110_02_NP_A_Socket',ds='https://suddendocs.samtec.com/prints/mec1-1xx-xx-xx-d-xx-xx-footprint.pdf')
groups=[('U12','NVM_OE_N',['NVM_SCL','NVM_SDA','NVM_WP']),('U13','SENSOR_OE_N',['SENSOR_SCL','SENSOR_SDA','SENSOR_SCK','SENSOR_MOSI','SENSOR_MISO','SENSOR_CS_N','SENSOR_TX','SENSOR_RX']),('U14','SENSOR_OE_N',['SENSOR_IRQ_N','SENSOR_RESET_N'])]
for ref,oe,names in groups:
    nets={10:G,19:oe,20:V}
    for i,name in enumerate(names): nets[i+2]='H_'+name; nets[18-i]=name
    add(p,'BUS8',ref,'SN74CB3Q3245PWR',nets,'Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm',TI+'sn74cb3q3245.pdf')
    c(p,'100nF / '+ref,V)
for net in ['NVM_SCL','NVM_SDA','SENSOR_SCL','SENSOR_SDA']: r(p,'4.7k',D,net)
for net in ['NVM_WP','SENSOR_CS_N','SENSOR_IRQ_N','SENSOR_RESET_N']: r(p,'10k',D,net)

# Explicit reference block for the revision B power-policy additions.
def rr(pg,ref,value,a,b):
    add(pg,'R',ref,value,{1:a,2:b},'Resistor_SMD:R_0603_1608Metric')
def cc(pg,ref,value,a,b=G):
    add(pg,'C',ref,value,{1:a,2:b},'Capacitor_SMD:C_0805_2012Metric')
def gate(pg,kind,ref,nets,rail):
    part={'AND':'sn74lvc1g08','NOT':'sn74lvc1g04','ODNOT':'sn74lvc1g06'}[kind]
    add(pg,kind,ref,part.upper()+'DBVR',{**nets,3:G,5:rail},'Package_TO_SOT_SMD:SOT-23-5',TI+part+'.pdf')

p=page('usb_policy','USB-C PERMISSION / INPUT AND DATA GATING',[
    'Supported: 5V USB-C source advertising >=1.5A; no PD, legacy USB-A or default-current operation.',
    'U15 runs from VBUS-derived V3V3_CC, independent of the battery and main regulator. Its internal Rd replaces R6/R7.',
    'OUT1 low means attached medium/high current. U17 inverts to USB_ALLOW; U18 admits power only then.',
    'U19 disconnects D+/D- when permission is absent, including battery-only operation and ROM USB pull-ups.',
    'R_ILIM limits charger input to 976mA worst case; CC/control loads are additional but remain below 1.5A.',
    'Validate attach/detach/inrush and source-advertisement changes on hardware. Input gate is not PD overvoltage protection.'
])
add(p,'LDO','U16','TPS70933DBVR',{1:'USB_5V',2:G,3:None,4:None,5:'V3V3_CC'},'Package_TO_SOT_SMD:SOT-23-5',TI+'tps709.pdf')
cc(p,'C100','2.2uF / 16V / LDO IN','USB_5V');cc(p,'C101','2.2uF / 10V / LDO OUT','V3V3_CC')
add(p,'CC','U15','TUSB320LAIRWBR',{1:'CC1',2:'CC2',3:G,4:'CC_VBUS_DET',5:None,6:None,7:'CC_HIGH_N',8:None,9:None,10:G,11:G,12:'V3V3_CC'},
    'Package_DFN_QFN:Texas_X2QFN-12_1.6x1.6mm_P0.4mm',TI+'tusb320lai.pdf')
rr(p,'R100','887k 1%','USB_5V','CC_VBUS_DET');rr(p,'R101','10k','V3V3_CC','CC_HIGH_N')
cc(p,'C102','100nF / U15','V3V3_CC')
gate(p,'NOT','U17',{2:'CC_HIGH_N',4:'USB_ALLOW'},'V3V3_CC');cc(p,'C103','100nF / U17','V3V3_CC')
rr(p,'R102','100k','USB_ALLOW',G)
add(p,'LOAD_SWITCH','U18','TPS22810DBVR',{1:'USB_5V',2:G,3:'USB_ALLOW',4:'USB_SLEW',5:'USB_CHG_IN',6:'USB_CHG_IN'},'Package_TO_SOT_SMD:SOT-23-6',TI+'tps22810.pdf')
cc(p,'C109','27nF / slew ~2.2ms at 5V','USB_SLEW')
add(p,'USB_SWITCH','U19','TS3USB221ARSER',{1:'USB_DP_LINK',2:'USB_DM_LINK',3:None,4:None,5:G,6:'CC_HIGH_N',7:'USB_DM',8:'USB_DP',9:G,10:'V3V3_CC'},
    'Package_DFN_QFN:Texas_UQFN-10_1.5x2mm_P0.5mm',TI+'ts3usb221a.pdf')
cc(p,'C104','100nF / U19','V3V3_CC')

p=page('charge_guard','HARDWARE TEMPERATURE WINDOW / BATTERY STARTUP',[
    'J5 NTC is independently biased from V3V3_CC; U20 window outputs are wired together. Firmware cannot override.',
    'BQ24079 TS has 10k fixed bias because U20 performs pack temperature protection through CE.',
    '0.1% dividers; audit_charge_limits.py checks exported values before reference/bias/resistor corner analysis.',
    'U22/U23 require BOTH acceptable temperature and USB_ALLOW. R90 remains DNP pending qualification.',
    'R108: nominal 9.53h fast-charge / 57.2min precharge. CE thermal cycling resets timer; not a cumulative watchdog.',
    'U21 permits battery startup above about 3.33V; diode OR also permits battery-free USB startup.',
    'No latched low-battery cutoff. Qualify pack NTC curve, thermal lag, startup and fault behavior on hardware.'
])
add(p,'WINDOW','U20','TPS3700DDCR',{1:'TEMP_OK',2:G,3:'TEMP_HOT_SENSE',4:'TEMP_COLD_SENSE',5:'V3V3_CC',6:'TEMP_OK'},'Package_TO_SOT_SMD:SOT-23-6',TI+'tps3700.pdf')
rr(p,'R103','10k 0.1%','V3V3_CC','PACK_NTC')
rr(p,'R104','200k 0.1%','PACK_NTC','TEMP_HOT_SENSE');rr(p,'R105','100k 0.1%','TEMP_HOT_SENSE',G)
rr(p,'R106','412k 0.1%','PACK_NTC','TEMP_COLD_SENSE');rr(p,'R107','100k 0.1%','TEMP_COLD_SENSE',G)
rr(p,'R108','71.5k 0.1%','CHG_TMR',G);rr(p,'R109','10k / external NTC guard used','CHG_TS_FIXED',G)
rr(p,'R110','10k','V3V3_CC','TEMP_OK');cc(p,'C105','100nF / U20','V3V3_CC')
gate(p,'AND','U22',{1:'TEMP_OK',2:'USB_ALLOW',4:'CHARGE_ALLOWED'},'V3V3_CC')
gate(p,'ODNOT','U23',{2:'CHARGE_ALLOWED',4:'GUARD_DISABLE'},'V3V3_CC')
cc(p,'C106','100nF / U22','V3V3_CC');cc(p,'C107','100nF / U23','V3V3_CC')
add(p,'WINDOW','U21','TPS3700DDCR',{1:'BAT_OK',2:G,3:'BAT_SENSE',4:G,5:'SYS_RAW',6:None},'Package_TO_SOT_SMD:SOT-23-6',TI+'tps3700.pdf')
rr(p,'R111','732k 0.1%','VBAT','BAT_SENSE');rr(p,'R112','100k 0.1%','BAT_SENSE',G)
rr(p,'R113','10k','VBAT','BAT_OK');cc(p,'C108','100nF / U21','SYS_RAW')
add(p,'DIODE','D1','1N4148W',{1:'POWER_AVAILABLE',2:'BAT_OK'},'Diode_SMD:D_SOD-123')
add(p,'DIODE','D2','1N4148W',{1:'POWER_AVAILABLE',2:'USB_ALLOW'},'Diode_SMD:D_SOD-123')
rr(p,'R114','100k','POWER_AVAILABLE',G)

# Probe without attaching wires to fine-pitch packages. Do not expose SW nodes.
# Keep the converter feedback and output capacitors on the converter side of
# R125. Removing this link isolates the complete 3V3 load without opening FB.
def remap_supply(refs, old, new):
    for comp in components:
        if comp['ref'] in refs:
            for pin, net in comp['nets'].items():
                if net == old:
                    comp['nets'][pin] = new
                    expected[f"{comp['ref']}.{pin}"] = new

remap_supply({'U4', 'R17', 'C12', 'C13', 'C14', 'C15'}, V, 'V3V3_REG')
remap_supply({'J2', 'C4', 'R4', 'R5'}, V, 'V3V3_OLED')
remap_supply({'U11', 'C22'}, V, 'V3V3_PORT_IN')
for pg, ref, a, b, size in [
    ('regulator', 'R125', 'V3V3_REG', V, '0805_2012'),
    ('host', 'R126', V, 'V3V3_OLED', '0603_1608'),
    ('port_power', 'R127', V, 'V3V3_PORT_IN', '0603_1608'),
]:
    add(pg, 'R', ref, '0R / removable current link', {1:a, 2:b},
        'Resistor_SMD:R_' + size + 'Metric')
add('regulator', 'FLAG', '#FLG04', 'Power through R125', {1:V})
add('port_power', 'FLAG', '#FLG05', 'Power through R127', {1:'V3V3_PORT_IN'})
pages['regulator']['notes'].append('R125: remove unpowered for load isolation/current measurement; FB and output caps remain connected.')
pages['host']['notes'].append('R126 isolates OLED supply only: disconnect cable or hold interface low/high-Z to prevent signal back-power.')
pages['port_power']['notes'].append('R127 isolates switch input supply; disconnect daughter and keep requests low during isolation tests.')

page('test_points','BRING-UP TEST POINTS',[
    'Place supply probes with a nearby ground probe. Keep USB data and RF paths free of probe stubs.',
    'PACK_NTC probe: use high impedance only; loading can change temperature thresholds.',
    'Charging remains disabled until R90 qualification. No high-current injection through probe pads.'
])
for i,(pg,net) in enumerate([
    ('usb_charge','GND'),('usb_charge','USB_5V'),('usb_charge','USB_CHG_IN'),
    ('usb_charge','VBAT'),('usb_charge','SYS_RAW'),('usb_charge','CHG_N'),
    ('regulator','GND'),('regulator','V3V3'),('regulator','REG_EN'),('regulator','REG_PG'),
    ('charge_guard','PACK_NTC'),('charge_guard','TEMP_OK'),('charge_guard','CHARGE_DISABLE'),
    ('port_power','VDD_DAUGHTER'),('port_power','PORT_EN'),('usb_policy','USB_ALLOW')],1):
    add('test_points','TP',f'TP{i}',net,{1:net},'TestPoint:TestPoint_Pad_D1.0mm')

page('debug_points','BUS / POWER POLICY DEBUG ACCESS',[
    '1 mm exposed pads: solder fine wires for logic analysis; no permanent headers required.',
    'Host I2C is upstream of isolation; daughter test pads expose downstream I2C and WP.',
    'Observe control signals, do not force them against outputs. Ground pads support local probes.',
    'No added USB-data, CC-pin, switching-node or feedback stubs. J3 remains UART/BOOT/RESET recovery.'
])
debug_nets = ['H_NVM_SCL', 'H_NVM_SDA', 'H_NVM_WP', 'H_SENSOR_SCL',
              'H_SENSOR_SDA', 'NVM_OE_N', 'SENSOR_OE_N', 'PORT_FAULT_N',
              'PRESENT_N', G, 'V3V3_CC', 'CC_HIGH_N', 'USB_PGOOD_N',
              'BAT_OK', 'POWER_AVAILABLE', G, G, G, 'V3V3_REG', G, G, G]
for i, net in enumerate(debug_nets, 17):
    add('debug_points', 'TP', f'TP{i}', net, {1:net}, 'TestPoint:TestPoint_Pad_D1.0mm')

# Exact TI reference power capacitors: body sizes affect placement and effective C.
for comp in components:
    ref=comp['ref']
    if ref=='D3': comp['mpn']='SMBJ6.0A-13-F (Diodes Incorporated)'
    if ref in ('C9','C10'): comp['mpn']='GRM21BC71E106ME11L'
    if ref in ('C12','C13','C14'): comp['mpn']='GRM21BC81C226ME44L'
    if ref in ('C11','C15'):
        comp['mpn']='TMK107BBJ106MA-T'
        comp['fp']='Capacitor_SMD:C_0603_1608Metric'

# Source-series tuning sites, default shorts. Do not add these to I2C blindly.
for ref,name in zip(('R120','R121','R122','R123'),('SENSOR_SCK','SENSOR_MOSI','SENSOR_CS_N','SENSOR_TX')):
    rr('host',ref,'0R / source tuning near U1','MCU_'+name,'H_'+name)
# Ground-referenced, low-capacitance connector ESD. Layout/system testing required.
esd_pairs=[('U24','usb_policy','CC1','CC2')]
edge_signals=['NVM_SCL','NVM_SDA','NVM_WP','PRESENT_N','SENSOR_SCL','SENSOR_SDA',
              'SENSOR_SCK','SENSOR_MOSI','SENSOR_MISO','SENSOR_CS_N','SENSOR_TX',
              'SENSOR_RX','SENSOR_IRQ_N','SENSOR_RESET_N']
esd_pairs += [(f'U{30+i}','port_bus',*edge_signals[2*i:2*i+2]) for i in range(7)]
for ref,pg,a,b in esd_pairs:
    add(pg,'ESD2',ref,'TPD2E2U06DCKR',{1:a,2:b,3:G},'Package_TO_SOT_SMD:SOT-323_SC-70',TI+'tpd2e2u06.pdf')

def text(value,x,y,size=1):
    return f'(text {Q(value)} (at {x} {y} 0) (effects (font (size {size} {size})) (justify left top)) (uuid {Q(UID(str((value,x,y))))}))'

def render_component(comp,x,y,path):
    k,ref=comp['kind'],comp['ref']; pins,h=pinsets[k]; hidden=ref.startswith('#')
    props=prop('Reference',ref,x,y-h-7,hidden)+prop('Value',comp['value'],x,y-h-4,hidden)+prop('Footprint',comp['fp'],x,y,True)+prop('Datasheet',comp['ds'],x,y,True)
    if 'mpn' in comp: props+=prop('ManufacturerPartNumber',comp['mpn'],x,y,True)
    result=f'(symbol (lib_id {Q(LIB+":"+k)}) (at {x} {y} 0) (unit 1) (in_bom {"no" if hidden else "yes"}) (on_board {"no" if hidden else "yes"}) (dnp {"yes" if comp["dnp"] else "no"}) (uuid {Q(UID(ref))}) {props} (instances (project {Q(NAME)} (path {Q(path)} (reference {Q(ref)}) (unit 1)))))'
    for num,_,_,px,py,angle in pins:
        xx,yy=round(x+px,4),round(y-py,4); net=comp['nets'].get(num)
        if net is None:
            result+=f'(no_connect (at {xx} {yy}) (uuid {Q(UID(ref+num+"nc"))}))'
            continue
        end=round(xx+(-2.54 if angle==0 else 2.54),4)
        result+=f'(wire (pts (xy {xx} {yy}) (xy {end} {yy})) (stroke (width 0) (type default)) (uuid {Q(UID(ref+num+"wire"))}))'
        # Global labels make the electrical contract explicit across sheets.
        result+=f'(global_label {Q(net)} (shape bidirectional) (at {end} {yy} {180 if angle==0 else 0}) (effects (font (size 0.85 0.85)) (justify {"right" if angle==0 else "left"})) (uuid {Q(UID(ref+num+"label"))}))'
    return result

ROOT.mkdir(parents=True,exist_ok=True)
cached='\n'.join(s.replace('(symbol '+Q(k),'(symbol '+Q(LIB+':'+k),1) for k,s in definitions.items())
rootitems=text('BABEL RADIO / ESP32-S3-WROOM-1-N8R8',15,14,2)
rootitems+=text('Revision D prototype - ONBOARD CHARGING - NOT FOR FABRICATION',15,21,1.3)
rootitems+=text('USB-C >=1.5A -> fuse/TVS -> permission gate -> power path <- protected 1S battery\nSYS_RAW -> TPS63070 -> 3.3V host, display and gated daughter supply\nHardware charge-temperature window; WAMR / BLE on host; driver on daughter EEPROM',15,30,1.2)
for idx,(name,data) in enumerate(pages.items(),2):
    sid=UID(name); path='/'+UID('root')+'/'+sid
    heights=[30.48]*4; items=text(data['title'],12,14,1.7)
    for comp in data['parts']:
        col=min(range(4),key=lambda i:heights[i]); h=pinsets[comp['kind']][1]
        x=round(53.34+col*101.6,4); y=round(heights[col]+h+7.62,4)
        items+=render_component(comp,x,y,path)
        heights[col]=round(y+h+12.7,4)
    end=max(heights)+5
    assert end+len(data['notes'])*5 < 265,(name,heights)
    items+=text('\n'.join(data['notes']),12,end,1.2)
    sheet=f'(kicad_sch (version 20250114) (generator "eeschema") (uuid {Q(sid)}) (paper "A3") (title_block (title {Q(data["title"])}) (date "2026-10-19") (rev "D-DRAFT")) (lib_symbols {cached}) {items})\n'
    (ROOT/(name+'.kicad_sch')).write_text(sheet)
    yy=63+(idx-2)*24
    rootitems+=f'(sheet (at 15 {yy}) (size 120 15) (stroke (width 0.254) (type default)) (fill (color 0 0 0 0)) (uuid {Q(sid)}) {prop("Sheetname",data["title"],75,yy-2)} {prop("Sheetfile",name+".kicad_sch",75,yy+17)} (instances (project {Q(NAME)} (path {Q("/"+UID("root"))} (page {Q(idx)})))))'
rootitems+=text('QUALIFICATION / RELEASE GATES\n- Verify mechanical mock-up and custom land patterns\n- Keyed carrier, retention and battery protection\n- USB cold-start, discharge thermals and RF tests\n- ESD and insertion tests; POWER OFF before swapping\n- WAMR memory / EEPROM sizing qualification',151,65,1.3)
rootitems+=text('Charging is disabled by R90 DNP until bench qualification.\nUse the selected protected pack and verified harness.\nRouting is in progress; see ../ROUTING.md. Not for fabrication.',151,115,1.3)
(ROOT/(NAME+'.kicad_sch')).write_text(f'(kicad_sch (version 20250114) (generator "eeschema") (uuid {Q(UID("root"))}) (paper "A3") (lib_symbols) {rootitems} (sheet_instances (path "/" (page "1"))))\n')
(ROOT/(LIB+'.kicad_sym')).write_text('(kicad_symbol_lib (version 20241209) (generator "babel")\n'+'\n'.join(definitions.values())+')\n')
(ROOT/'sym-lib-table').write_text(f'(sym_lib_table (version 7) (lib (name {Q(LIB)}) (type "KiCad") (uri "${{KIPRJMOD}}/{LIB}.kicad_sym") (options "") (descr "Babel radio project symbols")))\n')
# Resolve the user's supplied KiCad footprint libraries without global setup.
fp_libraries=sorted({x['fp'].split(':')[0] for x in components if x['fp']})
(ROOT/'fp-lib-table').write_text('(fp_lib_table (version 7)\n'+''.join(
    f'(lib (name {Q(lib)}) (type "KiCad") (uri "${{KIPRJMOD}}/{"../Babel.pretty" if lib=="Babel" else "../../AppDir/share/kicad/footprints/"+lib+".pretty"}") (options "") (descr "Project/workspace library"))\n'
    for lib in fp_libraries)+')\n')
project=ROOT/(NAME+'.kicad_pro')
if not project.exists(): project.write_text(json.dumps({'meta':{'filename':project.name,'version':1}},indent=2)+'\n')
(ROOT/'expected-nets.json').write_text(json.dumps({'connected':expected,'nc':nc},indent=2)+'\n')
with (ROOT/'bom.csv').open('w') as f:
    w=csv.writer(f, lineterminator='\n');w.writerow(['Reference','Value','Assembly','Footprint','Datasheet','Sheet','MPN'])
    for x in components:
        if not x['ref'].startswith('#'): w.writerow([x['ref'],x['value'],'DNP' if x['dnp'] else 'FIT',x['fp'],x['ds'],x['page'],x.get('mpn','')])
with (ROOT/'gpio-map.csv').open('w') as f:
    w=csv.writer(f, lineterminator='\n'); w.writerow(['GPIO','Module pad','Net'])
    for pin,gpio in sorted(gpio_by_pin.items(),key=lambda x:x[1]): w.writerow([gpio,pin,signals.get(gpio,'NC / RESERVED')])
print(f'Generated {len(pages)+1} sheets, {sum(not c['ref'].startswith('#') for c in components)} BOM items, {len(expected)} connected pads.')
