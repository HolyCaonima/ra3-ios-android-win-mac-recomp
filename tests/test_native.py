# SPDX-License-Identifier: MIT
import ctypes
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name == 'posix' and shutil.which('cc'), 'requires POSIX and a C compiler')
class NativeTests(unittest.TestCase):
    def compile_run(self, sources, flags=()):
        with tempfile.TemporaryDirectory(prefix='ra3-public-native-') as d:
            binary = Path(d) / 'check'
            subprocess.run(['cc', '-std=c11', '-D_DEFAULT_SOURCE', '-Wall', '-Wextra', *flags,
                            *[str(ROOT / x) for x in sources], '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True, timeout=15)

    def test_cursor_pixels_and_animation(self):
        self.compile_run(['tools/macos/test_cursors.c', 'hosts/macos/cursor_image.c'],
                         ['-fsanitize=address,undefined', '-fno-omit-frame-pointer'])

    def test_udp_transport_loopback_only(self):
        self.compile_run(['tools/net/test_lan_discovery.c'], ['-pthread'])

    def test_windows_path_semantics(self):
        with tempfile.TemporaryDirectory(prefix='ra3-public-path-') as d:
            source, library = Path(d) / 'wrapper.c', Path(d) / 'paths.so'
            source.write_text('#include "path_combine.h"\nint combine(uint16_t*d,const uint16_t*a,const uint16_t*b){return ra3_path_combine_w(d,a,b);}\n')
            subprocess.run(['cc', '-shared', '-fPIC', '-I', str(ROOT / 'runtime/hle'), str(source), '-o', str(library)], check=True)
            fn = ctypes.CDLL(str(library)).combine
            unit = ctypes.c_uint16
            fn.argtypes = [ctypes.POINTER(unit)] * 3
            def utf16(value):
                if value is None:
                    return None
                data = value.encode('utf-16-le') + bytes(2)
                return (unit * (len(data)//2)).from_buffer_copy(data)
            cases = [('', '', '\\'), ('C:\\a', 'b', 'C:\\a\\b'),
                     ('C:\\a', '..\\b', 'C:\\b'), ('C:\\a', '\\b', 'C:\\b'),
                     ('C:\\a', 'D:\\b', 'D:\\b'),
                     ('\\\\server\\share\\folder', '\\b', '\\\\server\\share\\b'),
                     ('C:\\目录', '文档', 'C:\\目录\\文档')]
            for a, b, expected in cases:
                out = (unit * 260)()
                self.assertEqual(fn(out, utf16(a), utf16(b)), 1)
                value = bytes(out).decode('utf-16-le').split('\0')[0]
                self.assertEqual(value, expected)
            out = (unit * 260)()
            self.assertEqual(fn(out, None, None), 0)
            self.assertEqual(fn(out, utf16('C:\\'), utf16('a'*257)), 0)
            self.assertEqual(out[0], 0)

    @unittest.skipUnless(sys.platform == 'darwin', 'Apple SDK required')
    def test_apple_discovery_compiles(self):
        with tempfile.TemporaryDirectory(prefix='ra3-public-apple-') as d:
            subprocess.run(['cc', '-fblocks', '-DDNS_SD_LIBDISPATCH=1', '-I', str(ROOT/'runtime/hle'),
                            '-c', str(ROOT/'hosts/apple/bonjour.c'), '-o', str(Path(d)/'bonjour.o')], check=True)
