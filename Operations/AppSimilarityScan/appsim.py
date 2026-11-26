#!/usr/bin/env python3
"""App Similarity Scan: static self-check of an iOS app bundle against peer apps,
in the spirit of App Store Review Guideline 4.3 (spam / near-duplicate apps).

Subcommands:
  index  BUNDLE --out INDEX.json        build a feature index (.app, .ipa or .xcarchive)
  score  QUERY.json --peers P.json...   score one index against peers
  scan   INDEX.json...                  all-pairs matrix and clusters

Standard library only. The scoring model is a reconstruction for self-checks,
not Apple's implementation.
"""

import argparse
import fnmatch
import hashlib
import io
import json
import math
import os
import plistlib
import re
import sys
import zipfile
from array import array
from struct import error as struct_error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import appsim_formats as fmt

INDEX_SCHEMA = 1

DEFAULT_THIRD_PARTY = [
    'AppLovin*', 'FBSDK*', 'FBAEMKit*', 'FBAudienceNetwork*', 'Firebase*', 'Google*', 'GoogleMobileAds*',
    'UserMessagingPlatform*', 'OneSignal*', 'InMobi*', 'Moloco*', 'Vungle*', 'Unity Ads*', 'UnityAds*',
    'IronSource*', 'Mintegral*', 'MTG*', 'BidMachine*', 'Pangle*', 'PAG*', 'BURelyFoundation*', 'Chartboost*',
    'AppsFlyer*', 'Adjust*', 'Branch*', 'Sentry*', 'Crashlytics*', 'Lofelt*', 'VelocityAds*', 'Zendesk*',
    'Usercentrics*', 'Mixpanel*', 'Amplitude*', 'RevenueCat*', 'Purchases*', 'Kingfisher*', 'Alamofire*',
]

CODE_SECTIONS = {'__text', '__stubs', '__auth_stubs'}

LAYER_WEIGHTS = {
    'code': 0.30,
    'assets': 0.20,
    'names': 0.20,
    'strings': 0.10,
    'packaging': 0.10,
    'icon': 0.05,
    'binary_data': 0.05,
}

LAYER_OF = {
    'code': 'code',
    'macho_data': 'binary_data',
    'assets': 'assets',
    'objc_classes': 'names',
    'objc_selectors': 'names',
    'il2cpp_identifiers': 'names',
    'il2cpp_assemblies': 'names',
    'cstrings': 'strings',
    'il2cpp_literals': 'strings',
    'frameworks': 'packaging',
    'plist_items': 'packaging',
    'privacy_items': 'packaging',
}

READABLE = {'objc_classes', 'il2cpp_assemblies', 'frameworks', 'plist_keys', 'namespaces'}


def h12(data):
    return hashlib.blake2b(data, digest_size=12).hexdigest()


# ---------------------------------------------------------------- chunking

_GEAR = [(i * 0x9E3779B97F4A7C15 + 0x632BE59BD9B4E019) & 0xFFFFFFFFFFFFFFFF for i in range(256)]
_M64 = 0xFFFFFFFFFFFFFFFF


def byte_chunks(data, min_size=2048, mask_bits=13, max_size=65536):
    mask = (1 << mask_bits) - 1
    n = len(data)
    i = 0
    while i < n:
        end = min(n, i + max_size)
        k = i + min_size
        if k >= end:
            yield i, end
            return
        h = 0
        cut = end
        while k < end:
            h = ((h << 1) + _GEAR[data[k]]) & _M64
            k += 1
            if (h & mask) == 0:
                cut = k
                break
        yield i, cut
        i = cut


def mask_arm64(word):
    """Zero address/offset immediates so identical source code linked at other
    addresses hashes the same."""
    if (word & 0x7C000000) == 0x14000000:
        return word & 0xFC000000
    if (word & 0xFF000010) == 0x54000000:
        return word & 0xFF00001F
    if (word & 0x7E000000) == 0x34000000:
        return word & 0xFF00001F
    if (word & 0x7E000000) == 0x36000000:
        return word & 0xFFF8001F
    if (word & 0x1F000000) == 0x10000000:
        return word & 0x9F00001F
    if (word & 0x3B000000) == 0x18000000:
        return word & 0xFF00001F
    if (word & 0x1F000000) == 0x11000000:
        return word & 0xFFC003FF
    if (word & 0x3B000000) == 0x39000000:
        return word & 0xFFC003FF
    return word


