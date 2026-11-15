# SPDX-License-Identifier: MIT
"""Fetch a pinned upstream into a new directory outside this checkout and apply patches."""
import argparse
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = {
    'dxvk': ('https://github.com/doitsujin/dxvk.git', 'v3.1.1',
             'b1a1c99ab52b687cf950d62c88bc2fa316b41663'),
    'moltenvk': ('https://github.com/KhronosGroup/MoltenVK.git', 'v1.4.2',
                'db66022459ffb663aa2b50f6b018bc2e124f5edf'),
}


def external(path):
    path = Path(path).resolve()
    if path == ROOT or ROOT in path.parents:
        raise ValueError('source and build directories must be outside the public checkout')
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('project', choices=PROJECTS)
    ap.add_argument('destination', type=external)
    args = ap.parse_args()
    if args.destination.exists():
        ap.error('destination already exists; choose a new directory')
    url, tag, revision = PROJECTS[args.project]
    subprocess.run(['git', 'clone', '--depth', '1', '--branch', tag, url, str(args.destination)], check=True)
    actual = subprocess.check_output(['git', '-C', str(args.destination), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != revision:
        raise SystemExit('upstream tag does not match the reviewed commit; no patches applied')
    for patch in sorted((ROOT / 'tools' / args.project).glob('00*.patch')):
        for options in (['--check'], ['--whitespace=nowarn']):
            subprocess.run(['git', '-C', str(args.destination), 'apply', *options, str(patch)], check=True)
        print('Applied', patch.name, flush=True)
    if args.project == 'dxvk':
        subprocess.run(['git', '-C', str(args.destination), 'submodule', 'update', '--init', '--recursive', '--depth', '1'], check=True)
    print('Patched upstream:', args.destination)


if __name__ == '__main__':
    main()
