"""Shared read-only probes for workspace cleanup: processes, sizes, Git, broker, volumes."""
from __future__ import annotations

import contextlib
import fcntl
import json
import os
import re
import stat
import subprocess
from pathlib import Path
from typing import Iterable, Sequence

PROTECTED_SUFFIXES = ('.xcresult', '.xcarchive', '.ipa')
UNITY_VERSION_PATTERN = re.compile(r'^m_EditorVersion:\s*\S+', re.MULTILINE)


class Deferred(RuntimeError):
    """Preserve this candidate when ownership, activity or recovery is uncertain."""


def canonical(path) -> Path:
    if not isinstance(path, (str, os.PathLike)) or not os.path.isabs(path):
        raise Deferred('path must be an explicit absolute filesystem path')
    path = Path(os.path.abspath(path))
    if any(p.is_symlink() for p in [path, *path.parents]) or path.resolve() != path:
        raise Deferred(f'non-canonical or symlink path: {path}')
    return path


def within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def is_unity_project(project_root: Path) -> bool:
    assets = project_root / 'Assets'
    files = [project_root / 'Packages' / 'manifest.json',
             project_root / 'ProjectSettings' / 'ProjectSettings.asset',
             project_root / 'ProjectSettings' / 'ProjectVersion.txt']
    if not assets.is_dir() or assets.is_symlink() or not all(p.is_file() and not p.is_symlink() for p in files):
        return False
    try:
        return bool(UNITY_VERSION_PATTERN.search(files[2].read_text(encoding='utf-8')))
    except (OSError, UnicodeError):
        return False


def is_xcode_derived_data(path: Path) -> bool:
    if 'DerivedData' not in path.name:
        return False
    try:
        names = set(os.listdir(path))
    except OSError:
        return False
    return bool(names & {'Build', 'SourcePackages', 'Index.noindex', 'ModuleCache.noindex'})


def tree_stats(path: Path, protected_suffixes: Sequence[str] = PROTECTED_SUFFIXES) -> dict:
    """Metadata-only walk: logical and allocated bytes, newest mtime, protected hits, errors."""
    stats = {'logical_bytes': 0, 'allocated_bytes': 0, 'entries': 0, 'newest_mtime': 0.0,
             'protected': [], 'errors': []}
    seen: set[tuple[int, int]] = set()

    def account(item: str, info: os.stat_result) -> None:
        if info.st_nlink > 1 and not stat.S_ISDIR(info.st_mode):
            key = (info.st_dev, info.st_ino)
            if key in seen:
                return
            seen.add(key)
        stats['entries'] += 1
        stats['logical_bytes'] += info.st_size if stat.S_ISREG(info.st_mode) else 0
        stats['allocated_bytes'] += info.st_blocks * 512
        stats['newest_mtime'] = max(stats['newest_mtime'], info.st_mtime)
        if item.lower().endswith(tuple(protected_suffixes)) and len(stats['protected']) < 5:
            stats['protected'].append(item)

    try:
        account(str(path), os.lstat(path))
    except OSError as error:
        stats['errors'].append(str(error))
        return stats
    if not stat.S_ISDIR(os.lstat(path).st_mode):
        return stats
    for root, dirs, files in os.walk(path, followlinks=False,
                                     onerror=lambda e: stats['errors'].append(f'{e.filename}: {e.strerror}')):
        for name in dirs + files:
            item = os.path.join(root, name)
            try:
                account(item, os.lstat(item))
            except OSError as error:
                stats['errors'].append(f'{item}: {error.strerror}')
    return stats


def process_table() -> list[tuple[str, str]]:
    """(executable basename, full argv) for every process, joined by pid."""
    def listing(field: str) -> dict[int, str]:
        output = subprocess.run(['ps', '-axww', '-o', f'pid=,{field}='], check=True,
                                capture_output=True, text=True, timeout=15).stdout
        rows = {}
        for line in output.splitlines():
            pid, _, value = line.strip().partition(' ')
            if pid.isdigit():
                rows[int(pid)] = value.strip()
        return rows
    comm, args = listing('comm'), listing('args')
    return [(os.path.basename(comm[pid]), args.get(pid, '')) for pid in comm]


def blocking(table: Iterable[tuple[str, str]], executables: Iterable[str]) -> list[str]:
    wanted = set(executables)
    return sorted({exe for exe, _args in table if exe in wanted})


