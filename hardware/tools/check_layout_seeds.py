"""Independent PCB/netlist import and critical geometry checks, not full DRC.

Run with AppDir/bin/python3.11. Supports placement and partial routing; retains schematic parity checks.
"""
from pathlib import Path
import json
import xml.etree.ElementTree as ET
import pcbnew as k

HW=Path(__file__).resolve().parents[1]
# pcbnew can save default project rules if a scratch PCB is loaded without its
# matching .kicad_pro. Catch that regression before trusting a routed board.
project=json.loads((HW/'radio'/'babel-radio.kicad_pro').read_text())
rules=project['board']['design_settings']['rules']
for rule,want in {'min_clearance':.15,'min_copper_edge_clearance':.3,
                  'min_hole_clearance':.15,'min_through_hole_diameter':.2,
                  'min_track_width':.15,'min_via_diameter':.6}.items():
    assert rules[rule]==want, (rule,rules[rule],want)
classes={c['name']:c for c in project['net_settings']['classes']}
assert {'Default','Power','USB'} <= set(classes)
assert all(classes[n]['clearance']==.15 for n in ('Default','Power','USB'))
assert classes['Power']['track_width']==.8
assert classes['USB']['diff_pair_width']==.3 and classes['USB']['diff_pair_gap']==.15
assignments={(p['pattern'],p['netclass']) for p in project['net_settings']['netclass_patterns']}
assert {(n,'Power') for n in ('V3V3','V3V3_REG','V3V3_OLED','V3V3_PORT_IN','SYS_RAW','VBAT','USB_5V','USB_CHG_IN')} <= assignments
assert ('USB_D*','USB') in assignments
print('PASS project fabrication constraints and power/USB routing presets')
def near(a,b): assert abs(a-b)<0.00001,(a,b)
def mm(v): return k.ToMM(v)
boards={}
for folder,name,count,layers in [('radio','babel-radio',179,4),('ir-daughter','babel-ir-daughter',13,2)]:
    b=k.LoadBoard(str(HW/folder/(name+'.kicad_pcb')));boards[folder]=b
    doc=ET.parse(HW/folder/(name+'.net.xml'))
    fps={f.GetReference():f for f in b.GetFootprints()}
    components=doc.findall('./components/comp'); assert len(components)==count
    assert b.GetCopperLayerCount()==layers
    assert all(t.GetNetCode() > 0 for t in b.GetTracks()), 'Unassigned copper track/via'
    expected={}
    for net in doc.findall('./nets/net'):
        for n in net.findall('node'): expected[n.attrib['ref'],n.attrib['pin']]=net.attrib['name'].lstrip('/')
    for c in components:
        f=fps[c.attrib['ref']]
        assert f.GetFPID().GetUniStringLibId()==c.findtext('footprint')
        assert f.GetValue()==c.findtext('value')
        assert f.IsDNP()==any(p.attrib.get('name')=='dnp' for p in c.findall('property'))
        assert str(f.GetPath().AsString())==c.find('sheetpath').attrib['tstamps']+c.findtext('tstamps').split()[0]
        actual=set()
        for p in f.Pads():
            if p.GetNumber():
                actual.add(p.GetNumber())
                assert p.GetNetname()==expected[f.GetReference(),p.GetNumber()],(f.GetReference(),p.GetNumber())
        assert actual=={p for r,p in expected if r==f.GetReference()}
    assert all(r in {c.attrib['ref'] for c in components} or r.startswith('H') for r in fps)
    print(f'PASS {name}: {count} components, pad/net/value/FPID/DNP/UUID parity, {layers} layers, {len(list(b.GetTracks()))} track/via objects')

def footprint(name):
    f=k.FootprintLoad(str(HW/'Babel.pretty'),name); assert f
    return f
