#!/usr/bin/env python3
"""Workspace cleanup: read-only discovery, tier A reclaim, tier B quarantine with expiry.

Default is a dry run. --apply deletes eligible tier A targets, moves tier B
allowlist entries into quarantine and purges expired quarantine payloads.
Exit codes: 0 clean, 3 needs attention (deferrals, partial deletes, alerts),
1 failure (a report is still written), 2 refused before running.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import sys
import time
import traceback
from pathlib import Path
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cleanup_common as common  # noqa: E402
import discovery  # noqa: E402
import reclaim  # noqa: E402
import recoverable_cleanup  # noqa: E402

SCHEMA_VERSION = 2
ATTENTION_STATES = {'deferred', 'partially_deleted', 'failed', 'moved_unconfirmed', 'purge_partial',
                    'tombstone_partial'}


def load_config(path: Path) -> dict:
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('schema_version') != SCHEMA_VERSION:
        raise ValueError('config schema_version must be 2; schema 1 is the retired destructive format')
    return data


def write_report(report: dict, destination: Path | None) -> None:
    payload = json.dumps(report, indent=2, sort_keys=True) + '\n'
    if destination is not None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + '.tmp')
        temporary.write_text(payload, encoding='utf-8')
        temporary.replace(destination)
    sys.stdout.write(payload)


def volume_paths(config: dict) -> list[Path]:
    paths = reclaim.roots(config.get('reclaim', {}))
    if 'recoverable' in config:
        paths.append(Path(config['recoverable']['quarantine_root']))
    return paths or [Path.home()]


def needs_attention(report: dict) -> bool:
    rows = report.get('reclaim', {}).get('entries', []) + report.get('recoverable', {}).get('entries', []) \
        + report.get('recoverable', {}).get('purge', [])
    return bool(report.get('discovery', {}).get('alerts')) or any(r.get('state') in ATTENTION_STATES for r in rows)


def summarize(report: dict) -> dict:
    reclaim_totals = report.get('reclaim', {}).get('totals', {})
    purge = report.get('recoverable', {}).get('purge', [])
    return {
        'deleted_allocated_bytes': reclaim_totals.get('deleted_allocated_bytes', 0),
        'eligible_allocated_bytes': reclaim_totals.get('eligible_allocated_bytes', 0),
        'quarantined_entries': sum(1 for r in report.get('recoverable', {}).get('entries', []) if r.get('state') == 'quarantined'),
        'purged_allocated_bytes': sum(r.get('allocated_bytes', 0) for r in purge if r.get('state') == 'purged'),
        'df_freed_bytes': report.get('df_freed_bytes'),
        'alerts': len(report.get('discovery', {}).get('alerts', [])),
    }


def execute(config: dict, *, apply: bool, discover_only: bool, restore: Path | None) -> dict:
    report: dict = {'schema_version': SCHEMA_VERSION, 'started_at_epoch': int(time.time()),
                    'mode': 'restore' if restore else 'discover' if discover_only else 'apply' if apply else 'dry_run'}
    if restore is not None:
        report['recoverable'] = recoverable_cleanup.run(config['recoverable'], restore_path=restore)
        return report
    volumes = volume_paths(config)
    report['volumes_before'] = common.volume_free(volumes)
    if 'discovery' in config:
        report['discovery'] = discovery.run(config['discovery'])
    if not discover_only:
        if 'reclaim' in config:
            report['reclaim'] = reclaim.run(config['reclaim'], apply=apply)
        if 'recoverable' in config:
            report['recoverable'] = recoverable_cleanup.run(config['recoverable'], apply=apply)
    report['volumes_after'] = common.volume_free(volumes)
    report['df_freed_bytes'] = common.freed(report['volumes_before'], report['volumes_after'])
    report['summary'] = summarize(report)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--config', type=Path, required=True)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--discover', action='store_true', help='read-only inventory and growth alerts only')
    modes.add_argument('--apply', action='store_true', help='delete tier A, quarantine tier B, purge expired')
    modes.add_argument('--restore', type=Path, help='restore one quarantine manifest')
    parser.add_argument('--report', type=Path)
    parser.add_argument('--lock', type=Path, default=Path('/private/tmp/workspace-cleanup.lock'))
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
    except (OSError, ValueError) as error:
        print(f'Cleanup refused: {error}', file=sys.stderr)
        return 2
    args.lock.parent.mkdir(parents=True, exist_ok=True)
    with args.lock.open('w', encoding='utf-8') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('cleanup already running', file=sys.stderr)
            return 2
        try:
            report = execute(config, apply=args.apply, discover_only=args.discover, restore=args.restore)
        except Exception as error:  # the report must exist even when the run fails
            report = {'schema_version': SCHEMA_VERSION, 'status': 'failed', 'error': str(error),
                      'traceback': traceback.format_exc(limit=5)}
            write_report(report, args.report)
            return 1
        report['status'] = 'attention' if needs_attention(report) else 'clean'
        write_report(report, args.report)
    return 3 if report['status'] == 'attention' else 0


if __name__ == '__main__':
    raise SystemExit(main())