def path_aliases(path: Path) -> set[str]:
    aliases = {str(path)}
    for prefix in ('/private/tmp/', '/private/var/', '/private/etc/'):
        if str(path).startswith(prefix):
            aliases.add(str(path)[len('/private'):])
    return aliases


def referencing(table: Iterable[tuple[str, str]], path: Path) -> bool:
    aliases = path_aliases(path)
    return any(alias in args for _exe, args in table for alias in aliases)


def open_paths(timeout: int = 120) -> list[str]:
    """Every open file path on the host, or Deferred when the inventory is unavailable."""
    try:
        result = subprocess.run(['/usr/sbin/lsof', '-nP', '-Fn'], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        raise Deferred('open-file inventory timed out') from error
    if result.returncode not in (0, 1):
        raise Deferred('open-file inventory unavailable')
    return [line[1:] for line in result.stdout.splitlines() if line.startswith('n/')]


def has_open_file(paths: Iterable[str], target: Path) -> bool:
    aliases = tuple(alias.rstrip('/') + '/' for alias in path_aliases(target))
    exact = path_aliases(target)
    return any(p in exact or p.startswith(aliases) for p in paths)


def git_tracked_inside(path: Path) -> bool:
    top = subprocess.run(['git', '-c', 'core.fsmonitor=false', '-C', str(path.parent), 'rev-parse', '--show-toplevel'],
                         capture_output=True, text=True, timeout=15)
    if top.returncode:
        if 'not a git repository' in top.stderr:
            return False
        raise Deferred('Git ownership inventory unavailable')
    repository = Path(top.stdout.strip()).resolve()
    try:
        relative = path.resolve().relative_to(repository)
    except ValueError:
        return False
    tracked = subprocess.run(['git', '-c', 'core.fsmonitor=false', '-C', str(repository), 'ls-files', '--', str(relative)],
                             capture_output=True, text=True, timeout=30)
    if tracked.returncode:
        raise Deferred('Git ownership inventory unavailable')
    return bool(tracked.stdout.strip())


def contains_dirty_git(path: Path) -> bool:
    roots = []
    for root, dirs, files in os.walk(path, followlinks=False):
        if '.git' in dirs or '.git' in files:
            roots.append(root)
        if '.git' in dirs:
            dirs.remove('.git')
    for root in roots:
        status = subprocess.run(['git', '-c', 'core.fsmonitor=false', '-C', root, 'status', '--porcelain'],
                                capture_output=True, text=True, timeout=60)
        if status.returncode or status.stdout.strip():
            return True
    return False


@contextlib.contextmanager
def broker_idle(state_dir: str | None, table: Sequence[tuple[str, str]]):
    """Hold every broker capacity slot, or prove the broker is absent. Yields 'held' or 'absent'."""
    if not state_dir:
        yield 'not-configured'
        return
    state = Path(state_dir)
    if not state.exists():
        if any('simulator_broker' in args for _exe, args in table):
            raise Deferred('broker process running without its state directory')
        yield 'absent'
        return
    contract_path = state / 'contract.json'
    try:
        contract = json.loads(contract_path.read_text())
    except (OSError, ValueError) as error:
        raise Deferred(f'broker contract unreadable: {error}') from error
    capacity = contract.get('capacity')
    if contract.get('schemaVersion') != 1 or contract.get('contractVersion') != 1 or not isinstance(capacity, int) or capacity < 1:
        raise Deferred('unsupported broker contract')
    handles = []
    try:
        for slot in range(capacity):
            handle = canonical(state.resolve() / 'capacity' / f'slot-{slot}.lock').open('r+')
            handles.append(handle)
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise Deferred('active broker lease') from error
        yield 'held'
    finally:
        for handle in handles:
            handle.close()


def volume_free(paths: Iterable[Path]) -> dict[str, dict]:
    """Available bytes per device (statvfs f_bavail, the same figure df reports)."""
    result: dict[str, dict] = {}
    for path in paths:
        probe = Path(path)
        while not probe.exists() and probe != probe.parent:
            probe = probe.parent
        try:
            device = str(probe.stat().st_dev)
            if device in result:
                continue
            info = os.statvfs(probe)
            result[device] = {'probe': str(probe), 'available_bytes': info.f_bavail * info.f_frsize}
        except OSError:
            continue
    return result


def freed(before: dict[str, dict], after: dict[str, dict]) -> dict[str, int]:
    return {device: after[device]['available_bytes'] - info['available_bytes']
            for device, info in before.items() if device in after}
