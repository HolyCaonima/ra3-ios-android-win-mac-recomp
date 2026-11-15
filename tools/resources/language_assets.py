"""Small BIG/CSF helpers for local language-pack preparation.

RefPack decoder adapted from Ra3Source/tools/analysis/build_asset_type_table.py;
the reference tree remains read-only. Generated game-derived output stays local.
"""
import struct
from pathlib import Path


def unpack_refpack(src):
    if len(src) < 5 or (((src[0] << 8) | src[1]) & 0x3EFF) != 0x10FB:
        return src
    pos = 2
    width = 4 if src[0] & 0x80 else 3
    if src[0] & 1:
        pos += width
    expected = int.from_bytes(src[pos:pos+width], 'big')
    pos += width
    if expected > 32 * 1024 * 1024:
        raise ValueError('language member is too large')
    out = bytearray()
    while pos < len(src):
        c0 = src[pos]
        if c0 < 0x80:
            c1 = src[pos+1]; pos += 2
            plain, count = c0 & 3, ((c0 >> 2) & 7) + 3
            distance = ((c0 & 0x60) << 3) + c1 + 1
        elif c0 < 0xC0:
            c1, c2 = src[pos+1:pos+3]; pos += 3
            plain, count = (c1 >> 6) & 3, (c0 & 0x3F) + 4
            distance = ((c1 & 0x3F) << 8) + c2 + 1
        elif c0 < 0xE0:
            c1, c2, c3 = src[pos+1:pos+4]; pos += 4
            plain, count = c0 & 3, ((c0 & 0x0C) << 6) + c3 + 5
            distance = ((c0 & 0x10) << 12) + (c1 << 8) + c2 + 1
        elif c0 < 0xFC:
            pos += 1
            plain, count, distance = ((c0 & 0x1F) << 2) + 4, 0, 0
        else:
            pos += 1
            out.extend(src[pos:pos+(c0 & 3)])
            break
        if pos + plain > len(src): raise ValueError('truncated RefPack literal')
        out.extend(src[pos:pos+plain]); pos += plain
        if count and not 0 < distance <= len(out): raise ValueError('invalid RefPack distance')
        for _ in range(count): out.append(out[-distance])
        if len(out) > expected: raise ValueError('RefPack output overflow')
    if len(out) != expected: raise ValueError('RefPack output size mismatch')
    return bytes(out)


def read_big_member(path, name):
    with Path(path).open('rb') as f:
        h = f.read(16)
        if h[:4] not in (b'BIG4', b'BIGF'): raise ValueError(f'not a BIG: {path}')
        n, end = struct.unpack('>II', h[8:16])
        if end > 8 * 1024 * 1024 or n > 100000: raise ValueError('unreasonable BIG directory')
        directory = f.read(end - 16); p = 0
        for _ in range(n):
            offset, size = struct.unpack_from('>II', directory, p); p += 8
            z = directory.index(0, p)
            label = directory[p:z].decode('ascii').replace('\\', '/').lower(); p = z + 1
            if label == name.lower().replace('\\', '/'):
                if size > 32 * 1024 * 1024: raise ValueError('language member is too large')
                f.seek(offset); data = f.read(size)
                if len(data) != size: raise ValueError('truncated BIG member')
                return unpack_refpack(data)
    return None


def read_csf(data):
    magic, version, labels, strings, unused, language = struct.unpack_from('<4s5I', data)
    if magic != b' FSC' or version not in (2, 3) or labels > 100000: raise ValueError('invalid CSF header')
    p = 24; result = {}; count = 0
    for _ in range(labels):
        start = p
        tag, n, size = struct.unpack_from('<4sII', data, p); p += 12
        if tag != b' LBL' or n > 1000: raise ValueError('invalid CSF label')
        label = data[p:p+size].decode('ascii'); p += size
        value_start = p
        for _ in range(n):
            tag, size = struct.unpack_from('<4sI', data, p); p += 8
            if tag not in (b' RTS', b'WRTS'): raise ValueError('invalid CSF string')
            p += size * 2
            if tag == b'WRTS':
                size = struct.unpack_from('<I', data, p)[0]; p += 4 + size
            if p > len(data): raise ValueError('truncated CSF')
        key = label.lower()
        if key in result: raise ValueError('duplicate CSF label: ' + label)
        result[key] = (data[start:p], data[value_start:p], n)
        count += n
    if p != len(data) or strings != count: raise ValueError('CSF count/trailing data mismatch')
    return (version, unused, language), result


def write_csf(header, entries):
    version, unused, language = header
    return struct.pack('<4s5I', b' FSC', version, len(entries), sum(x[2] for x in entries.values()), unused, language) + b''.join(x[0] for x in entries.values())


def single_member_big(name, data):
    name = name.replace('/', '\\').encode('ascii') + b'\0'
    end = 16 + 8 + len(name)
    offset = (end + 63) & ~63
    # RA3 BIG4/BIGF use LE total size, with BE directory fields.
    return (b'BIGF' + struct.pack('<I', offset + len(data)) + struct.pack('>II', 1, end)
            + struct.pack('>II', offset, len(data)) + name + bytes(offset - end) + data)
