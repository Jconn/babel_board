"""Create unrouted placement-start boards from verified schematic exports.

Run using AppDir/bin/python3.11. Refuses to overwrite existing boards unless
--replace-generated is supplied. Never run that flag after manual layout work.
"""
from pathlib import Path
import argparse
import xml.etree.ElementTree as ET
import pcbnew as k

ROOT=Path(__file__).resolve().parents[2]
HW=ROOT/'hardware'
parser=argparse.ArgumentParser()
parser.add_argument('--replace-generated',action='store_true')
args=parser.parse_args()

def xy(x,y): return k.VECTOR2I(k.FromMM(x),k.FromMM(y))
def line(b,a,c,layer=k.Edge_Cuts):
    s=k.PCB_SHAPE();s.SetShape(k.SHAPE_T_SEGMENT);s.SetStart(xy(*a));s.SetEnd(xy(*c))
    s.SetLayer(layer);s.SetWidth(k.FromMM(.05));b.Add(s)
def box(b,x1,y1,x2,y2,layer=k.Dwgs_User):
    pts=[(x1,y1),(x2,y1),(x2,y2),(x1,y2)]
    for a,c in zip(pts,pts[1:]+pts[:1]):line(b,a,c,layer)
def note(b,text,x,y):
    t=k.PCB_TEXT(b);t.SetText(text);t.SetPosition(xy(x,y));t.SetLayer(k.Dwgs_User)
    t.SetTextSize(xy(1,1));t.SetTextThickness(k.FromMM(.15));b.Add(t)
def keepout(b,x1,y1,x2,y2,layers,only_components=False):
    z=k.ZONE(b);z.SetIsRuleArea(True)
    z.SetZoneName('Battery' if only_components else 'Antenna')
    ls=k.LSET()
    for l in layers:ls.AddLayer(l)
    z.SetLayerSet(ls);z.SetDoNotAllowFootprints(only_components)
    z.SetDoNotAllowTracks(not only_components);z.SetDoNotAllowVias(not only_components)
    z.SetDoNotAllowPads(not only_components);z.SetDoNotAllowZoneFills(not only_components)
    z.Outline().NewOutline()
    for x,y in [(x1,y1),(x2,y1),(x2,y2),(x1,y2)]:z.Outline().Append(k.FromMM(x),k.FromMM(y))
    b.Add(z)
def libpath(lib,folder):
    if lib=='Babel':return HW/'Babel.pretty'
    if lib=='Babel_IR':return folder/'Babel_IR.pretty'
    return ROOT/'AppDir/share/kicad/footprints'/(lib+'.pretty')
def hole(b,ref,x,y,diam=2.2):
    f=k.FOOTPRINT(b);f.SetReference(ref);f.SetValue('M2 mechanical / NPTH')
    p=k.PAD(f);p.SetNumber('');p.SetAttribute(k.PAD_ATTRIB_NPTH);p.SetShape(k.PAD_SHAPE_CIRCLE)
    p.SetSize(xy(diam,diam));p.SetDrillSize(xy(diam,diam))
    ls=k.LSET.AllCuMask();ls.AddLayer(k.F_Mask);ls.AddLayer(k.B_Mask);p.SetLayerSet(ls)
    f.Add(p);f.SetPosition(xy(x,y));b.Add(f)
    f.SetAttributes(k.FP_EXCLUDE_FROM_BOM|k.FP_EXCLUDE_FROM_POS_FILES)
    return f

