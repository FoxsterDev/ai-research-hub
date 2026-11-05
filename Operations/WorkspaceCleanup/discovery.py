"""Read-only inventory: nested build caches, watched paths, growth alerts. Never mutates."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import cleanup_common as common
import reclaim

GIB = 1024 ** 3
DERIVED_DATA_PARTS = ('SourcePackages/repositories', 'Build/Intermediates.noindex', 'Build/Products',
                      'Index.noindex', 'ModuleCache.noindex', 'CompilationCache.noindex')


def _measure(path: Path, now: float) -> dict:
    stats = common.tree_stats(path, ())
    return {'path': str(path), 'logical_bytes': stats['logical_bytes'], 'allocated_bytes': stats['allocated_bytes'],
            'newest_age_hours': round(max(0.0, now - stats['newest_mtime']) / 3600, 1) if stats['newest_mtime'] else None,
            'errors': stats['errors'][:3]}


def _inside_evidence(path: Path, names: set[str]) -> bool:
    return bool(names & set(path.parts))


def nested(config: dict, now: float) -> list[dict]:
    items: list[dict] = []
    names = set(config.get('evidence_names', []))
    scans = [('xcode_derived_data', {'container_kind': 'xcode_derived_data'}),
             ('unity_library', {'container_kind': 'unity_library'})]
    for kind, rule in scans:
        for container in reclaim.containers({**rule, 'scan_roots': config.get('scan_roots', [])}):
            row = {'kind': kind, **_measure(container, now), 'inside_evidence': _inside_evidence(container, names)}
            if kind == 'xcode_derived_data':
                row['parts'] = {part: common.tree_stats(container / part, ())['allocated_bytes']
                                for part in DERIVED_DATA_PARTS if (container / part).is_dir()}
            items.append(row)
    return items


def watched(config: dict, now: float) -> list[dict]:
    items: list[dict] = []
    for entry in config.get('watch', []):
        path = Path(entry['path'])
        if not path.exists():
            items.append({'kind': 'watch', 'label': entry.get('label'), 'path': str(path), 'exists': False,
                          'personal': bool(entry.get('personal'))})
            continue
        children = sorted(p for p in path.iterdir() if not p.is_symlink()) if entry.get('children') else [path]
        for child in children:
            items.append({'kind': 'watch', 'label': entry.get('label'), 'personal': bool(entry.get('personal')),
                          **_measure(child, now)})
    return items


def alerts(items: list[dict], previous: dict, config: dict) -> list[dict]:
    growth = int(config.get('growth_alert_bytes', 20 * GIB))
    new_item = int(config.get('new_item_alert_bytes', 10 * GIB))
    personal_growth = int(config.get('personal_growth_alert_bytes', 2 * GIB))
    found = []
    for item in items:
        size = item.get('allocated_bytes')
        if size is None:
            continue
        before = previous.get(item['path'])
        limit = personal_growth if item.get('personal') else growth
        if before is None and not item.get('personal') and size >= new_item:
            found.append({'type': 'new_large_item', 'path': item['path'], 'allocated_bytes': size})
        elif before is not None and size - before >= limit:
            found.append({'type': 'growth', 'path': item['path'], 'allocated_bytes': size, 'growth_bytes': size - before})
    total = sum(i.get('allocated_bytes', 0) for i in items if i['kind'] != 'watch')
    previous_total = previous.get('__nested_total__')
    if previous_total is not None and total - previous_total >= growth:
        found.append({'type': 'nested_cache_growth', 'allocated_bytes': total, 'growth_bytes': total - previous_total})
    return found


def run(config: dict, *, now: float | None = None) -> dict:
    now = time.time() if now is None else now
    started = time.monotonic()
    items = nested(config, now) + watched(config, now)
    state_path = Path(config['state_path']) if config.get('state_path') else None
    previous: dict = {}
    if state_path and state_path.is_file():
        try:
            previous = json.loads(state_path.read_text()).get('sizes', {})
        except (OSError, ValueError):
            previous = {}
    found = alerts(items, previous, config)
    sizes = {item['path']: item['allocated_bytes'] for item in items if 'allocated_bytes' in item}
    sizes['__nested_total__'] = sum(i.get('allocated_bytes', 0) for i in items if i['kind'] != 'watch')
    if state_path:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = state_path.with_name(f'.{state_path.name}.{os.getpid()}.tmp')
        temporary.write_text(json.dumps({'observed_at': now, 'sizes': sizes}, indent=1, sort_keys=True))
        temporary.replace(state_path)
    by_kind: dict[str, int] = {}
    for item in items:
        by_kind[item['kind']] = by_kind.get(item['kind'], 0) + item.get('allocated_bytes', 0)
    return {'items': items, 'alerts': found, 'allocated_by_kind': by_kind,
            'duration_seconds': round(time.monotonic() - started, 1)}