def code_chunks(blob, min_words=64, mask_bits=9, max_words=4096):
    count = len(blob) // 4
    words = array('I', blob[:count * 4])
    if sys.byteorder != 'little':
        words.byteswap()
    norm = array('I', (mask_arm64(w) for w in words))
    data = norm.tobytes()
    mask = (1 << mask_bits) - 1
    i = 0
    while i < count:
        end = min(count, i + max_words)
        k = i + min_words
        if k >= end:
            yield h12(data[i * 4:end * 4]), (end - i) * 4
            return
        h = 0
        cut = end
        while k < end:
            w = norm[k]
            h = ((h << 1) + _GEAR[(w ^ (w >> 11) ^ (w >> 22)) & 255]) & _M64
            k += 1
            if (h & mask) == 0:
                cut = k
                break
        yield h12(data[i * 4:cut * 4]), (cut - i) * 4
        i = cut


def chunk_list(data):
    return [[h12(data[a:b]), b - a] for a, b in byte_chunks(data)]


# ---------------------------------------------------------------- bundle access

def iter_bundle(path):
    """Yield (relative path inside the .app, bytes) for every regular file."""
    path = os.path.abspath(path)
    if os.path.isfile(path) and zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if re.match(r'Payload/[^/]+\.app/', n) and not n.endswith('/')]
            for n in names:
                info = z.getinfo(n)
                if (info.external_attr >> 16) & 0o170000 == 0o120000:
                    continue
                rel = n.split('.app/', 1)[1]
                yield rel, z.read(n)
        return
    app = path
    if path.endswith('.xcarchive'):
        apps_dir = os.path.join(path, 'Products', 'Applications')
        found = [d for d in os.listdir(apps_dir) if d.endswith('.app')]
        if not found:
            raise SystemExit(f'no .app inside {path}')
        app = os.path.join(apps_dir, found[0])
    if not os.path.isdir(app):
        raise SystemExit(f'unsupported bundle: {path}')
    for root, _, files in os.walk(app):
        for f in files:
            p = os.path.join(root, f)
            if os.path.islink(p):
                continue
            with open(p, 'rb') as fh:
                yield os.path.relpath(p, app), fh.read()


def flatten_plist(obj, prefix=''):
    if isinstance(obj, dict):
        for k in sorted(obj):
            yield from flatten_plist(obj[k], f'{prefix}{k}/')
    elif isinstance(obj, list):
        for v in obj:
            yield from flatten_plist(v, f'{prefix}[]/')
    else:
        yield prefix.rstrip('/'), repr(obj)


VOLATILE_PLIST_KEYS = {
    'CFBundleIdentifier', 'CFBundleVersion', 'CFBundleShortVersionString', 'CFBundleName',
    'CFBundleDisplayName', 'CFBundleExecutable', 'BuildMachineOSBuild', 'DTCompiler', 'DTPlatformBuild',
    'DTPlatformName', 'DTPlatformVersion', 'DTSDKBuild', 'DTSDKName', 'DTXcode', 'DTXcodeBuild',
    'CFBundleSupportedPlatforms', 'MinimumOSVersion', 'CFBundleInfoDictionaryVersion', 'CFBundlePackageType',
}


# ---------------------------------------------------------------- indexing

class Index:
    def __init__(self):
        self.chunks = {'code': {}, 'macho_data': {}, 'assets': {}}
        self.sets = {k: set() for k in ('objc_classes', 'objc_selectors', 'cstrings', 'il2cpp_identifiers',
                                        'il2cpp_literals', 'il2cpp_assemblies', 'frameworks', 'plist_items',
                                        'privacy_items')}
        self.names = {k: set() for k in READABLE}
        self.icons = []
        self.meta = {}
        self.owner_images = []
        self.owners = {}

    def add_chunks(self, layer, group, items):
        bucket = self.chunks[layer].setdefault(group, {})
        for h, size in items:
            bucket[h] = bucket.get(h, 0) + size


