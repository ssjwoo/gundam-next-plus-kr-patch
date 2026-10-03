#!/usr/bin/env python3
"""Read source PMF2 texture selectors and vertex spans without changing assets.

The supported vertex layouts are defined by PSPSDK's pspgu.h:
https://github.com/pspdev/pspsdk/blob/master/src/gu/pspgu.h
UV and XYZ values are source geometry, not proof of runtime screen placement.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from repack_pzz import parse
from unpack_pzz import xor_words, detect_xor_key
from inspect_gim import parse_chunk, gather, image_info

LAYOUTS = {0x102: (10, 4), 0x11A: (12, 6), 0x142: (16, 10)}


def decode(path):
    path = Path(path)
    raw = path.read_bytes()
    parts, _ = parse(xor_words(raw, detect_xor_key(raw)))
    rows, unknown = [], []
    for part in parts:
        mesh = part['payload']
        if mesh[:4] != b'PMF2':
            continue
        picture_part = part['index'] + 1
        gim = parts[picture_part]['payload']
        dimensions = []
        for picture in gather(parse_chunk(gim, 16), 3):
            images = [c for c in picture.children if c.type == 4]
            assert len(images) == 1
            info = image_info(gim, images[0])
            dimensions.append([info['width'], info['height']])
        count = struct.unpack_from('<I', mesh, 4)[0]
        offsets = list(struct.unpack_from(f'<{count}I', mesh, 32))
        for obj, off in enumerate(offsets):
            name = mesh[off + 0x60:off + 0x74].split(b'\0')[0].decode()
            pic = struct.unpack_from('<I', mesh, off + 0x74)[0]
            origin = off + 0x100
            limit = min([len(mesh), *[p for p in offsets if p > off]])
            vtype = base = None
            cursor = primitive = 0
            for pos in range(origin, min(limit, origin + 0x100), 4):
                word = struct.unpack_from('<I', mesh, pos)[0]
                cmd, argument = word >> 24, word & 0xFFFFFF
                if cmd == 1:
                    base, cursor = origin + argument, 0
                elif cmd == 18:
                    vtype = argument
                elif cmd == 4:
                    n, mode = argument & 65535, argument >> 16
                    if vtype not in LAYOUTS or mode not in (3, 4, 5) or pic >= len(dimensions):
                        unknown.append({'object': name, 'vtype': vtype, 'mode': mode,
                                        'picture': pic, 'primitive_index': primitive})
                        cursor += n
                        primitive += 1
                        continue
                    stride, xyz_offset = LAYOUTS[vtype]
                    assert base is not None and base >= origin
                    width, height = dimensions[pic]
                    vertices = []
                    for i in range(cursor, cursor + n):
                        address = base + i * stride
                        assert address + stride <= limit
                        u, v = struct.unpack_from('<HH', mesh, address)
                        xyz = struct.unpack_from('<hhh', mesh, address + xyz_offset)
                        color = struct.unpack_from('<H', mesh, address + 4)[0] if vtype == 0x11A else 65535
                        vertex = {'uv': [u / 32768 * width, v / 32768 * height],
                                  'xyz': xyz, 'color': [(color >> (4 * k) & 15) / 15 for k in range(4)]}
                        if vtype == 0x142:
                            vertex['normal_s16'] = struct.unpack_from('<hhh', mesh, address + 4)
                        vertices.append(vertex)
                    triangles = ([(i, i + 1, i + 2) for i in range(n - 2)] if mode == 4 else
                                 [(i, i + 1, i + 2) for i in range(0, n, 3)] if mode == 3 else
                                 [(0, i, i + 1) for i in range(1, n - 1)])
                    assert all(max(t) < n for t in triangles)
                    rows.append({'asset': path.name, 'part': picture_part, 'mesh_part': part['index'],
                                 'object': obj, 'object_name': name, 'primitive_index': primitive,
                                 'picture': pic, 'dimensions': dimensions[pic], 'vtype': vtype,
                                 'mode': mode, 'vertices': vertices, 'triangles': triangles,
                                 'mesh_sha256': hashlib.sha256(mesh).hexdigest(),
                                 'source_pzz_sha256': hashlib.sha256(raw).hexdigest()})
                    cursor += n
                    primitive += 1
                elif cmd == 11:
                    break
    return rows, unknown


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a fresh report filename')
    rows, unknown = decode(args.source)
    report = {'records': rows, 'unsupported': unknown, 'runtime_verdict': 'NOT_TESTED',
              'mode_reachability_proven': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'primitives': len(rows), 'unsupported': len(unknown)}))


if __name__ == '__main__':
    main()
