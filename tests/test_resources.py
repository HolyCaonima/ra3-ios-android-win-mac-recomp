# SPDX-License-Identifier: MIT
from pathlib import Path
import struct
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tools/resources'), str(ROOT/'tools/versions')]
from language_assets import read_big_member, single_member_big, unpack_refpack, read_csf, write_csf
from skudef import contained, flatten
from steam_manifest import fields, read_manifest


class ResourceTests(unittest.TestCase):
    def test_big_and_refpack_synthetic_roundtrip(self):
        # Literal-only RefPack stream constructed here, not sampled from a game.
        packed = bytes([16, 251, 0, 0, 4, 224]) + b'TEST' + bytes([252])
        self.assertEqual(unpack_refpack(packed), b'TEST')
        with tempfile.TemporaryDirectory() as d:
            archive = Path(d)/'synthetic.big'
            archive.write_bytes(single_member_big('Example/Text', packed))
            self.assertEqual(read_big_member(archive, 'example\\text'), b'TEST')
            self.assertIsNone(read_big_member(archive, 'absent'))
        with self.assertRaises(ValueError):
            unpack_refpack(bytes([16, 251, 0, 0, 3, 0, 0]))
        with self.assertRaises(ValueError):
            unpack_refpack(packed[:-2])

    def test_csf_synthetic_text_roundtrip_and_rejection(self):
        label = b'EXAMPLE'
        text = bytes(b ^ 255 for b in '合成 text'.encode('utf-16-le'))
        value = struct.pack('<4sI', b' RTS', len(text)//2) + text
        row = struct.pack('<4sII', b' LBL', 1, len(label)) + label + value
        encoded = write_csf((3, 0, 0), {'example': (row, value, 1)})
        header, entries = read_csf(encoded)
        self.assertEqual(write_csf(header, entries), encoded)
        with self.assertRaises(ValueError):
            read_csf(encoded[:-1])
        with self.assertRaises(ValueError):
            read_csf(encoded+b'!')

    def test_skudef_cycles_and_escape(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'one.big').write_bytes(b'synthetic')
            (root/'main.skudef').write_text('add-config child.skudef\nset-exe ignored.exe\n')
            (root/'child.skudef').write_text('add-big one.big\n')
            rows = flatten(root, 'main.skudef')
            self.assertEqual(len(rows), 1)
            self.assertTrue(rows[0].endswith('/one.big'))
            with self.assertRaises(ValueError):
                contained(root, '../outside')
            (root/'child.skudef').write_text('add-config main.skudef\n')
            with self.assertRaises(ValueError):
                flatten(root, 'main.skudef')

    def test_local_manifest_synthetic_and_encryption_rejected(self):
        def blob(tag, data):
            return bytes([tag*8+2, len(data)]) + data
        entry = blob(1, b'example.txt') + bytes([16, 4]) + blob(5, bytes(range(20)))
        payload = blob(1, entry)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'manifest'
            def write(meta):
                path.write_bytes(struct.pack('<II', 0x71f617d0, len(payload)) + payload + struct.pack('<II', 0x1f4812be, len(meta)) + meta)
            write(bytes([32, 0]))
            self.assertEqual(read_manifest(path)['example.txt']['size'], 4)
            write(bytes([32, 1]))
            with self.assertRaises(ValueError):
                read_manifest(path)
        for data in (bytes([128]), bytes([10, 20, 1]), bytes([15])):
            with self.assertRaises(ValueError):
                list(fields(data))