def _group_for(rel, third_party):
    parts = rel.split('/')
    if parts[0] in ('Frameworks', 'PlugIns') and len(parts) > 1:
        name = parts[1].rsplit('.', 1)[0]
        if any(fnmatch.fnmatch(name, pat) for pat in third_party):
            return 'third_party'
        return 'app_frameworks'
    return 'app'


def _add_strings(idx, layer, blob, minlen):
    for part in blob.split(b'\0'):
        if len(part) >= minlen:
            idx.sets[layer].add(h12(part))
            if layer == 'objc_classes' and re.fullmatch(rb'[A-Za-z_$][\w$.]+', part):
                idx.names['objc_classes'].add(part.decode('ascii'))


def build_index(bundle, third_party=None, max_icon_pixels=1_500_000):
    third_party = third_party or DEFAULT_THIRD_PARTY
    idx = Index()
    total = 0
    for rel, data in iter_bundle(bundle):
        if rel.startswith('_CodeSignature/') or rel.endswith('embedded.mobileprovision') or '/_CodeSignature/' in rel:
            continue
        total += len(data)
        group = _group_for(rel, third_party)
        parts = rel.split('/')
        if parts[0] in ('Frameworks', 'PlugIns') and len(parts) == 3 and parts[2] == parts[1].rsplit('.', 1)[0]:
            idx.sets['frameworks'].add(h12(parts[1].encode()))
            idx.names['frameworks'].add(parts[1])
        if rel == 'Info.plist':
            try:
                info = plistlib.loads(data)
            except Exception:
                info = {}
            idx.meta['bundle_id'] = info.get('CFBundleIdentifier')
            idx.meta['version'] = info.get('CFBundleShortVersionString')
            idx.meta['build'] = info.get('CFBundleVersion')
            for k in info:
                idx.names['plist_keys'].add(k)
            for key, value in flatten_plist({k: v for k, v in info.items() if k not in VOLATILE_PLIST_KEYS}):
                idx.sets['plist_items'].add(h12(f'{key}={value}'.encode()))
            continue
        if rel.endswith('.xcprivacy') and '/' not in rel:
            try:
                priv = plistlib.loads(data)
                for key, value in flatten_plist(priv):
                    idx.sets['privacy_items'].add(h12(f'{key}={value}'.encode()))
            except Exception:
                pass
        if fmt.is_macho(data[:4]):
            for (seg, sect), blob in fmt.macho_sections(data).items():
                if not blob:
                    continue
                if seg == '__TEXT' and sect in CODE_SECTIONS:
                    idx.add_chunks('code', group, code_chunks(blob))
                    continue
                if sect == '__objc_classname':
                    _add_strings(idx, 'objc_classes', blob, 1)
                elif sect == '__objc_methname':
                    _add_strings(idx, 'objc_selectors', blob, 1)
                elif sect == '__cstring':
                    _add_strings(idx, 'cstrings', blob, 6)
                idx.add_chunks('macho_data', group, chunk_list(blob))
            continue
        if rel.endswith('global-metadata.dat'):
            try:
                version, identifiers, literals = fmt.il2cpp_metadata(data)
                idx.meta['il2cpp_metadata_version'] = version
                for s in identifiers:
                    idx.sets['il2cpp_identifiers'].add(h12(s.encode()))
                    if s.endswith('.dll'):
                        idx.sets['il2cpp_assemblies'].add(h12(s.encode()))
                        idx.names['il2cpp_assemblies'].add(s)
                    elif re.fullmatch(r'[A-Za-z_]\w*(\.[A-Za-z_]\w*)+', s):
                        idx.names['namespaces'].add(s)
                for s in literals:
                    idx.sets['il2cpp_literals'].add(h12(s.encode()))
                try:
                    ownership = fmt.il2cpp_ownership(data)
                    images = sorted({img for imgs in ownership.values() for img in imgs})
                    pos = {img: i for i, img in enumerate(images)}
                    idx.owner_images = images
                    idx.owners = {h12(s.encode()): sorted(pos[i] for i in imgs) for s, imgs in ownership.items()}
                    for img in images:
                        idx.owners.setdefault(h12(img.encode()), [pos[img]])
                except (ValueError, struct_error) as exc:
                    idx.meta.setdefault('warnings', []).append(f'{rel}: ownership {exc}')
            except ValueError:
                idx.add_chunks('assets', 'app', chunk_list(data))
            continue
        if data.startswith(b'UnityFS\0'):
            try:
                for _, entry in fmt.unityfs_entries(data):
                    idx.add_chunks('assets', 'app', chunk_list(entry))
                continue
            except ValueError as exc:
                idx.meta.setdefault('warnings', []).append(f'{rel}: {exc}')
        if re.match(r'AppIcon.*\.png$', os.path.basename(rel)):
            try:
                w, h, rows = fmt.png_gray(data)
                if w * h <= max_icon_pixels:
                    idx.icons.append(fmt.dhash(w, h, rows))
            except (ValueError, Exception) as exc:
                idx.meta.setdefault('warnings', []).append(f'{rel}: icon {exc}')
        idx.add_chunks('assets' if rel.startswith('Data/') or rel.endswith(('.car', '.png', '.jpg', '.ttf', '.otf')) else 'macho_data', 'app', chunk_list(data))
    idx.meta['bundle_bytes'] = total
    idx.meta['source'] = os.path.basename(os.path.abspath(bundle))
    return idx


