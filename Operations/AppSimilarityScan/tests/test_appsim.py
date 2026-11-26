"""Offline tests for App Similarity Scan on synthetic fixtures.

Run: python3 -m unittest discover -s tests   (from the module directory)
"""

import json
import os
import plistlib
import random
import struct
import sys
import tempfile
import unittest
import zipfile
import zlib
from pathlib import Path

MODULE_DIR = Path(__file__).parents[1]
sys.path.insert(0, str(MODULE_DIR))

import appsim  # noqa: E402
import appsim_formats as fmt  # noqa: E402


def make_macho(sections):
    """Minimal arm64 MH_EXECUTE with one LC_SEGMENT_64 per segment name."""
    by_seg = {}
    for (seg, sect), data in sections.items():
        by_seg.setdefault(seg, []).append((sect, data))
    cmds = []
    payload = bytearray()
    header_size = 32
    cmd_sizes = [72 + 80 * len(v) for v in by_seg.values()]
    data_off = header_size + sum(cmd_sizes)
    for seg, items in by_seg.items():
        cmd = bytearray(struct.pack('<II16sQQQQiiII', 0x19, 72 + 80 * len(items), seg.encode(), 0, 0, 0, 0, 7, 5, len(items), 0))
        for sect, data in items:
            off = data_off + len(payload)
            cmd += struct.pack('<16s16sQQIIIIIIII', sect.encode(), seg.encode(), 0, len(data), off, 2, 0, 0, 0, 0, 0, 0)
            payload += data
        cmds.append(bytes(cmd))
    header = struct.pack('<IiiIIIII', 0xFEEDFACF, 0x0100000C, 0, 2, len(cmds), sum(cmd_sizes), 0, 0)
    return header + b''.join(cmds) + bytes(payload)


def make_unityfs(entries):
    raw = b''.join(data for _, data in entries)
    info = bytearray(16)
    info += struct.pack('>i', 1) + struct.pack('>IIH', len(raw), len(raw), 0)
    info += struct.pack('>i', len(entries))
    off = 0
    for name, data in entries:
        info += struct.pack('>qqI', off, len(data), 4) + name.encode() + b'\0'
        off += len(data)
    head = b'UnityFS\0' + struct.pack('>I', 6) + b'5.x.x\0' + b'2020.1\0'
    head += struct.pack('>qIII', 0, len(info), len(info), 0)
    return head + bytes(info) + raw


def make_metadata(identifiers, literals):
    strings = b''.join(s.encode() + b'\0' for s in identifiers)
    lit_data = b''.join(s.encode() for s in literals)
    lit_table = bytearray()
    pos = 0
    for s in literals:
        lit_table += struct.pack('<Ii', len(s.encode()), pos)
        pos += len(s.encode())
    header_size = 8 + 6 * 4
    lit_off = header_size
    lit_data_off = lit_off + len(lit_table)
    str_off = lit_data_off + len(lit_data)
    header = struct.pack('<Ii', 0xFAB11BAF, 31) + struct.pack('<6I', lit_off, len(lit_table), lit_data_off, len(lit_data), str_off, len(strings))
    return header + bytes(lit_table) + lit_data + strings


def make_png(width, height, pixel, cgbi=False):
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            r, g, b, a = pixel(x, y)
            rows += bytes((b, g, r, a) if cgbi else (r, g, b, a))
    if cgbi:
        comp = zlib.compressobj(9, zlib.DEFLATED, -15)
        idat = comp.compress(bytes(rows)) + comp.flush()
    else:
        idat = zlib.compress(bytes(rows))

    def chunk(kind, body):
        return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body))
    out = b'\x89PNG\r\n\x1a\n'
    if cgbi:
        out += chunk(b'CgBI', b'\x50\x00\x20\x02')
    out += chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
    out += chunk(b'IDAT', idat) + chunk(b'IEND', b'')
    return out


