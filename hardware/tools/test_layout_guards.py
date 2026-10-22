"""Negative tests for frozen-anchor and antenna checks; never saves boards."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
baseline = subprocess.run([sys.executable, 'hardware/tools/check_layout_seeds.py'],
                          cwd=root, capture_output=True, text=True)
if baseline.returncode:
    raise SystemExit('Baseline must pass before negative tests:\n' + baseline.stdout + baseline.stderr)
cases = {
    'locked connector off board': "fps['J2'].SetPosition(k.VECTOR2I(k.FromMM(100),k.FromMM(100)))",
    'USB connector rotated': "fps['J4'].SetOrientationDegrees(0)",
    'OLED mounting hole moved': "fps['H7'].SetPosition(k.VECTOR2I(k.FromMM(15.76),k.FromMM(17.54)))",
    'antenna routing restriction disabled': "next(z for z in b.Zones() if z.GetZoneName()=='Antenna').SetDoNotAllowTracks(False)",
}
for label, mutation in cases.items():
    code = f'''
import pcbnew as k, runpy
original=k.LoadBoard
held=[]
def changed(path):
    b=original(path)
    held.append(b)
    if '/radio/' in str(path):
        fps={{f.GetReference():f for f in b.GetFootprints()}}
        {mutation}
    return b
k.LoadBoard=changed
try:
    runpy.run_path('hardware/tools/check_layout_seeds.py',run_name='__main__')
except AssertionError:
    pass
else:
    raise SystemExit('Mutation escaped audit')
'''
    result = subprocess.run([sys.executable, '-c', code], cwd=root, capture_output=True, text=True)
    if result.returncode:
        raise SystemExit(f'{label}: {result.stdout}\n{result.stderr}')
    print(f'PASS rejects {label}')

# Simulate the default project presets that pcbnew can save when a scratch PCB
# is opened without its companion project. Do not write the real project file.
code = '''
import json, runpy
original=json.loads
def changed(text,*args,**kwargs):
    data=original(text,*args,**kwargs)
    if 'net_settings' in data:
        data['net_settings']['classes']=[c for c in data['net_settings']['classes'] if c['name']=='Default']
    return data
json.loads=changed
try:
    runpy.run_path('hardware/tools/check_layout_seeds.py',run_name='__main__')
except AssertionError:
    pass
else:
    raise SystemExit('Default routing presets escaped audit')
'''
result = subprocess.run([sys.executable, '-c', code], cwd=root, capture_output=True, text=True)
if result.returncode:
    raise SystemExit(result.stdout + result.stderr)
print('PASS rejects lost power/USB project presets')