def save_index(idx, out, label=None):
    doc = {
        'schema': INDEX_SCHEMA,
        'label': label or idx.meta.get('bundle_id') or idx.meta.get('source'),
        'meta': idx.meta,
        'chunks': idx.chunks,
        'sets': {k: sorted(v) for k, v in idx.sets.items()},
        'names': {k: sorted(v) for k, v in idx.names.items()},
        'icons': [format(x, '016x') for x in idx.icons],
        'owners': {'images': idx.owner_images, 'map': idx.owners},
    }
    with open(out, 'w') as fh:
        json.dump(doc, fh)


def load_index(path):
    with open(path) as fh:
        doc = json.load(fh)
    if doc.get('schema') != INDEX_SCHEMA:
        raise SystemExit(f'{path}: unsupported index schema {doc.get("schema")}')
    doc['sets'] = {k: set(v) for k, v in doc['sets'].items()}
    doc['names'] = {k: set(v) for k, v in doc['names'].items()}
    doc['icons'] = [int(x, 16) for x in doc['icons']]
    doc['_path'] = path
    flat = {}
    for layer, groups in doc['chunks'].items():
        merged = {}
        for group, items in groups.items():
            for h, size in items.items():
                merged[h] = (merged.get(h, (0, group))[0] + size, group)
        flat[layer] = merged
    doc['_chunks'] = flat
    return doc


# ---------------------------------------------------------------- scoring

class Weights:
    """Feature weight = rarity in a background corpus of unrelated apps, times a
    discount for known third-party frameworks."""

    def __init__(self, background, floor=0.05, third_party_factor=0.25, mode='rarity'):
        if mode not in ('rarity', 'presence'):
            raise ValueError(f'unknown background mode {mode}')
        self.floor = floor
        self.third_party_factor = third_party_factor
        self.mode = mode
        self.n = len(background)
        self.df = {}
        for doc in background:
            seen = set()
            for layer, items in doc['_chunks'].items():
                seen.update(('c', h) for h in items)
            for layer, items in doc['sets'].items():
                seen.update(('s', layer, h) for h in items)
            for key in seen:
                self.df[key] = self.df.get(key, 0) + 1

    def rarity(self, key):
        if not self.n:
            return 1.0
        df = self.df.get(key, 0)
        if not df:
            return 1.0
        if self.mode == 'presence':
            return self.floor
        return self.floor + (1 - self.floor) * (1 - df / self.n) ** 2

    def chunk(self, h, group):
        w = self.rarity(('c', h))
        if group == 'third_party':
            w *= self.third_party_factor
        return w

    def item(self, layer, h):
        return self.rarity(('s', layer, h))


