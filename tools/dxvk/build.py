# SPDX-License-Identifier: MIT
"""Configure/build the patched D3D9 renderer only; no game input or app signing."""
import argparse
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from upstream import external


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('platform', choices=['macos', 'iphoneos', 'iphonesimulator', 'android', 'win32'])
    ap.add_argument('--source', required=True, type=external, help='fresh tools/upstream.py dxvk checkout')
    ap.add_argument('--build', required=True, type=external, help='new external build directory')
    ap.add_argument('--ndk', type=Path, help='Android NDK root')
    ap.add_argument('--abi', choices=['arm64-v8a', 'x86_64'], default='arm64-v8a')
    ap.add_argument('--jobs', type=int, default=6)
    args = ap.parse_args()
    if args.build.exists():
        ap.error('choose a new build directory; reuse it with ninja -C afterward')
    if not (args.source / 'src/wsi/ios/wsi_platform_ios.cpp').is_file():
        ap.error('source must have the complete public patch series applied')
    options = ['-Denable_d3d8=false', '-Denable_d3d10=false', '-Denable_d3d11=false', '-Denable_dxgi=false',
               '-Dnative_sdl2=disabled', '-Dnative_sdl3=disabled', '-Dnative_glfw=disabled']
    cross = None
    if args.platform == 'macos':
        options[4] = '-Dnative_sdl2=enabled'
    elif args.platform in ('iphoneos', 'iphonesimulator'):
        sdk = subprocess.check_output(['xcrun', '--sdk', args.platform, '--show-sdk-path'], text=True).strip()
        target = 'arm64-apple-ios16.0' + ('-simulator' if args.platform == 'iphonesimulator' else '')
        flags = ['-target', target, '-isysroot', sdk]
        binaries = {name: subprocess.check_output(['xcrun', '--find', exe], text=True).strip()
                    for name, exe in [('c', 'clang'), ('cpp', 'clang++'), ('ar', 'ar'), ('strip', 'strip')]}
        cross = (binaries, 'darwin', 'aarch64', 'arm64', flags, flags)
        options += ['-Dnative_ios=true', '-Ddefault_library=static']
    elif args.platform == 'android':
        if not args.ndk:
            ap.error('--ndk is required for Android')
        host = {'Darwin': 'darwin-x86_64', 'Linux': 'linux-x86_64', 'Windows': 'windows-x86_64'}[platform.system()]
        suffix = '.exe' if platform.system() == 'Windows' else ''
        bindir = args.ndk.resolve() / 'toolchains/llvm/prebuilt' / host / 'bin'
        arm = args.abi == 'arm64-v8a'
        triple = 'aarch64-linux-android' if arm else 'x86_64-linux-android'
        binaries = {'c': [str(bindir / ('clang' + suffix)), '--target=' + triple + '29'],
                    'cpp': [str(bindir / ('clang++' + suffix)), '--target=' + triple + '29'],
                    'ar': str(bindir / ('llvm-ar' + suffix)), 'strip': str(bindir / ('llvm-strip' + suffix))}
        cross = (binaries, 'android', 'aarch64' if arm else 'x86_64', 'armv8' if arm else 'x86_64',
                 ['-fPIC'], ['-static-libstdc++', '-landroid', '-llog'])
        options += ['-Dnative_android=true']
    else:
        binaries = {key: shutil.which(exe) for key, exe in [('c', 'i686-w64-mingw32-gcc'),
                    ('cpp', 'i686-w64-mingw32-g++'), ('ar', 'i686-w64-mingw32-ar'),
                    ('strip', 'i686-w64-mingw32-strip'), ('windres', 'i686-w64-mingw32-windres')]}
        if not all(binaries.values()):
            ap.error('put the i686 MinGW compiler and binutils on PATH')
        cross = (binaries, 'windows', 'x86', 'x86', [], [])
    args.build.mkdir(parents=True)
    extra = []
    if cross:
        binaries, system, family, cpu, flags, links = cross
        text = '[binaries]\n' + ''.join(f'{k} = {v!r}\n' for k, v in binaries.items())
        text += f"[host_machine]\nsystem = {system!r}\ncpu_family = {family!r}\ncpu = {cpu!r}\nendian = 'little'\n"
        text += '[properties]\nneeds_exe_wrapper = true\n[built-in options]\n'
        text += ''.join(f'{k} = {v!r}\n' for k, v in [('c_args', flags), ('cpp_args', flags), ('c_link_args', links), ('cpp_link_args', links)])
        config = args.build / 'cross.ini'
        config.write_text(text)
        extra = ['--cross-file', str(config)]
    subprocess.run(['meson', 'setup', str(args.build), str(args.source), '--buildtype', 'release', *extra, *options], check=True)
    subprocess.run(['ninja', '-C', str(args.build), '-j', str(args.jobs)], check=True)


if __name__ == '__main__':
    main()
