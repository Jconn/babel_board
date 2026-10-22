"""Raster regression checks; run with a Python environment containing NumPy."""
import json
from pathlib import Path
import runpy
import struct
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch
import numpy as np

with TemporaryDirectory(prefix='babel-grid-test-') as tmp:
    root = Path(tmp)
    geom = {'W': 3., 'H': 3., 'items': [
        {'id': 'mount', 'net': '', 'layer': 'F',
         'polys': [[[.3, .3], [.6, .3], [.6, .6], [.3, .6]]]},
        {'id': 'signal', 'net': 'SIGNAL', 'layer': 'F',
         'polys': [[[2.5, .3], [2.7, .3], [2.7, .6], [2.5, .6]]]}],
        'keep': [], 'bodies': [], 'holes': [[1.5, 1.9, .15]],
        'nets': {'SIGNAL': {'width': .2, 'clusters': [['signal']]}}}
    source = root / 'geom.json'; source.write_text(json.dumps(geom))
    grid = root / 'grid.bin'; names = root / 'names.json'
    script = Path(__file__).with_name('prep_pf.py')
    with patch.object(sys, 'argv', [str(script), str(source), str(grid), str(names)]):
        runpy.run_path(str(script), run_name='__main__')
    with grid.open('rb') as stream:
        nx, ny, pitch = struct.unpack('<iid', stream.read(16))
        labels = np.frombuffer(stream.read(3 * nx * ny * 4), '<i4').reshape(3, ny, nx)
        forbidden = np.frombuffer(stream.read(nx * ny), np.uint8).reshape(ny, nx)
    assert labels[0, int(.45 / pitch), int(.45 / pitch)] == -1
    assert labels[0, int(.45 / pitch), int(2.6 / pitch)] > 0
    x, y = np.meshgrid((np.arange(nx) + .5) * pitch, (np.arange(ny) + .5) * pitch)
    must_block = np.hypot(x - 1.5, y - 1.9) < .8
    assert np.all(forbidden[must_block]), 'Off-grid hole spacing underestimates clearance'
    print('PASS unassigned pads block copper; named pads remain terminals; off-grid holes block every unsafe via center')