def layer_containment(q, p_docs, weights):
    """Per sub-layer weighted containment of q in the union of p_docs."""
    out = {}
    for layer, items in q['_chunks'].items():
        union = set()
        for p in p_docs:
            union.update(p['_chunks'].get(layer, {}))
        tot = sh = raw_tot = raw_sh = 0.0
        for h, (size, group) in items.items():
            w = weights.chunk(h, group) * size
            tot += w
            raw_tot += size
            if h in union:
                sh += w
                raw_sh += size
        out[layer] = {'weighted': sh / tot if tot else None, 'raw': raw_sh / raw_tot if raw_tot else None,
                      'mass': tot, 'bytes': raw_tot}
    for layer, items in q['sets'].items():
        union = set()
        for p in p_docs:
            union.update(p['sets'].get(layer, ()))
        tot = sh = 0.0
        for h in items:
            w = weights.item(layer, h)
            tot += w
            if h in union:
                sh += w
        out[layer] = {'weighted': sh / tot if tot else None, 'raw': (len(items & union) / len(items)) if items else None,
                      'mass': tot, 'count': len(items)}
    return out


def icon_similarity(q, p_docs):
    best = None
    for a in q['icons']:
        for p in p_docs:
            for b in p['icons']:
                d = bin(a ^ b).count('1')
                s = max(0.0, 1 - d / 32)
                best = s if best is None else max(best, s)
    return best


def combine(sub, icon):
    """Layer score = mass-weighted mean of its sub-layers; overall = LAYER_WEIGHTS mean."""
    layers = {}
    for name, res in sub.items():
        if res['weighted'] is None:
            continue
        layer = LAYER_OF[name]
        acc = layers.setdefault(layer, [0.0, 0.0])
        mass = res['mass'] if layer in ('code', 'assets', 'binary_data') else 1.0
        acc[0] += res['weighted'] * mass
        acc[1] += mass
    scores = {k: v[0] / v[1] for k, v in layers.items() if v[1]}
    if icon is not None:
        scores['icon'] = icon
    wsum = sum(LAYER_WEIGHTS[k] for k in scores)
    overall = sum(LAYER_WEIGHTS[k] * s for k, s in scores.items()) / wsum if wsum else 0.0
    return overall, scores


def pair_score(q, p, weights):
    sub = layer_containment(q, [p], weights)
    overall, layers = combine(sub, icon_similarity(q, [p]))
    return {'peer': p['label'], 'overall': overall, 'layers': layers, 'sub': sub}


DEFAULT_OWNER_GROUPS = [
    ('engine/.NET', r'^(UnityEngine|mscorlib|System|Mono\.|netstandard|__Generated|Unity\.(TextMeshPro|Burst|Mathematics|Collections|Jobs|RenderPipelines|Timeline|InputSystem|Animation|Postprocessing|Profiling|InternalAPI|Services\.Core|Notifications|Purchasing|Mobile|AI\.|Addressables|ResourceManager|ScriptableBuildPipeline|2D|Splines|Cinemachine|VisualScripting|Localization|Entities|Physics|Properties|Serialization))'),
]


