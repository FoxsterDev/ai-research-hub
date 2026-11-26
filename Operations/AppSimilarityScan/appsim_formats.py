"""Binary format readers used by the scanner: Mach-O sections, UnityFS bundles,
IL2CPP global-metadata, Apple CgBI PNGs. Standard library only."""

import struct
import zlib

CPU_ARM64 = 0x0100000C
MH_MAGIC_64 = 0xFEEDFACF
FAT_MAGICS = (0xCAFEBABE, 0xBEBAFECA)
LC_SEGMENT_64 = 0x19


def is_macho(head):
    if len(head) < 4:
        return False
    le = struct.unpack_from('<I', head, 0)[0]
    be = struct.unpack_from('>I', head, 0)[0]
    return le == MH_MAGIC_64 or be in FAT_MAGICS


def macho_sections(data):
    """Return {(segment, section): bytes} for the arm64 slice of a Mach-O image."""
    base = 0
    if struct.unpack_from('>I', data, 0)[0] in FAT_MAGICS:
        count = struct.unpack_from('>I', data, 4)[0]
        for i in range(count):
            cputype, _, offset, _, _ = struct.unpack_from('>iiIII', data, 8 + i * 20)
            if cputype == CPU_ARM64:
                base = offset
    if struct.unpack_from('<I', data, base)[0] != MH_MAGIC_64:
        return {}
    ncmds = struct.unpack_from('<I', data, base + 16)[0]
    offset = base + 32
    sections = {}
    for _ in range(ncmds):
        cmd, size = struct.unpack_from('<II', data, offset)
        if cmd == LC_SEGMENT_64:
            nsects = struct.unpack_from('<I', data, offset + 64)[0]
            s = offset + 72
            for _ in range(nsects):
                sect = data[s:s + 16].rstrip(b'\0').decode('ascii', 'replace')
                seg = data[s + 16:s + 32].rstrip(b'\0').decode('ascii', 'replace')
                _, size_, file_off = struct.unpack_from('<QQI', data, s + 32)
                flags = struct.unpack_from('<I', data, s + 64)[0]
                zerofill = (flags & 0xFF) in (0x01, 0x0C, 0x12)
                sections[(seg, sect)] = b'' if zerofill or not file_off else data[base + file_off:base + file_off + size_]
                s += 80
        offset += size
    return sections


def lz4_block_decompress(src):
    dst = bytearray()
    i, n = 0, len(src)
    while i < n:
        token = src[i]
        i += 1
        lit = token >> 4
        if lit == 15:
            while True:
                b = src[i]
                i += 1
                lit += b
                if b != 255:
                    break
        dst += src[i:i + lit]
        i += lit
        if i >= n:
            break
        off = src[i] | (src[i + 1] << 8)
        i += 2
        if off == 0:
            raise ValueError('lz4: zero offset')
        ml = token & 15
        if ml == 15:
            while True:
                b = src[i]
                i += 1
                ml += b
                if b != 255:
                    break
        ml += 4
        start = len(dst) - off
        if start < 0:
            raise ValueError('lz4: offset before start')
        if off >= ml:
            dst += dst[start:start + ml]
        else:
            for k in range(ml):
                dst.append(dst[start + k])
    return bytes(dst)


def _cstr(data, pos):
    end = data.index(b'\0', pos)
    return data[pos:end].decode('utf-8', 'replace'), end + 1


def _decompress(blob, kind):
    if kind == 0:
        return blob
    if kind in (2, 3):
        return lz4_block_decompress(blob)
    raise ValueError(f'UnityFS compression {kind} is not supported (LZMA bundles are rare on iOS)')


def unityfs_entries(data):
    """Yield (name, bytes) for each node of a UnityFS archive (uncompressed or LZ4/LZ4HC)."""
    if not data.startswith(b'UnityFS\0'):
        raise ValueError('not a UnityFS archive')
    p = 8
    version = struct.unpack_from('>I', data, p)[0]
    p += 4
    _, p = _cstr(data, p)
    _, p = _cstr(data, p)
    _, comp_size, uncomp_size, flags = struct.unpack_from('>qIII', data, p)
    p += 20
    if version >= 7:
        p = (p + 15) & ~15
    if flags & 0x80:
        info = data[len(data) - comp_size:]
    else:
        info = data[p:p + comp_size]
        p += comp_size
    info = _decompress(info, flags & 0x3F)
    q = 16
    block_count = struct.unpack_from('>i', info, q)[0]
    q += 4
    blocks = []
    for _ in range(block_count):
        u, c, f = struct.unpack_from('>IIH', info, q)
        q += 10
        blocks.append((u, c, f))
    node_count = struct.unpack_from('>i', info, q)[0]
    q += 4
    nodes = []
    for _ in range(node_count):
        off, size, _ = struct.unpack_from('>qqI', info, q)
        q += 20
        name, q = _cstr(info, q)
        nodes.append((off, size, name))
    if flags & 0x200:
        p = (p + 15) & ~15
    raw = bytearray()
    for _, c, f in blocks:
        raw += _decompress(data[p:p + c], f & 0x3F)
        p += c
    for off, size, name in nodes:
        yield name, bytes(raw[off:off + size])


