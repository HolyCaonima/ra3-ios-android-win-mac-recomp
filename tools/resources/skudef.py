# SPDX-License-Identifier: MIT
"""Flatten local SkuDef references without copying game resources."""
import argparse
from pathlib import Path

def contained(root, relative):
    path = (root/relative.replace('\\', '/')).resolve()
    if not path.is_relative_to(root.resolve()) or path == root.resolve():
        raise ValueError(f'path escapes resource directory: {relative}')
    return path


def flatten(game, config, stack=None):
    """Resolve bundle SkuDefs into absolute, read-only BIG references for this host."""
    stack = set() if stack is None else stack
    path = contained(game, config)
    if path in stack:
        raise ValueError(f'cyclic configuration: {config}')
    stack.add(path)
    rows = []
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        cmd, value = line.split(None, 1)
        value = value.strip('"')
        if cmd == 'add-big':
            asset = contained(game, value)
            if not asset.is_file():
                raise FileNotFoundError(asset)
            # POSIX HLE interprets /foo as C:\\foo. Z: maps to the host root;
            # use it explicitly so archives outside the writable C: resolve.
            host_path = asset.as_posix()
            rows.append('add-big '+('Z:' if host_path.startswith('/') else '')+host_path)
        elif cmd == 'add-config':
            rows.extend(flatten(game, value, stack))
        elif cmd == 'set-search-path':
            # Loose Data/Movies files live beside the original BIG files,
            # outside the writable run directory. Preserve existing search
            # entries and add the bundle root using the host's drive syntax.
            host_root = game.resolve().as_posix()
            root = ('Z:' if host_root.startswith('/') else '') + host_root
            rows.append('set-search-path ' + value + ';' + root)
        elif cmd != 'set-exe':
            raise ValueError(f'unsupported resource directive: {line}')
    stack.remove(path)
    return rows


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('root', type=Path)
    ap.add_argument('config', help='SkuDef path relative to root')
    args = ap.parse_args()
    print('\n'.join(flatten(args.root, args.config)))