def owner_breakdown(q, p, groups=None, background=None, top=15, rest=None):
    """Attribute the IL2CPP identifiers q shares with p to the assemblies that declare
    them in q. Identifiers also present in a background index are counted as 'in background'.
    Groups are (label, regex on assembly name): caller groups first, then the built-in
    engine/.NET group, then `rest` (if given) for everything else; otherwise unmatched
    assemblies are reported by name."""
    owners = q.get('owners') or {}
    images = owners.get('images') or []
    mapping = owners.get('map') or {}
    if not images:
        return None
    ordered = (groups or []) + DEFAULT_OWNER_GROUPS + ([(rest, '.')] if rest else [])
    groups = [(label, re.compile(rx)) for label, rx in ordered]
    bg = set()
    for b in background or []:
        bg |= b['sets'].get('il2cpp_identifiers', set())

    def bucket(name):
        stem = name[:-4] if name.endswith('.dll') else name
        for label, rx in groups:
            if rx.search(stem):
                return label
        return stem

    ids = q['sets'].get('il2cpp_identifiers', set())
    shared = ids & p['sets'].get('il2cpp_identifiers', set())
    counts, totals = {}, {}
    for h in ids:
        if h in bg:
            key = 'in background'
        else:
            labels = sorted({bucket(images[i]) for i in mapping.get(h, [])})
            key = 'engine/.NET' if 'engine/.NET' in labels else (labels[0] if len(labels) == 1 else ('mixed' if labels else 'unattributed'))
        totals[key] = totals.get(key, 0) + 1
        if h in shared:
            counts[key] = counts.get(key, 0) + 1
    rows = sorted(((k, counts.get(k, 0), totals[k]) for k in totals), key=lambda r: -r[1])
    head, tail = rows[:top], rows[top:]
    if tail:
        head.append(('other', sum(r[1] for r in tail), sum(r[2] for r in tail)))
    return {'query_identifiers': len(ids), 'shared': len(shared), 'rows': head}


def shared_readable(q, p, limit=40):
    out = {}
    for k in ('frameworks', 'il2cpp_assemblies', 'objc_classes', 'namespaces'):
        both = sorted(q['names'].get(k, set()) & p['names'].get(k, set()))
        out[k] = {'shared': len(both), 'total': len(q['names'].get(k, ())), 'sample': both[:limit]}
    return out


DEFAULT_THRESHOLDS = {'cluster': 0.40, 'high': 0.50, 'medium': 0.35, 'unique_low': 0.70}


def assess(q, peers, background, previous=None, thresholds=None, floor=0.05, third_party_factor=0.25, groups=None, rest=None,
           mode='rarity'):
    t = dict(DEFAULT_THRESHOLDS, **(thresholds or {}))
    weights = Weights(background, floor=floor, third_party_factor=third_party_factor, mode=mode)
    pairs = sorted((pair_score(q, p, weights) for p in peers), key=lambda r: -r['overall'])
    union_sub = layer_containment(q, peers, weights) if peers else {}
    shared_any, _ = combine(union_sub, icon_similarity(q, peers)) if peers else (0.0, {})
    uniqueness = 1 - shared_any
    cluster = [r['peer'] for r in pairs if r['overall'] >= t['cluster']]
    nn = pairs[0] if pairs else None
    result = {
        'query': q['label'],
        'meta': q['meta'],
        'peers': pairs,
        'uniqueness': uniqueness,
        'cluster': cluster,
        'thresholds': t,
        'background': [b['label'] for b in background],
        'background_mode': mode,
        'floor': floor,
        'flags': [],
    }
    if previous is not None:
        prev = pair_score(q, previous, weights)
        result['self_similarity'] = prev['overall']
        result['self_layers'] = prev['layers']
        if nn and nn['overall'] > prev['overall']:
            result['flags'].append(f"identity shift: closer to {nn['peer']} ({nn['overall']:.0%}) than to its own previous build ({prev['overall']:.0%})")
    level = 'low'
    if nn and nn['overall'] >= t['medium']:
        level = 'medium'
    if nn and nn['overall'] >= t['high'] and (uniqueness <= t['unique_low'] or len(cluster) >= 2):
        level = 'high'
    if level != 'low':
        result['flags'].append(f"nearest peer {nn['peer']} at {nn['overall']:.0%}; {len(cluster)} peer(s) above {t['cluster']:.0%}; uniqueness {uniqueness:.0%}")
    result['level'] = level
    if nn:
        top = next(p for p in peers if p['label'] == nn['peer'])
        result['nearest_shared'] = shared_readable(q, top)
        result['nearest_owners'] = owner_breakdown(q, top, groups, background, rest=rest)
    return result


def pct(x):
    return '—' if x is None else f'{x:.0%}'