def rand_code(seed, words):
    rnd = random.Random(seed)
    out = []
    for _ in range(words):
        kind = rnd.random()
        if kind < 0.2:
            out.append(0x94000000 | rnd.getrandbits(26))
        elif kind < 0.3:
            out.append(0x90000000 | (rnd.getrandbits(2) << 29) | (rnd.getrandbits(19) << 5) | rnd.getrandbits(5))
        else:
            out.append(0xAA0003E0 | rnd.getrandbits(5) | (rnd.getrandbits(5) << 16))
    return out


def relink(words, seed):
    """Same instructions, different branch targets and ADRP pages."""
    rnd = random.Random(seed)
    out = []
    for w in words:
        if (w & 0xFC000000) == 0x94000000:
            out.append(0x94000000 | rnd.getrandbits(26))
        elif (w & 0x9F000000) == 0x90000000:
            out.append((w & 0x9F00001F) | (rnd.getrandbits(2) << 29) | (rnd.getrandbits(19) << 5))
        else:
            out.append(w)
    return out


def pack(words):
    return struct.pack(f'<{len(words)}I', *words)


def make_app(root, name, bundle_id, code_words, assets, identifiers, literals, classes, frameworks, icon_pixel, extra_plist=None):
    app = Path(root) / f'{name}.app'
    (app / 'Data' / 'Managed' / 'Metadata').mkdir(parents=True)
    info = {'CFBundleIdentifier': bundle_id, 'CFBundleExecutable': name, 'CFBundleShortVersionString': '1.0',
            'CFBundleVersion': '1', 'NSUserTrackingUsageDescription': 'We use data for ads.'}
    info.update(extra_plist or {})
    (app / 'Info.plist').write_bytes(plistlib.dumps(info))
    classnames = b''.join(c.encode() + b'\0' for c in classes)
    (app / name).write_bytes(make_macho({('__TEXT', '__text'): pack(code_words), ('__TEXT', '__objc_classname'): classnames}))
    (app / 'Data' / 'data.unity3d').write_bytes(make_unityfs(assets))
    (app / 'Data' / 'Managed' / 'Metadata' / 'global-metadata.dat').write_bytes(make_metadata(identifiers, literals))
    for fw in frameworks:
        d = app / 'Frameworks' / f'{fw}.framework'
        d.mkdir(parents=True)
        (d / fw).write_bytes(make_macho({('__TEXT', '__text'): pack(rand_code(hash(fw) & 0xFFFF, 6000))}))
    (app / 'AppIcon60x60@2x.png').write_bytes(make_png(24, 24, icon_pixel, cgbi=True))
    return app


def noise(seed, n):
    rnd = random.Random(seed)
    return bytes(rnd.getrandbits(8) for _ in range(n))