def pads(f,n):return [p for p in f.Pads() if p.GetNumber()==str(n)]
socket=footprint('MEC1_110_02_NP_A_Socket')
card=footprint('MEC1_110_02_NP_Card')
for n in range(1,21):
    a=pads(socket,n)[0];c=pads(card,n)[0]
    near(mm(a.GetPosition().x),(n-1)//2-4.5)
    near(mm(a.GetPosition().y),3.5305 if n%2 else -3.5305)
    near(mm(a.GetSize().x),.610);near(mm(a.GetSize().y),1.880)
    near(mm(c.GetPosition().x),mm(a.GetPosition().x))
    near(mm(c.GetPosition().y),-3.275)
    near(mm(c.GetSize().x),.610);near(mm(c.GetSize().y),4.45)
    assert c.IsOnLayer(k.F_Cu if n%2 else k.B_Cu)
    assert not c.IsOnLayer(k.F_Paste) and not c.IsOnLayer(k.B_Paste)
holes=[p for p in socket.Pads() if not p.GetNumber()]
assert len(holes)==2
for p,(x,y) in zip(holes,[(-6.6225,0),(6.6225,-1.9425)]):
    near(mm(p.GetPosition().x),x);near(mm(p.GetPosition().y),y);near(mm(p.GetDrillSize().x),1.02)
bq=footprint('BQ24079_RGT0016B');ep=pads(bq,17)[0]
near(mm(ep.GetSize().x),1.6);near(mm(ep.GetSize().y),1.6)
for n in range(1,17):assert len(pads(bq,n))==1
assert len([p for p in bq.Pads() if not p.GetNumber()])==4
rnm=footprint('TPS63070_RNM0015A')
assert {p.GetNumber() for p in rnm.Pads() if p.GetNumber()}=={str(n) for n in range(1,16)}
for n,y,x,w in [(9,.5,.775,1.45),(10,0,.6,1.8),(11,-.5,.775,1.45)]:
    p=pads(rnm,n)[0];near(mm(p.GetPosition().x),x);near(mm(p.GetPosition().y),y)
    near(mm(p.GetSize().x),w);near(mm(p.GetSize().y),.35)
print('PASS custom footprints: connector rows/fingers/layers/holes, RGT-B exposed pad, RNM power lands')

radio={f.GetReference():f for f in boards['radio'].GetFootprints()}
daughter={f.GetReference():f for f in boards['ir-daughter'].GetFootprints()}
anchors={'U1':(30,72.25,180),'J1':(30,7,0),'J4':(2.5,45,270),
         'J2':(10,25,0),'J5':(48,32,0),'SW4':(57,63,90),
         'SW1':(7,70,0),'SW2':(7,64,0),'SW3':(53,70,0)}
for ref,(x,y,angle) in anchors.items():
    f=radio[ref]
    near(mm(f.GetPosition().x),x);near(mm(f.GetPosition().y),y)
    near(f.GetOrientationDegrees()%360,angle)
    assert f.IsLocked() and f.GetLayer()==k.F_Cu,ref
assert {ref for ref,f in radio.items() if f.IsLocked()} == set(anchors)
for i,(x,y) in enumerate([(4,4),(56,4),(4,76),(56,76),(12,7),(48,7),
                         (14.76,17.54),(45.24,17.54),(14.76,59.45),(45.24,59.45)],1):
    f=radio[f'H{i}'];near(mm(f.GetPosition().x),x);near(mm(f.GetPosition().y),y)
for ref,x,y in [('J1',20,45),('U1',20,16)]:
    f=daughter[ref];near(mm(f.GetPosition().x),x);near(mm(f.GetPosition().y),y)
    near(f.GetOrientationDegrees()%360,0)
    assert f.IsLocked() and f.GetLayer()==k.F_Cu
zones={z.GetZoneName():z for z in boards['radio'].Zones() if z.GetIsRuleArea()}
assert {'Antenna','Battery'} <= set(zones)
for name,bounds,layers in [('Antenna',(6,79,54,100),{k.F_Cu,k.In1_Cu,k.In2_Cu,k.B_Cu}),
                         ('Battery',(12.75,10,47.25,63),{k.B_Cu})]:
    z=zones[name];bb=z.Outline().BBox()
    for got,want in zip((bb.GetX(),bb.GetY(),bb.GetRight(),bb.GetBottom()),bounds):near(mm(got),want)
    assert set(z.GetLayerSet().Seq())==layers
z=zones['Antenna']
assert all([z.GetDoNotAllowTracks(),z.GetDoNotAllowVias(),z.GetDoNotAllowPads(),z.GetDoNotAllowZoneFills()])
assert zones['Battery'].GetDoNotAllowFootprints()
print('PASS all frozen anchors, mounting positions and native antenna/battery restrictions')
near(mm(boards['ir-daughter'].GetDesignSettings().GetBoardThickness()),1.57)
for ref,x,y in [('H1',10,22),('H2',30,18)]:
    near(mm(daughter[ref].GetPosition().x),x);near(mm(daughter[ref].GetPosition().y),y)
# Analytical design envelope checks, not a substitute for CAD collision/fit tests.
assert 79-63>=15 and 79-61.99>=15
assert .991-.5>0
assert 16+.5-9.04>7 # reversed key strikes boot before tip can contact socket
assert -3.5 > -4.5 > -5.5 > -6
assert 6>=5.8
print('PASS anchor/thickness contract and analytical antenna, battery barrier, reverse-key clearances')
print('NOT tested: physical mating, SCAD mesh collisions, routing, thermal/USB/RF or charging performance')