def il2cpp_metadata(data):
    """Return (version, identifiers, literals) from global-metadata.dat (v24+ header layout)."""
    sanity, version = struct.unpack_from('<Ii', data, 0)
    if sanity != 0xFAB11BAF:
        raise ValueError('not an IL2CPP global-metadata file')
    lit_off, lit_size, lit_data_off, _, str_off, str_size = struct.unpack_from('<6I', data, 8)
    identifiers = set()
    for part in data[str_off:str_off + str_size].split(b'\0'):
        if part:
            try:
                identifiers.add(part.decode('utf-8'))
            except UnicodeDecodeError:
                pass
    literals = set()
    for i in range(lit_size // 8):
        length, index = struct.unpack_from('<Ii', data, lit_off + i * 8)
        chunk = data[lit_data_off + index:lit_data_off + index + length]
        try:
            literals.add(chunk.decode('utf-8'))
        except UnicodeDecodeError:
            pass
    return version, identifiers, literals


_META_SECTIONS = ['string_literal', 'string_literal_data', 'string', 'events', 'properties', 'methods',
                  'parameter_default_values', 'field_default_values', 'field_param_default_data',
                  'field_marshaled_sizes', 'parameters', 'fields', 'generic_parameters',
                  'generic_parameter_constraints', 'generic_containers', 'nested_types', 'interfaces',
                  'vtable_methods', 'interface_offsets', 'type_definitions', 'images', 'assemblies']


def il2cpp_ownership(data):
    """Map every identifier in global-metadata (v29+) to the assembly images that
    declare it: type names, namespaces, methods, parameters, fields, properties,
    events and generic parameters. Returns {identifier: set(image names)}."""
    sanity, version = struct.unpack_from('<Ii', data, 0)
    if sanity != 0xFAB11BAF or version < 29:
        raise ValueError(f'unsupported metadata version {version}')
    sec = {name: struct.unpack_from('<II', data, 8 + i * 8) for i, name in enumerate(_META_SECTIONS)}
    str_off = sec['string'][0]

    def name_at(index):
        start = str_off + index
        end = data.index(b'\0', start)
        return data[start:end].decode('utf-8', 'replace')

    img_off, img_size = sec['images']
    images = []
    for i in range(img_size // 40):
        name_idx, _, type_start, type_count = struct.unpack_from('<iiiI', data, img_off + i * 40)
        images.append((name_at(name_idx), type_start, type_count))
    total_types = sum(c for _, _, c in images)
    td_off, td_size = sec['type_definitions']
    type_size = td_size // total_types if total_types else 0
    if type_size not in (84, 88):
        raise ValueError(f'unexpected type definition size {type_size}')
    shift = type_size - 84
    m_off, m_size = sec['methods']
    p_off = sec['parameters'][0]
    f_off = sec['fields'][0]
    pr_off = sec['properties'][0]
    e_off = sec['events'][0]
    types = []
    total_methods = 0
    for t in range(total_types):
        base = td_off + t * type_size
        name_idx, ns_idx = struct.unpack_from('<ii', data, base)
        field_start, method_start, event_start, prop_start = struct.unpack_from('<iiii', data, base + 28 + shift)
        method_count, prop_count, field_count, event_count = struct.unpack_from('<HHHH', data, base + 60 + shift)
        types.append((name_idx, ns_idx, field_start, method_start, event_start, prop_start,
                      method_count, prop_count, field_count, event_count))
        total_methods = max(total_methods, method_start + method_count if method_start >= 0 else 0)
    method_size = m_size // total_methods if total_methods else 0
    if method_size not in (32, 36):
        raise ValueError(f'unexpected method definition size {method_size}')
    param_start_at, param_count_at = (16, 34) if method_size == 36 else (12, 30)
    owners = {}

    def own(index, image):
        if index is None or index < 0:
            return
        owners.setdefault(name_at(index), set()).add(image)

    type_image = [None] * total_types
    for image, type_start, type_count in images:
        for t in range(type_start, type_start + type_count):
            type_image[t] = image
            (name_idx, ns_idx, field_start, method_start, event_start, prop_start,
             method_count, prop_count, field_count, event_count) = types[t]
            own(name_idx, image)
            if ns_idx >= 0 and name_at(ns_idx):
                own(ns_idx, image)
            for m in range(method_start, method_start + method_count) if method_start >= 0 else ():
                mb = m_off + m * method_size
                own(struct.unpack_from('<i', data, mb)[0], image)
                pstart = struct.unpack_from('<i', data, mb + param_start_at)[0]
                pcount = struct.unpack_from('<H', data, mb + param_count_at)[0]
                for p in range(pstart, pstart + pcount) if pstart >= 0 else ():
                    own(struct.unpack_from('<i', data, p_off + p * 12)[0], image)
            for f in range(field_start, field_start + field_count) if field_start >= 0 else ():
                own(struct.unpack_from('<i', data, f_off + f * 12)[0], image)
            for p in range(prop_start, prop_start + prop_count) if prop_start >= 0 else ():
                own(struct.unpack_from('<i', data, pr_off + p * 20)[0], image)
            for e in range(event_start, event_start + event_count) if event_start >= 0 else ():
                own(struct.unpack_from('<i', data, e_off + e * 24)[0], image)
    gc_off, gc_size = sec['generic_containers']
    gp_off, gp_size = sec['generic_parameters']
    for g in range(gp_size // 16):
        owner_idx, name_idx = struct.unpack_from('<ii', data, gp_off + g * 16)
        if not 0 <= owner_idx < gc_size // 16:
            continue
        c_owner, _, is_method = struct.unpack_from('<iii', data, gc_off + owner_idx * 16)
        if is_method:
            if 0 <= c_owner < total_methods:
                declaring = struct.unpack_from('<i', data, m_off + c_owner * method_size + 4)[0]
                image = type_image[declaring] if 0 <= declaring < total_types else None
            else:
                image = None
        else:
            image = type_image[c_owner] if 0 <= c_owner < total_types else None
        if image:
            own(name_idx, image)
    return owners


def _png_chunks(data):
    p = 8
    while p + 8 <= len(data):
        length, ctype = struct.unpack_from('>I4s', data, p)
        yield ctype, data[p + 8:p + 8 + length]
        p += 12 + length


def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def png_gray(data):
    """Decode an 8-bit PNG (standard or Apple CgBI) to (width, height, gray rows)."""
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('not a PNG')
    cgbi = False
    idat = bytearray()
    width = height = depth = ctype = None
    for kind, body in _png_chunks(data):
        if kind == b'CgBI':
            cgbi = True
        elif kind == b'IHDR':
            width, height, depth, ctype = struct.unpack_from('>IIBB', body, 0)
            interlace = body[12]
            if interlace:
                raise ValueError('interlaced PNG not supported')
        elif kind == b'IDAT':
            idat += body
    if depth != 8 or ctype not in (0, 2, 4, 6):
        raise ValueError('only 8-bit gray/RGB/RGBA PNG supported')
    channels = {0: 1, 2: 3, 4: 2, 6: 4}[ctype]
    raw = zlib.decompress(bytes(idat), -15 if cgbi else 15)
    stride = width * channels
    prev = bytearray(stride)
    rows = []
    p = 0
    for _ in range(height):
        f = raw[p]
        line = bytearray(raw[p + 1:p + 1 + stride])
        p += 1 + stride
        for i in range(stride):
            left = line[i - channels] if i >= channels else 0
            up = prev[i]
            ul = prev[i - channels] if i >= channels else 0
            if f == 1:
                line[i] = (line[i] + left) & 255
            elif f == 2:
                line[i] = (line[i] + up) & 255
            elif f == 3:
                line[i] = (line[i] + ((left + up) >> 1)) & 255
            elif f == 4:
                line[i] = (line[i] + _paeth(left, up, ul)) & 255
        prev = line
        if channels == 1 or channels == 2:
            rows.append([line[i * channels] for i in range(width)])
        else:
            if cgbi:
                rows.append([(line[i * channels + 2] * 299 + line[i * channels + 1] * 587 + line[i * channels] * 114) // 1000 for i in range(width)])
            else:
                rows.append([(line[i * channels] * 299 + line[i * channels + 1] * 587 + line[i * channels + 2] * 114) // 1000 for i in range(width)])
    return width, height, rows


def dhash(width, height, rows, size=8):
    """Difference hash on a box-downsampled (size+1)x(size) gray image."""
    w2, h2 = size + 1, size
    cells = []
    for y in range(h2):
        y0, y1 = y * height // h2, max(y * height // h2 + 1, (y + 1) * height // h2)
        row = []
        for x in range(w2):
            x0, x1 = x * width // w2, max(x * width // w2 + 1, (x + 1) * width // w2)
            total = cnt = 0
            for yy in range(y0, y1):
                r = rows[yy]
                for xx in range(x0, x1):
                    total += r[xx]
                    cnt += 1
            row.append(total / cnt)
        cells.append(row)
    bits = 0
    for y in range(h2):
        for x in range(size):
            bits = (bits << 1) | (1 if cells[y][x] > cells[y][x + 1] else 0)
    return bits
