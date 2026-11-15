#!/usr/bin/env python3
"""Compile the real DXVK pipeline-state checks with and without the iOS policy.

Run after tools/dxvk/build.py iphoneos has configured the pinned checkout.
This checks zero/constant strides, instance bindings and pipeline key separation;
the Metal validation run on iPad remains the integration check.
"""
import json
from pathlib import Path
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
import argparse
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('commands', type=Path, help='external iOS build/compile_commands.json')
commands = ap.parse_args().commands.resolve()
if not commands.is_file():
    raise SystemExit('First configure/build tools/dxvk/build.py iphoneos')
row = next(x for x in json.loads(commands.read_text()) if x['file'].endswith('dxvk_context.cpp'))
includes = [x for x in shlex.split(row['command']) if x.startswith('-I')]
with tempfile.TemporaryDirectory(prefix='ios-strides-', dir=None) as temp:
    for ios in [False, True]:
        output = Path(temp) / ('check-ios' if ios else 'check-default')
        subprocess.run(['xcrun', 'clang++', '-std=c++17', *includes,
                        *(['-DDXVK_WSI_IOS'] if ios else []),
                        str(Path(__file__).with_suffix('.cpp')), '-o', str(output)],
                       cwd=row['directory'], check=True)
        subprocess.run([str(output)], check=True)
        print('PASS', 'iOS static strides' if ios else 'unchanged non-iOS strides',
              ': zero stride, actual strides, instancing, distinct pipeline keys')