def render_markdown(r):
    lines = [f"# App similarity scan: {r['query']}", '']
    m = r['meta']
    lines.append(f"- Bundle: `{m.get('bundle_id')}` {m.get('version')} ({m.get('build')}), {m.get('bundle_bytes', 0) / 1e6:.1f} MB scanned")
    lines.append(f"- Risk level: **{r['level']}**")
    lines.append(f"- Uniqueness (weighted content found in no peer): **{r['uniqueness']:.0%}**")
    if 'self_similarity' in r:
        lines.append(f"- Similarity to its own previous build: **{r['self_similarity']:.0%}**")
    lines.append(f"- Background corpus ({r.get('background_mode', 'rarity')} mode, floor {r.get('floor', 0.05)}): {', '.join(r['background']) or 'none (all features weight 1)'}")
    for f in r['flags']:
        lines.append(f'- Flag: {f}')
    lines += ['', '| Peer | Overall | Code | Assets | Names | Strings | Packaging | Icon | Binary data |', '|---|---|---|---|---|---|---|---|---|']
    for p in r['peers']:
        L = p['layers']
        lines.append(f"| {p['peer']} | **{p['overall']:.0%}** | {pct(L.get('code'))} | {pct(L.get('assets'))} | {pct(L.get('names'))} | {pct(L.get('strings'))} | {pct(L.get('packaging'))} | {pct(L.get('icon'))} | {pct(L.get('binary_data'))} |")
    if r['peers']:
        nn = r['peers'][0]
        lines += ['', f"## Sub-layers vs nearest peer `{nn['peer']}`", '', '| Sub-layer | Weighted | Raw | Size |', '|---|---|---|---|']
        for k, v in nn['sub'].items():
            size = f"{v['bytes'] / 1e6:.1f} MB" if 'bytes' in v else f"{v.get('count', 0)} items"
            lines.append(f"| {k} | {pct(v['weighted'])} | {pct(v['raw'])} | {size} |")
        ob = r.get('nearest_owners')
        if ob:
            n = ob['query_identifiers']
            lines += ['', f"## Who owns the IL2CPP identifiers shared with `{nn['peer']}`", '',
                      f"{ob['shared']} of {n} identifiers shared ({ob['shared'] / n:.0%}).", '',
                      '| Owner (assembly or group) | Shared | Share of all query identifiers | Owner total | Owner shared |',
                      '|---|---|---|---|---|']
            for name, shared, total in ob['rows']:
                lines.append(f"| {name} | {shared} | {shared / n:.1%} | {total} | {shared / total if total else 0:.0%} |")
        lines += ['', '## Shared readable features with the nearest peer', '']
        for k, v in r.get('nearest_shared', {}).items():
            lines.append(f"- {k}: {v['shared']} / {v['total']}; e.g. {', '.join(v['sample'][:15])}")
    lines += ['', '## Method', '',
              '- Code: ARM64 `__text`/stubs with address and offset immediates masked, content-defined chunks (~2 KB).',
              '- Assets: UnityFS bundles unpacked, then all data files cut into content-defined chunks (~8 KB).',
              '- Names and strings: ObjC class/selector names, C strings, IL2CPP identifiers, literals and assemblies, compared as sets.',
              '- Packaging: framework list, Info.plist key=value pairs (build-volatile keys excluded), privacy manifest.',
              '- Icon: 64-bit dHash of AppIcon PNGs (Apple CgBI supported).',
              '- Weight of a feature = rarity in the background corpus (unrelated apps, engine-only builds); known third-party frameworks get a further discount.',
              f"- Overall = weighted mean of layers {LAYER_WEIGHTS}. Containment is asymmetric: share of the query found in the peer.",
              '- This is a self-check model, not Apple\'s algorithm. Store-listing text and screenshots are not covered.']
    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------- CLI

def cmd_index(args):
    third = DEFAULT_THIRD_PARTY + (args.third_party or [])
    idx = build_index(args.bundle, third)
    save_index(idx, args.out, args.label)
    sizes = {k: round(sum(sum(g.values()) for g in v.values()) / 1e6, 1) for k, v in idx.chunks.items()}
    print(json.dumps({'out': args.out, 'label': args.label or idx.meta.get('bundle_id'), 'chunk_mb': sizes,
                      'sets': {k: len(v) for k, v in idx.sets.items()}, 'icons': len(idx.icons),
                      'warnings': idx.meta.get('warnings', [])}, indent=1))


