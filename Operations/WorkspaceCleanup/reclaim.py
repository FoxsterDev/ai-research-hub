"""Tier A: delete reviewed, regenerable cache paths that are stale and idle.

Each rule names exact relative targets under explicit roots or under detected
containers (Xcode DerivedData by content, verified Unity Library, or named
directories). A target is deleted only when every guard passes; otherwise it is
kept with a reason. Deletion renames to a sibling tombstone first, so a crash
never leaves a half-deleted cache under its original name.
"""
from __future__ import annotations

import math
import os
import shutil
import sys
import time
import uuid
from fnmatch import fnmatch
from pathlib import Path

import cleanup_common as common
from cleanup_common import Deferred

TOMBSTONE = '.reclaim-'
SKIP_WALK = {'.git', 'node_modules'}
CONTAINER_KINDS = {'xcode_derived_data', 'unity_library', 'named'}


def _rule_minimum(rule: dict) -> float:
    minimum = float(rule.get('minimum_age_hours', 'nan'))
    if not math.isfinite(minimum) or minimum < 24:
        raise Deferred('rule needs minimum_age_hours >= 24')
    return minimum


def _is_container(path: Path, rule: dict) -> bool:
    kind = rule['container_kind']
    if kind == 'xcode_derived_data':
        return common.is_xcode_derived_data(path)
    if kind == 'unity_library':
        return path.name == 'Library' and common.is_unity_project(path.parent)
    return any(fnmatch(path.name, pattern) for pattern in rule.get('container_names', []))


def containers(rule: dict) -> list[Path]:
    found: list[Path] = []
    for raw in rule.get('scan_roots', []):
        root = Path(raw)
        if not root.is_dir() or root.is_symlink():
            continue
        for current, dirs, _files in os.walk(root, followlinks=False):
            keep = []
            for name in sorted(dirs):
                if name in SKIP_WALK or name.startswith(TOMBSTONE) or name.startswith('.pruning-'):
                    continue
                candidate = Path(current) / name
                if candidate.is_symlink():
                    continue
                if _is_container(candidate, rule):
                    found.append(candidate)
                else:
                    keep.append(name)
            dirs[:] = keep
    return found


def expand(rule: dict) -> tuple[list[tuple[Path, Path | None]], list[Path]]:
    """((target, owning container or None), leftover tombstones) for one rule."""
    if rule.get('container_kind') and rule['container_kind'] not in CONTAINER_KINDS:
        raise Deferred(f"unknown container_kind {rule['container_kind']}")
    bases = containers(rule) if rule.get('container_kind') else [Path(r) for r in rule.get('roots', [])]
    targets: list[tuple[Path, Path | None]] = []
    tombstones: list[Path] = []
    container = bool(rule.get('container_kind'))
    prefixes = tuple(rule.get('name_prefixes', []))
    for base in bases:
        if not base.is_dir() or base.is_symlink():
            continue
        for pattern in rule['targets']:
            matches = [base] if pattern == '.' else sorted(base.glob(pattern))
            for match in matches:
                if match.name.startswith(TOMBSTONE):
                    continue
                if prefixes and not match.name.startswith(prefixes):
                    continue
                if match.is_symlink() or not match.exists():
                    continue
                owner = base.parent if rule.get('container_kind') == 'unity_library' else base
                targets.append((match, owner if container else None))
        for parent in {base, *(t.parent for t, _ in targets if common.within(t, base))}:
            tombstones.extend(p for p in parent.glob(TOMBSTONE + '*') if p.is_dir() and not p.is_symlink())
    return sorted(set(targets)), sorted(set(tombstones))


def _remove_tree(path: Path) -> list[str]:
    failures: list[str] = []
    record = lambda _f, p, e: failures.append(f'{p}: {e}')
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=record)
    else:
        shutil.rmtree(path, onerror=record)
    return failures


def _delete(target: Path) -> dict:
    tombstone = target.with_name(f'{TOMBSTONE}{uuid.uuid4().hex[:8]}-{target.name}')
    target.rename(tombstone)
    failures = _remove_tree(tombstone) if tombstone.is_dir() else []
    if not tombstone.is_dir():
        tombstone.unlink(missing_ok=True)
    if failures:
        return {'state': 'partially_deleted', 'tombstone': str(tombstone), 'reason': failures[0],
                'failures': len(failures)}
    return {'state': 'deleted'}


