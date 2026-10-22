"""Project land patterns from TI RNM0015A and Samtec MEC1 rev R drawings.

Dimensions in mm, viewed from host top. See MECHANICAL.md for manufacturing
notes and the limits of these unbuilt patterns. No guessed generic QFN pad 16.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT/'Babel.pretty'
LIB.mkdir(exist_ok=True)

def start(name, descr):
    return [f'(footprint "{name}" (version 20241229) (generator "pcbnew") (layer "F.Cu") (attr smd)',
            f'(descr "{descr}")',
            '(property "Reference" "REF**" (at 0 -6 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))',
            f'(property "Value" "{name}" (at 0 6 0) (layer "F.Fab") (effects (font (size 0.7 0.7) (thickness 0.1))))']

def pad(items,n,x,y,w,h,layers='"F.Cu" "F.Paste" "F.Mask"',extra=''):
    items.append(f'(pad "{n}" smd rect (at {x} {y}) (size {w} {h}) (layers {layers}) {extra})')

def rect(items,x1,y1,x2,y2,layer,width=.05):
    items.append(f'(fp_rect (start {x1} {y1}) (end {x2} {y2}) (stroke (width {width}) (type default)) (fill none) (layer "{layer}"))')

def save(name,items):
    (LIB/(name+'.kicad_mod')).write_text('\n'.join(items)+')\n')

name='TPS63070_RNM0015A'
p=start(name,'TI RNM0015A 4222000/B 03/2020; copper/mask and split paste; 15 pads')
for n,y in enumerate((-.75,-.25,.25,.75),1): pad(p,n,-1.15,y,.6,.25,extra='(solder_mask_margin 0.05)')
for n,x,y in [(5,-.725,1.4),(6,-.225,1.4),(14,-.225,-1.4),(15,-.725,-1.4)]:
    pad(p,n,x,y,.25,.6,extra='(solder_mask_margin 0.05)')
# Power pins: 0.05 mm copper beyond the mask-defined land opening.
for n,x,y in [(7,.275,1.4),(8,.775,1.4),(12,.775,-1.4),(13,.275,-1.4)]:
    pad(p,n,x,y,.35,.7,'"F.Cu" "F.Mask"','(solder_mask_margin -0.05)')
    pad(p,'',x,y,.25,.6,'"F.Paste"')
# U-shaped copper/mask/paste joins between equal-net VIN and VOUT pin pairs.
for n,y in [(7,1.225),(13,-1.225)]:
    pad(p,n,.525,y,.75,.35,'"F.Cu" "F.Mask"','(solder_mask_margin -0.05)')
    pad(p,'',.525,y,.75,.25,'"F.Paste"')
for n,y,x,w in [(9,.5,.775,1.35),(10,0,.6,1.7),(11,-.5,.775,1.35)]:
    pad(p,n,x,y,w+.1,.35,'"F.Cu" "F.Mask"','(solder_mask_margin -0.05)')
    for px,pw in ([(.14,.72),(1.065,.72)] if n==10 else [(.3875,.575),(1.1625,.575)]):
        pad(p,'',px,y,pw,.25,'"F.Paste"')
rect(p,-1.25,-1.5,1.25,1.5,'F.Fab')
rect(p,-1.75,-2,1.75,2,'F.CrtYd')
p.append('(fp_circle (center -1.65 -1.25) (end -1.55 -1.25) (stroke (width 0.1) (type default)) (fill solid) (layer "F.SilkS"))')
save(name,p)

name='BQ24079_RGT0016B'
p=start(name,'TI RGT0016B 4219033/A 08/2016; 1.6mm thermal pad, not RGT0016C')
for i in range(4):
    t=-.75+i*.5
    pad(p,i+1,-1.4,t,.6,.25,extra='(solder_mask_margin 0.05)')
    pad(p,i+5,t,1.4,.25,.6,extra='(solder_mask_margin 0.05)')
    pad(p,i+9,1.4,-t,.6,.25,extra='(solder_mask_margin 0.05)')
    pad(p,i+13,-t,-1.4,.25,.6,extra='(solder_mask_margin 0.05)')
pad(p,17,0,0,1.6,1.6,'"F.Cu" "F.Mask"','(solder_mask_margin 0.05)')
for x in (-.4,.4):
    for y in (-.4,.4): pad(p,'',x,y,.7,.7,'"F.Paste"')
rect(p,-1.5,-1.5,1.5,1.5,'F.Fab')
rect(p,-1.95,-1.95,1.95,1.95,'F.CrtYd')
p.append('(fp_circle (center -1.9 -1.2) (end -1.8 -1.2) (stroke (width 0.1) (type default)) (fill solid) (layer "F.SilkS"))')
save(name,p)

name='MEC1_110_02_NP_A_Socket'
p=start(name,'Samtec MEC1-110-02-L-D-NP-A; NP required for all 20 contacts; vertical')
# Samtec 7.061 mm is row center distance (dimension arrows at pad centers).
row=7.061/2
for i in range(10):
    x=i-4.5
    pad(p,2*i+1,x,row,.610,1.880)
    pad(p,2*i+2,x,-row,.610,1.880)
# Opposite alignment hole is 1.588 mm inward from the even-row centerline.
for x,y in [(-6.6225,0),(6.6225,-row+1.588)]:
    p.append(f'(pad "" np_thru_hole circle (at {x} {y}) (size 1.02 1.02) (drill 1.02) (layers "*.Cu" "*.Mask"))')
rect(p,-7.5,-4.6,7.5,4.6,'F.Fab')  # conservative body envelope; do not use as drill datum
rect(p,-8,-5.1,8,5.1,'F.CrtYd')
p.append(f'(fp_text user "1" (at -5.4 {row} 0) (layer "F.SilkS") (effects (font (size .8 .8) (thickness .12))))')
save(name,p)

name='MEC1_110_02_NP_Card'
p=start(name,'MEC1 NP mating card; edge at y=0; 1.57mm board; bevel/hard gold per MECHANICAL.md')
for i in range(10):
    # Odd on front, even on back at identical physical x: mirrored when viewed from back.
    for n,layer in [(2*i+1,'F'),(2*i+2,'B')]:
        pad(p,n,i-4.5,-3.275,.610,4.45,f'"{layer}.Cu" "{layer}.Mask"', '(solder_mask_margin 0.05)')
rect(p,-5.885,-8.89,5.885,0,'Dwgs.User')
p.append('(fp_text user "TIP / BEVEL - SEE MECHANICAL" (at 0 1.5 0) (layer "Dwgs.User") (effects (font (size .7 .7) (thickness .1))))')
save(name,p)
print('Generated four project footprints in',LIB)