for folder,name in [(HW/'radio','babel-radio'),(HW/'ir-daughter','babel-ir-daughter')]:
    dest=folder/(name+'.kicad_pcb')
    if dest.exists() and not args.replace_generated:raise SystemExit(f'Refusing to overwrite {dest}')
    b=k.BOARD();b.SetFileName(str(dest));b.SetCopperLayerCount(4 if name=='babel-radio' else 2)
    b.GetDesignSettings().SetBoardThickness(k.FromMM(1.6 if name=='babel-radio' else 1.57))
    doc=ET.parse(folder/(name+'.net.xml'))
    nets={};pin_net={}
    for net in doc.findall('./nets/net'):
        ni=k.NETINFO_ITEM(b,net.attrib['name'].lstrip('/'));b.Add(ni);nets[net.attrib['name']]=ni
        for node in net.findall('node'):pin_net[(node.attrib['ref'],node.attrib['pin'])]=ni
    fps={}
    for i,c in enumerate(doc.findall('./components/comp')):
        ref=c.attrib['ref'];lib,fp=c.findtext('footprint').split(':',1)
        f=k.FootprintLoad(str(libpath(lib,folder)),fp)
        assert f is not None,(ref,lib,fp)
        f.SetReference(ref);f.SetValue(c.findtext('value'));f.SetFPID(k.LIB_ID(lib,fp))
        path=c.find('sheetpath').attrib['tstamps']+c.findtext('tstamps').split()[0]
        f.SetPath(k.KIID_PATH(path))
        f.SetDNP(any(p.attrib.get('name')=='dnp' for p in c.findall('property')))
        b.Add(f)
        for pad in f.Pads():
            if pad.GetNumber():pad.SetNet(pin_net[(ref,pad.GetNumber())])
        # Clearly outside outline: these components are NOT a completed placement.
        f.SetPosition(xy(85+(i%10)*12,10+(i//10)*12));fps[ref]=f
    if name=='babel-radio':
        box(b,0,0,60,80,k.Edge_Cuts)
        anchors={'U1':(30,72.25,180),'J1':(30,7,0),'J4':(2.5,45,270),
                 'J2':(10,25,0),'J5':(48,32,0),'SW4':(57,63,90),
                 'SW1':(7,70,0),'SW2':(7,64,0),'SW3':(53,70,0)}
        for ref,(x,y,a) in anchors.items():
            fps[ref].SetOrientationDegrees(a);fps[ref].SetPosition(xy(x,y));fps[ref].SetLocked(True)
        for i,(x,y) in enumerate([(4,4),(56,4),(4,76),(56,76),(12,7),(48,7)],1):hole(b,f'H{i}',x,y)
        # OLED M2 mounting pattern, 2.5 mm drills from original breakout CAD.
        for i,(x,y) in enumerate([(14.76,17.54),(45.24,17.54),(14.76,59.45),(45.24,59.45)],7):hole(b,f'H{i}',x,y,2.5)
        box(b,12.22,15,47.78,61.99);note(b,'OLED above PCB: 14 mm standoffs',30,38)
        box(b,12.75,10,47.25,63,k.Cmts_User);note(b,'Battery BELOW; no bottom components here',30,55)
        box(b,9,1,51,13);note(b,'Keyed boot: keep this envelope clear',30,-3)
        box(b,6,79,54,100,k.Cmts_User);note(b,'ANTENNA: no copper/metal/battery/display',30,95)
        keepout(b,6,79,54,100,[k.F_Cu,k.In1_Cu,k.In2_Cu,k.B_Cu])
        keepout(b,12.75,10,47.25,63,[k.B_Cu],True)
        note(b,'60 x 80 mm / 4 layers / UNROUTED PLACEMENT START',30,107)
        note(b,'Unplaced circuit blocks ->',90,-3)
    else:
        # Absolute J1 tip at (20,45), body -15..15, 35 mm high.
        outline=[(-5.885,0),(5.885,0),(5.885,-10),(15,-10),(15,-35),(-15,-35),(-15,-10),(-5.885,-10)]
        pts=[(20+x,45+y) for x,y in outline]
        for a,c in zip(pts,pts[1:]+pts[:1]):line(b,a,c)
        fps['J1'].SetPosition(xy(20,45));fps['J1'].SetLocked(True)
        fps['U1'].SetPosition(xy(20,16));fps['U1'].SetLocked(True)
        hole(b,'H1',10,22);hole(b,'H2',30,18)
        box(b,5,10,35,25);note(b,'Sensor thermal/optical zone; only U1 + C1',20,6)
        note(b,'30 x 35 mm / 1.57 mm / 2 layers / HARD GOLD + BEVEL',20,53)
        note(b,'Power OFF for initial module changes',20,56)
    k.SaveBoard(str(dest),b)
    if name=='babel-radio':
        # pcbnew's Python bindings do not expose the stackup descriptor methods.
        # Serialize the documented KiCad stackup in this generated seed only.
        stack='''(stackup
            (layer "F.SilkS" (type "Top Silk Screen"))
            (layer "F.Mask" (type "Top Solder Mask") (thickness 0.01524))
            (layer "F.Cu" (type "copper") (thickness 0.035))
            (layer "dielectric 1" (type "prepreg") (thickness 0.2104) (material "FR4 7628") (epsilon_r 4.4) (loss_tangent 0.02))
            (layer "In1.Cu" (type "copper") (thickness 0.0152))
            (layer "dielectric 2" (type "core") (thickness 1.065) (material "FR4") (epsilon_r 4.6) (loss_tangent 0.02))
            (layer "In2.Cu" (type "copper") (thickness 0.0152))
            (layer "dielectric 3" (type "prepreg") (thickness 0.2104) (material "FR4 7628") (epsilon_r 4.4) (loss_tangent 0.02))
            (layer "B.Cu" (type "copper") (thickness 0.035))
            (layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01524))
            (layer "B.SilkS" (type "Bottom Silk Screen"))
            (copper_finish "ENIG") (dielectric_constraints yes)
        )'''
        # Actual impedance mask model is 0.01524 over trace / 0.03048 between
        # traces. Nominal finished thickness is 1.6 mm, not an exact sum promise.
        dest.write_text(dest.read_text().replace('(setup', '(setup\n'+stack,1))
    assert len(list(k.LoadBoard(str(dest)).GetFootprints()))==len(list(b.GetFootprints()))
    print(f'Saved {dest}: {len(fps)} electrical footprints, all exported pad nets assigned; 0 tracks')