def assess(target: Path, rule: dict, protected: list[Path], now: float, table, open_files,
           container: Path | None = None) -> dict:
    row = {'rule': rule['name'], 'path': str(target), 'state': 'eligible'}
    try:
        path = common.canonical(target)
        if any(common.within(path, p) or common.within(p, path) for p in protected):
            return {**row, 'state': 'kept', 'reason': 'protected path overlap'}
        stats = common.tree_stats(path, rule.get('forbid_suffixes', common.PROTECTED_SUFFIXES))
        row.update(logical_bytes=stats['logical_bytes'], allocated_bytes=stats['allocated_bytes'],
                   newest_age_hours=round(max(0.0, now - stats['newest_mtime']) / 3600, 1))
        if stats['protected']:
            return {**row, 'state': 'kept', 'reason': f"protected artifact inside: {stats['protected'][0]}"}
        if stats['errors']:
            return {**row, 'state': 'deferred', 'reason': f"unreadable subtree: {stats['errors'][0]}"}
        if now - stats['newest_mtime'] < _rule_minimum(rule) * 3600:
            return {**row, 'state': 'kept_recent', 'reason': 'newest descendant inside retention window'}
        if rule.get('require_unity_project') and not common.is_unity_project(path.parent):
            return {**row, 'state': 'kept', 'reason': 'Unity project identity not verified'}
        if common.git_tracked_inside(path):
            return {**row, 'state': 'kept', 'reason': 'tracked files inside'}
        if rule.get('skip_dirty_git') and common.contains_dirty_git(path):
            return {**row, 'state': 'kept', 'reason': 'dirty or unreadable Git checkout inside'}
        if common.referencing(table, path) or (container is not None and common.referencing(table, container)):
            return {**row, 'state': 'deferred', 'reason': 'live process references path'}
        if common.has_open_file(open_files, path):
            return {**row, 'state': 'deferred', 'reason': 'open files inside'}
    except (Deferred, OSError, ValueError) as error:
        return {**row, 'state': 'deferred', 'reason': str(error)}
    return row


def run_rule(rule: dict, protected: list[Path], broker_state: str | None, apply: bool, now: float,
             table_source=None, open_source=None) -> list[dict]:
    table_source = table_source or common.process_table
    open_source = open_source or common.open_paths
    rows: list[dict] = []
    try:
        _rule_minimum(rule)
        targets, tombstones = expand(rule)
        ignored = set(rule.get('ignore_reference_from', []))
        table = [row for row in table_source() if row[0] not in ignored]
        active = common.blocking(table, rule.get('block_executables', []))
        if active:
            return [{'rule': rule['name'], 'path': str(t), 'state': 'deferred',
                     'reason': f"active {', '.join(active)}"} for t, _ in targets]
        open_files = open_source() if targets else []
    except (Deferred, OSError, ValueError, KeyError) as error:
        return [{'rule': rule.get('name', '?'), 'state': 'deferred', 'reason': f'rule unavailable: {error}'}]
    rows = [assess(t, rule, protected, now, table, open_files, c) for t, c in targets]
    if not apply:
        rows += [{'rule': rule['name'], 'path': str(t), 'state': 'tombstone'} for t in tombstones]
        return rows
    eligible = [row for row in rows if row['state'] == 'eligible']
    if not eligible and not tombstones:
        return rows
    try:
        with common.broker_idle(broker_state if rule.get('use_broker') else None, table):
            for t in tombstones:
                failures = _remove_tree(t)
                rows.append({'rule': rule['name'], 'path': str(t),
                             'state': 'tombstone_partial' if failures else 'tombstone_swept'})
            for row in eligible:
                fresh = [r for r in table_source() if r[0] not in ignored]
                owner = dict((str(t), c) for t, c in targets).get(row['path'])
                if (common.blocking(fresh, rule.get('block_executables', [])) or common.referencing(fresh, Path(row['path']))
                        or (owner is not None and common.referencing(fresh, owner))):
                    row.update(state='deferred', reason='activity appeared before delete')
                    continue
                try:
                    row.update(_delete(Path(row['path'])))
                except OSError as error:
                    row.update(state='failed', reason=str(error))
    except Deferred as error:
        for row in eligible:
            row.update(state='deferred', reason=str(error))
    return rows


def run(config: dict, *, apply: bool, now: float | None = None, **sources) -> dict:
    now = time.time() if now is None else now
    protected = [Path(p) for p in config.get('protected_paths', [])]
    entries: list[dict] = []
    for rule in config.get('rules', []):
        entries.extend(run_rule(rule, protected, config.get('broker_state_dir'), apply, now, **sources))
    totals: dict[str, int] = {}
    for row in entries:
        key = f"{row['state']}_allocated_bytes"
        totals[key] = totals.get(key, 0) + row.get('allocated_bytes', 0)
    return {'mode': 'apply' if apply else 'dry_run', 'entries': entries, 'totals': totals}


def roots(config: dict) -> list[Path]:
    paths: list[Path] = []
    for rule in config.get('rules', []):
        paths += [Path(p) for p in rule.get('roots', []) + rule.get('scan_roots', [])]
    return paths
