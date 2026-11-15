"""List a PE's imports, grouped by DLL (names, or #ordinals)."""
import struct
import sys


def imports(path):
    d = open(path, 'rb').read()
    nt = struct.unpack_from('<I', d, 0x3C)[0]
    opt = nt + 0x18
    nsec, = struct.unpack_from('<H', d, nt + 6)
    secs = []
    so = opt + struct.unpack_from('<H', d, nt + 0x14)[0]
    for i in range(nsec):
        vs, va, rawsz, raw = struct.unpack_from('<IIII', d, so + i * 40 + 8)
        secs.append((va, max(vs, rawsz), raw))

    def off(rva):
        for va, sz, raw in secs:
            if va <= rva < va + sz:
                return rva - va + raw
        raise ValueError(hex(rva))

    def cstr(rva):
        o = off(rva)
        return d[o:d.index(b'\0', o)].decode('latin1')

    imp_rva, _ = struct.unpack_from('<II', d, opt + 0x60 + 8)
    out = {}
    o = off(imp_rva)
    while True:
        oft, _, _, name, ft = struct.unpack_from('<IIIII', d, o)
        if not name:
            break
        dll = cstr(name)
        t = off(oft or ft)
        while True:
            e, = struct.unpack_from('<I', d, t)
            if not e:
                break
            out.setdefault(dll, []).append(f"#{e & 0xFFFF}" if e & 0x80000000 else cstr(e + 2))
            t += 4
        o += 20
    return out


if __name__ == '__main__':
    for dll, names in imports(sys.argv[1]).items():
        print(f"{dll} ({len(names)}): {' '.join(names)}")