def cmd_score(args):
    q = load_index(args.query)
    peers = [load_index(p) for p in args.peers]
    background = [load_index(b) for b in (args.background or [])]
    previous = load_index(args.previous) if args.previous else None
    groups = []
    for g in args.group or []:
        label, _, rx = g.partition('=')
        if not rx:
            raise SystemExit(f'--group expects LABEL=REGEX, got {g!r}')
        groups.append((label, rx))
    r = assess(q, peers, background, previous, floor=args.floor, third_party_factor=args.third_party_factor,
               groups=groups, rest=args.group_rest, mode=args.background_mode)
    md = render_markdown(r)
    if args.out_md:
        with open(args.out_md, 'w') as fh:
            fh.write(md)
    if args.out_json:
        slim = dict(r)
        with open(args.out_json, 'w') as fh:
            json.dump(slim, fh, indent=1, default=list)
    if not args.quiet:
        print(md)
    return 2 if r['level'] == 'high' else 0


def cmd_scan(args):
    docs = [load_index(p) for p in args.indexes]
    background = [load_index(b) for b in (args.background or [])]
    weights = Weights(background, floor=args.floor, third_party_factor=args.third_party_factor, mode=args.background_mode)
    labels = [d['label'] for d in docs]
    matrix = [[None if i == j else pair_score(a, b, weights)['overall'] for j, b in enumerate(docs)] for i, a in enumerate(docs)]
    parent = list(range(len(docs)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i in range(len(docs)):
        for j in range(i + 1, len(docs)):
            if min(matrix[i][j], matrix[j][i]) >= args.cluster:
                parent[find(i)] = find(j)
    clusters = {}
    for i in range(len(docs)):
        clusters.setdefault(find(i), []).append(labels[i])
    print('| query \\ peer | ' + ' | '.join(labels) + ' |')
    print('|---' * (len(labels) + 1) + '|')
    for i, row in enumerate(matrix):
        print(f'| {labels[i]} | ' + ' | '.join('—' if v is None else f'{v:.0%}' for v in row) + ' |')
    print()
    for members in clusters.values():
        if len(members) > 1:
            print(f'cluster (both directions >= {args.cluster:.0%}): ' + ', '.join(members))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('index')
    a.add_argument('bundle')
    a.add_argument('--out', required=True)
    a.add_argument('--label')
    a.add_argument('--third-party', action='append', help='extra framework name glob treated as third-party')
    a.set_defaults(func=cmd_index)
    for name in ('score', 'scan'):
        s = sub.add_parser(name)
        if name == 'score':
            s.add_argument('query')
            s.add_argument('--peers', nargs='+', required=True)
            s.add_argument('--previous', help='index of the same app\'s previous build')
            s.add_argument('--out-md')
            s.add_argument('--out-json')
            s.add_argument('--group', action='append', help='LABEL=REGEX on assembly names, e.g. studio=^(MyCo|Shared)')
            s.add_argument('--group-rest', help='label for assemblies matched by no group (default: list them by name)')
            s.add_argument('--quiet', action='store_true', help='do not print the markdown report')
            s.set_defaults(func=cmd_score)
        else:
            s.add_argument('indexes', nargs='+')
            s.add_argument('--cluster', type=float, default=DEFAULT_THRESHOLDS['cluster'])
            s.set_defaults(func=cmd_scan)
        s.add_argument('--background', nargs='*', help='indexes of unrelated apps / engine-only builds')
        s.add_argument('--floor', type=float, default=0.05)
        s.add_argument('--background-mode', choices=('rarity', 'presence'), default='rarity',
                       help='rarity: weight falls with the share of background apps containing a feature; '
                            'presence: any feature found in the background gets --floor (use --floor 0 to exclude it)')
        s.add_argument('--third-party-factor', type=float, default=0.25)
    args = ap.parse_args(argv)
    return args.func(args) or 0


if __name__ == '__main__':
    sys.exit(main())