class FormatTests(unittest.TestCase):
    def test_macho_sections_roundtrip(self):
        blob = make_macho({('__TEXT', '__text'): b'\x01\x02\x03\x04', ('__TEXT', '__cstring'): b'hello\0'})
        secs = fmt.macho_sections(blob)
        self.assertEqual(secs[('__TEXT', '__text')], b'\x01\x02\x03\x04')
        self.assertEqual(secs[('__TEXT', '__cstring')], b'hello\0')
        self.assertTrue(fmt.is_macho(blob[:4]))

    def test_lz4_literals_and_overlapping_match(self):
        self.assertEqual(fmt.lz4_block_decompress(bytes([0x30]) + b'abc'), b'abc')
        copy = bytes([0x30]) + b'abc' + bytes([0x03, 0x00]) + bytes([0x10]) + b'z'
        self.assertEqual(fmt.lz4_block_decompress(copy), b'abcabcaz')
        overlap = bytes([0x15]) + b'a' + bytes([0x01, 0x00]) + bytes([0x10]) + b'!'
        self.assertEqual(fmt.lz4_block_decompress(overlap), b'a' * 10 + b'!')

    def test_unityfs_uncompressed(self):
        entries = [('CAB-1', b'first'), ('CAB-2', b'second payload')]
        self.assertEqual(list(fmt.unityfs_entries(make_unityfs(entries))), entries)

    def test_il2cpp_metadata(self):
        version, ids, lits = fmt.il2cpp_metadata(make_metadata(['Game.Core', 'Player', 'Game.dll'], ['Hello', 'Wörld']))
        self.assertEqual(version, 31)
        self.assertEqual(ids, {'Game.Core', 'Player', 'Game.dll'})
        self.assertEqual(lits, {'Hello', 'Wörld'})

    def test_cgbi_and_standard_png_hash_equal(self):
        def px(x, y):
            v = 255 if x > y else 0
            return (v, v // 2, 255 - v, 255)
        a = fmt.png_gray(make_png(20, 20, px, cgbi=True))
        b = fmt.png_gray(make_png(20, 20, px, cgbi=False))
        self.assertEqual(fmt.dhash(*a), fmt.dhash(*b))


def make_full_metadata(assemblies):
    """v31 metadata with images, types, methods, params, fields, properties, events.
    assemblies: [(image_name, [(namespace, type, [(method, [params])], [fields], [props], [events])])]"""
    strings = bytearray()
    index = {}

    def s(text):
        if text not in index:
            index[text] = len(strings)
            strings.extend(text.encode() + b'\0')
        return index[text]
    images, typedefs, methods, params, fields, props, events = (bytearray() for _ in range(7))
    t_count = m_count = p_count = f_count = pr_count = e_count = 0
    for image, types in assemblies:
        images += struct.pack('<iiiIiIiIiI', s(image), 0, t_count, len(types), 0, 0, -1, 0, 0, 0)
        for ns, name, meths, flds, prs, evs in types:
            typedefs += struct.pack('<15i', s(name), s(ns), 0, -1, -1, -1, 0, f_count, m_count, e_count, pr_count, 0, 0, 0, 0)
            typedefs += struct.pack('<8H', len(meths), len(prs), len(flds), len(evs), 0, 0, 0, 0) + struct.pack('<II', 0, 0)
            for mname, pnames in meths:
                methods += struct.pack('<7i4H', s(mname), t_count, 0, 0, p_count, -1, 0, 0, 0, 0, len(pnames))
                for pn in pnames:
                    params += struct.pack('<iii', s(pn), 0, 0)
                    p_count += 1
                m_count += 1
            for fn in flds:
                fields += struct.pack('<iii', s(fn), 0, 0)
                f_count += 1
            for pn in prs:
                props += struct.pack('<5i', s(pn), -1, -1, 0, 0)
                pr_count += 1
            for en in evs:
                events += struct.pack('<6i', s(en), 0, -1, -1, -1, 0)
                e_count += 1
            t_count += 1
    sections = {'string': bytes(strings), 'events': bytes(events), 'properties': bytes(props), 'methods': bytes(methods),
                'parameters': bytes(params), 'fields': bytes(fields), 'type_definitions': bytes(typedefs),
                'images': bytes(images), 'assemblies': bytes(64 * len(assemblies))}
    header_size = 8 + len(fmt._META_SECTIONS) * 8
    body = bytearray()
    table = []
    for name in fmt._META_SECTIONS:
        blob = sections.get(name, b'')
        table.append((header_size + len(body), len(blob)))
        body += blob
    header = struct.pack('<Ii', 0xFAB11BAF, 31) + b''.join(struct.pack('<II', o, n) for o, n in table)
    return header + bytes(body)


class OwnershipTests(unittest.TestCase):
    def test_identifiers_map_to_declaring_assembly(self):
        data = make_full_metadata([
            ('Studio.Core.dll', [('Studio.Core', 'Wallet', [('Withdraw', ['amount'])], ['balance'], ['Balance'], ['Changed'])]),
            ('ThirdParty.dll', [('Vendor.Ads', 'AdView', [('Show', ['placement']), ('Withdraw', [])], [], [], [])]),
        ])
        owners = fmt.il2cpp_ownership(data)
        self.assertEqual(owners['Wallet'], {'Studio.Core.dll'})
        self.assertEqual(owners['amount'], {'Studio.Core.dll'})
        self.assertEqual(owners['balance'], {'Studio.Core.dll'})
        self.assertEqual(owners['Changed'], {'Studio.Core.dll'})
        self.assertEqual(owners['placement'], {'ThirdParty.dll'})
        self.assertEqual(owners['Withdraw'], {'Studio.Core.dll', 'ThirdParty.dll'})

    def test_owner_breakdown_groups(self):
        q_meta = make_full_metadata([
            ('Studio.Core.dll', [('Studio.Core', 'Wallet', [('Withdraw', ['amount'])], ['balance'], [], [])]),
            ('UnityEngine.CoreModule.dll', [('UnityEngine', 'GameObject', [('SetActive', ['value'])], [], [], [])]),
            ('Vendor.Ads.dll', [('Vendor.Ads', 'AdView', [('Show', [])], [], [], [])]),
            ('Game.dll', [('Game', 'Level', [('Win', [])], [], [], [])]),
        ])
        p_meta = make_full_metadata([
            ('Studio.Core.dll', [('Studio.Core', 'Wallet', [('Withdraw', ['amount'])], ['balance'], [], [])]),
            ('UnityEngine.CoreModule.dll', [('UnityEngine', 'GameObject', [('SetActive', ['value'])], [], [], [])]),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            docs = []
            for name, meta in (('q', q_meta), ('p', p_meta)):
                app = Path(tmp) / f'{name}.app' / 'Data' / 'Managed' / 'Metadata'
                app.mkdir(parents=True)
                (app / 'global-metadata.dat').write_bytes(meta)
                (Path(tmp) / f'{name}.app' / 'Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier': name}))
                out = Path(tmp) / f'{name}.json'
                appsim.save_index(appsim.build_index(str(Path(tmp) / f'{name}.app')), str(out), name)
                docs.append(appsim.load_index(str(out)))
            ob = appsim.owner_breakdown(docs[0], docs[1], [('studio', r'^Studio\.')], rest='third-party')
            by_name = appsim.owner_breakdown(docs[0], docs[1], [('studio', r'^Studio\.')])
        rows = {name: (shared, total) for name, shared, total in ob['rows']}
        self.assertEqual(rows['studio'][0], rows['studio'][1])
        self.assertEqual(rows['engine/.NET'][0], rows['engine/.NET'][1])
        self.assertEqual(rows['third-party'], (0, 8))
        named = {name: (shared, total) for name, shared, total in by_name['rows']}
        self.assertEqual(named['Game'][0], 0)
        self.assertEqual(named['Vendor.Ads'][0], 0)


class MaskingTests(unittest.TestCase):
    def test_relinked_code_matches_only_after_masking(self):
        words = rand_code(1, 20000)
        moved = relink(words, 2)
        a = {h for h, _ in appsim.code_chunks(pack(words))}
        b = {h for h, _ in appsim.code_chunks(pack(moved))}
        self.assertGreater(len(a & b) / len(a), 0.95)
        raw_a = {h for h, _ in appsim.chunk_list(pack(words))}
        raw_b = {h for h, _ in appsim.chunk_list(pack(moved))}
        self.assertLess(len(raw_a & raw_b) / max(1, len(raw_a)), 0.05)


class EndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = cls.tmp.name
        shared_code = rand_code(10, 30000)
        shared_assets = [('shared-ui', noise(11, 400_000))]
        shared_ids = [f'Studio.Shared.Type{i}' for i in range(3000)]
        engine_ids = [f'UnityEngine.Thing{i}' for i in range(2000)]
        shared_classes = [f'SDKClass{i}' for i in range(300)]

        def icon(seed):
            rnd = random.Random(seed)
            grid = [[rnd.getrandbits(8) for _ in range(4)] for _ in range(4)]
            return lambda x, y: (grid[y // 6][x // 6],) * 3 + (255,)

        cls.a = make_app(root, 'GameA', 'com.example.a', relink(shared_code, 1) + rand_code(20, 4000),
                         shared_assets + [('a', noise(21, 100_000))], shared_ids + engine_ids + ['A.Only'],
                         ['shared text', 'a text'], shared_classes, ['AppLovinSDK', 'StudioKit'], icon(1))
        cls.b = make_app(root, 'GameB', 'com.example.b', relink(shared_code, 2) + rand_code(30, 4000),
                         shared_assets + [('b', noise(31, 100_000))], shared_ids + engine_ids + ['B.Only'],
                         ['shared text', 'b text'], shared_classes, ['AppLovinSDK', 'StudioKit'], icon(2))
        cls.c = make_app(root, 'Indie', 'com.other.c', rand_code(40, 30000),
                         [('c', noise(41, 500_000))], engine_ids + ['C.Only'], ['c text'], ['Other'], [], icon(3))
        cls.engine = make_app(root, 'Engine', 'com.example.engine', rand_code(50, 2000),
                              [('e', noise(51, 10_000))], engine_ids, [], [], [], icon(4))
        ipa = Path(root) / 'GameA.ipa'
        with zipfile.ZipFile(ipa, 'w') as z:
            for p in cls.a.rglob('*'):
                if p.is_file():
                    z.write(p, f'Payload/GameA.app/{p.relative_to(cls.a)}')
        cls.ipa = ipa
        cls.idx = {}
        for name, path in (('a', cls.a), ('b', cls.b), ('c', cls.c), ('engine', cls.engine), ('ipa', ipa)):
            out = Path(root) / f'{name}.json'
            appsim.save_index(appsim.build_index(str(path)), str(out), name)
            cls.idx[name] = appsim.load_index(str(out))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_ipa_and_app_index_identically(self):
        self.assertEqual(self.idx['a']['sets'], self.idx['ipa']['sets'])
        self.assertEqual(set(self.idx['a']['_chunks']['code']), set(self.idx['ipa']['_chunks']['code']))

    def test_index_has_no_plaintext_strings(self):
        raw = Path(self.idx['a']['_path']).read_text()
        self.assertNotIn('We use data for ads.', raw)
        self.assertNotIn('shared text', raw)

    def test_shared_template_scores_high_unrelated_low(self):
        r = appsim.assess(self.idx['a'], [self.idx['b'], self.idx['c']], [self.idx['engine']])
        scores = {p['peer']: p['overall'] for p in r['peers']}
        self.assertGreater(scores['b'], 0.5)
        self.assertLess(scores['c'], 0.15)
        self.assertEqual(r['peers'][0]['peer'], 'b')
        self.assertEqual(r['level'], 'high')
        self.assertIn('StudioKit.framework', r['nearest_shared']['frameworks']['sample'])

    def test_background_discounts_engine_features(self):
        with_bg = appsim.assess(self.idx['c'], [self.idx['a']], [self.idx['engine']])
        without = appsim.assess(self.idx['c'], [self.idx['a']], [])
        self.assertLess(with_bg['peers'][0]['layers']['names'], without['peers'][0]['layers']['names'])

    def test_presence_mode_excludes_reference_features(self):
        rarity = appsim.assess(self.idx['a'], [self.idx['b']], [self.idx['b'], self.idx['engine'], self.idx['c']])
        presence = appsim.assess(self.idx['a'], [self.idx['b']], [self.idx['b']], floor=0.0, mode='presence')
        self.assertGreater(rarity['peers'][0]['overall'], 0.3)
        self.assertLess(presence['peers'][0]['overall'], 0.05)

    def test_identity_shift_flag(self):
        r = appsim.assess(self.idx['a'], [self.idx['b']], [self.idx['engine']], previous=self.idx['c'])
        self.assertTrue(any('identity shift' in f for f in r['flags']))

    def test_cli_score_writes_reports(self):
        out_md = Path(self.tmp.name) / 'r.md'
        out_json = Path(self.tmp.name) / 'r.json'
        code = appsim.main(['score', self.idx['a']['_path'], '--peers', self.idx['b']['_path'], self.idx['c']['_path'],
                            '--background', self.idx['engine']['_path'], '--out-md', str(out_md), '--out-json', str(out_json),
                            '--quiet'])
        self.assertEqual(code, 2)
        self.assertIn('Risk level: **high**', out_md.read_text())
        self.assertEqual(json.loads(out_json.read_text())['level'], 'high')


if __name__ == '__main__':
    unittest.main()
