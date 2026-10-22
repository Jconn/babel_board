"""Revision D static audit of restored charging, NOT a safety certification.

Sources: TI BQ2407x, TPS3700, TPS709 and Jauch 251555 specifications.
Includes divider loading and comparator leakage. Pack beta tolerance is unknown:
+/-5% below is a stress assumption, NOT a manufacturer guarantee. Thermal lag
and the actual pack curve still require physical qualification.
"""
from pathlib import Path
import runpy
from itertools import product
from math import log

# Refuse to report margins for a different or stale circuit. This independent
# checker compares the export to the manifest and asserts audited part values,
# critical pin maps and R90 DNP before any hard-coded corner model is evaluated.
runpy.run_path(str(Path(__file__).with_name('verify_netlist.py')))

def temp(r, r25=10000, beta=3435):
    return 1 / (1 / 298.15 + log(r / r25) / beta) - 273.15

def trip_resistance(vcc, rbias, rh, rhl, rc, rcl, ih, ic, threshold, hot):
    # Solve NTC-node KCL including both divider loads and input leakage.
    upper, lower, leakage = (rh, rhl, ih) if hot else (rc, rcl, ic)
    vn = threshold * (1 + upper/lower) + leakage * upper
    bias = vcc/rbias - ih*rhl/(rh+rhl) - ic*rcl/(rc+rcl)
    conductance = bias/vn - 1/rbias - 1/(rh+rhl) - 1/(rc+rcl)
    assert conductance > 0
    return 1/conductance

ri = 5360
imin, inom, imax = 797/(ri*1.01), 890/ri, 975/(ri*.99)
assert imax < .2*.950
assert 4.141 < 4.2  # BQ24079 guaranteed CV maximum vs pack maximum.
input_max = 1720/(1780*.99)
assert input_max + .010 < 1.5  # 10mA allowance for CC/control rail.
print(f'Charge current: {imin*1000:.1f} / {inom*1000:.1f} / {imax*1000:.1f} mA min/nom/max')
print(f'USB charger input maximum: {input_max*1000:.1f} mA; source requirement >=1500mA')
print('Charge voltage: 4.1V nominal, 4.141V maximum; less runtime than a full 4.2V charge.')

results = {}
for label, hot, thresholds, nominal in [
        ('cold cutoff', False, (.396,.404), .400),
        ('cold resume', False, (.387,.400), .3945),
        ('hot cutoff', True, (.387,.400), .3945),
        ('hot resume', True, (.396,.404), .400)]:
    corners = []
    for signs in product((-1,1), repeat=5):
        resistors = [n*(1+s*.001) for n,s in zip((10000,200000,100000,412000,100000),signs)]
        for vcc, ih, ic, threshold, r25, beta in product(
                (3.3*.98,3.3*1.02), (-25e-9,25e-9),(-15e-9,15e-9),
                thresholds,(9900,10100),(3435*.95,3435*1.05)):
            corners.append(temp(trip_resistance(vcc,*resistors,ih,ic,threshold,hot),r25,beta))
    nominal_temp=temp(trip_resistance(3.3,10000,200000,100000,412000,100000,0,0,nominal,hot))
    results[label]=(min(corners),max(corners))
    print(f'{label}: nominal {nominal_temp:.2f} C, screened corners {min(corners):.2f}..{max(corners):.2f} C')
assert results['cold cutoff'][0] > 0
assert results['hot cutoff'][1] < 55
assert results['cold resume'][1] < results['hot resume'][0]

# Missing/open NTC must trip the cold comparator; short NTC must trip hot.
for signs in product((-1,1), repeat=5):
    rb,rh,rhl,rc,rcl=[n*(1+s*.001) for n,s in zip((10000,200000,100000,412000,100000),signs)]
    for vcc,ih,ic in product((3.3*.98,3.3*1.02),(-25e-9,25e-9),(-15e-9,15e-9)):
        vopen=(vcc/rb-ih*rhl/(rh+rhl)-ic*rcl/(rc+rcl))/(1/rb+1/(rh+rhl)+1/(rc+rcl))
        assert (vopen-ic*rc)/(1+rc/rcl) > .404
        assert (-ih*rh)/(1+rh/rhl) < .387
print('PASS: open/short NTC inhibit charging across screened electrical corners.')

timer_min=10*71.5*.999*36/3600
timer_nom=10*71.5*48/3600
timer_max=10*71.5*1.001*60/3600
assert 18 < 71.5*.999 < 71.5*1.001 < 72
print(f'Fast-charge timer: {timer_min:.2f} / {timer_nom:.2f} / {timer_max:.2f} h min/nom/max')
print(f'Precharge timer: {timer_min*6:.1f} / {timer_nom*6:.1f} / {timer_max*6:.1f} minutes')
print(f'Conservative 1Ah/min-current time before taper: {1/imin:.2f} h; completion needs bench validation.')
print('PASS: static margins. R90 remains DNP until pack curve, thermal and fault tests pass.')
