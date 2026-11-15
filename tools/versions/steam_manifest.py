"""Read the file hashes in a locally cached, plaintext Steam depot manifest.

Wire schema: ValvePython/steam, protobufs/content_manifest.proto.
This compares files with the supplied local manifest, not a remote signature
verification. It neither contacts Steam nor reads account credentials.
"""
import struct
from pathlib import Path


def fields(data):
    pos = 0

    def varint():
        nonlocal pos
        out = 0
        for shift in range(0, 70, 7):
            if pos >= len(data):
                raise ValueError('truncated protobuf varint')
            b = data[pos]
            pos += 1
            out |= (b & 127) << shift
            if not b & 128:
                return out
        raise ValueError('oversized protobuf varint')

    while pos < len(data):
        key = varint()
        kind = key & 7
        if kind == 0:
            value = varint()
        elif kind in (1, 2, 5):
            n = varint() if kind == 2 else 8 if kind == 1 else 4
            if n > len(data) - pos:
                raise ValueError('truncated protobuf field')
            value = data[pos:pos+n]
            if kind != 2:
                value = int.from_bytes(value, 'little')
            pos += n
        else:
            raise ValueError(f'unsupported wire type {kind}')
        yield key >> 3, value


def read_manifest(path):
    data = Path(path).read_bytes()
    magic, size = struct.unpack_from('<II', data)
    if magic != 0x71f617d0 or size > len(data) - 8:
        raise ValueError('not a Steam protobuf payload')
    meta_magic, meta_size = struct.unpack_from('<II', data, size + 8)
    if meta_magic != 0x1f4812be or meta_size > len(data) - size - 16:
        raise ValueError('missing manifest metadata')
    meta = dict(fields(data[size+16:size+16+meta_size]))
    if meta.get(4):
        raise ValueError('encrypted filenames are not supported')
    out = {}
    for tag, entry in fields(data[8:8+size]):
        if tag != 1:
            continue
        f = dict(fields(entry))
        name = f[1].decode('utf-8').replace('\\', '/')
        out[name.lower()] = {'name': name, 'size': f[2], 'sha1': f.get(5, b'').hex()}
    return out
