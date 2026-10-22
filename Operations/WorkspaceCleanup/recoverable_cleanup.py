"""Exact-allowlist cache quarantine. No deletion, Simulator mutation or expiry."""
from __future__ import annotations
import contextlib
import ctypes
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import time
import uuid

class Deferred(RuntimeError):
    """Preserve the category when ownership or recovery is uncertain."""

PROTECTED = {'.git', 'archives', 'evidence', 'screenshots', 'logs', 'test', 'tests',
             '_codesignature', 'release', 'receipts'}
SUFFIXES = {'.xcresult', '.xcarchive', '.app', '.ipa', '.zip', '.png', '.jpg',
            '.jpeg', '.heic', '.mov', '.mp4'}
BUILD = re.compile(r'(?:^|[/\s])(?:Xcode|xcodebuild|xctest|Unity|Simulator|clang(?:\+\+)?|'
                   r'swiftc|swift-frontend|XCBBuildService|ibtoold|actool)(?:\s|$)')
CATEGORIES = {'temporary', 'scratch', 'unity_library', 'xcode_derived_data', 'model_fitness_workspace'}

def canonical(path):
    path = Path(os.path.abspath(path))
    if any(p.is_symlink() for p in [path, *path.parents]) or path.resolve() != path:
        raise Deferred(f'non-canonical or symlink path: {path}')
    return path

def within(path, root):
    return path == root or root in path.parents

def snapshot(path, protected=(), minimum_age_hours=0):
    canonical(path)
    if any(within(path, p) or within(p, path) for p in protected):
        raise Deferred(f'protected path overlap: {path}')
    for ancestor in path.parents:
        if ancestor.name.lower() in PROTECTED - {'release'} or ancestor.suffix.lower() in SUFFIXES:
            raise Deferred(f'protected ancestor: {ancestor}')
    if not path.is_dir():
        raise Deferred(f'not a cache directory: {path}')
    digest = hashlib.sha256()
    total = count = 0
    newest = 0.0
    def unreadable(error):
        raise Deferred(f'unreadable subtree: {error.filename}') from error
    for root, dirs, files in os.walk(path, followlinks=False, onerror=unreadable):
        for name in ['.', *sorted(dirs), *sorted(files)]:
            item = Path(root) if name == '.' else Path(root) / name
            if item.name.lower() in PROTECTED or item.suffix.lower() in SUFFIXES:
                raise Deferred(f'protected artifact: {item}')
            s = item.lstat()
            if not (stat.S_ISDIR(s.st_mode) or stat.S_ISREG(s.st_mode)):
                raise Deferred(f'link or special file: {item}')
            if stat.S_ISREG(s.st_mode) and s.st_nlink != 1:
                raise Deferred(f'hardlinked file: {item}')
            count += 1
            if count > 100000:
                raise Deferred('inventory exceeds bounded entry budget')
            newest = max(newest, s.st_mtime)
            signature = [str(item.relative_to(path)), s.st_dev, s.st_ino, s.st_mode,
                         s.st_size if item.is_file() else 0, s.st_mtime_ns]
            # Root ctime changes on rename; retain descendant and content identity.
            if item != path:
                signature.append(s.st_ctime_ns)
            digest.update(json.dumps(signature).encode())
            if item.is_file():
                total += s.st_size
                if total > 5 * 1024**3:
                    raise Deferred('inventory exceeds 5GiB per-candidate budget')
                with item.open('rb') as source:
                    for chunk in iter(lambda: source.read(1024 * 1024), b''):
                        digest.update(chunk)
                after = item.lstat()
                if (after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns) != (s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns):
                    raise Deferred(f'changed during inventory: {item}')
    if time.time() - newest < minimum_age_hours * 3600:
        raise Deferred('candidate or descendant is inside retention window')
    return {'sha256': digest.hexdigest(), 'bytes': total, 'entries': count}

def fsync_directory(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_json(path, value):
    temporary = path.with_name('.' + path.name + '.' + uuid.uuid4().hex)
    with temporary.open('x') as output:
        json.dump(value, output, indent=2)
        output.write('\n')
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)
    fsync_directory(path.parent)

def rename_exclusive(source, destination):
    # macOS renamex_np(RENAME_EXCL), verified in SDK sys/stdio.h; no copy fallback.
    libc = ctypes.CDLL(None, use_errno=True)
    rename = getattr(libc, 'renamex_np', None)
    if rename is None:
        raise Deferred('atomic no-replace rename unavailable')
    rename.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(os.fsencode(source), os.fsencode(destination), 4) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), str(source))

def owners_idle(policy):
    data = json.loads(canonical(policy['ownership_snapshot']).read_text())
    age = time.time() - float(data['observed_at'])
    if not math.isfinite(age) or age < 0 or age > 120 or data.get('coverage') != 'complete':
        raise Deferred('owner inventory must be complete and fresh (120s maximum)')
    if data.get('unavailable_hosts') or data.get('unavailable_sources'):
        raise Deferred('owner inventory has unavailable hosts or sources')
    if data.get('maintenance_thread_id') != policy['maintenance_thread_id']:
        raise Deferred('maintenance owner mismatch')
    for task in data['active_tasks']:
        if task['id'] != policy['maintenance_thread_id']:
            raise Deferred(f"active local/cloud task: {task['id']}")

def process_idle(path):
    commands = subprocess.run(['ps', '-axo', 'command='], check=True, capture_output=True, text=True, timeout=15).stdout
    aliases = {str(path)}
    for prefix in ('/private/tmp/', '/private/var/', '/private/etc/'):
        if str(path).startswith(prefix):
            aliases.add(str(path)[len('/private'):])
    if any(alias in commands for alias in aliases):
        raise Deferred('live process command references candidate')
    if any(BUILD.search(line) for line in commands.splitlines()):
        raise Deferred('active build/test/editor/Simulator process')
    result = subprocess.run(['/usr/sbin/lsof', '-nP', '+D', str(path)], capture_output=True, text=True, timeout=30)
    if result.returncode not in (0, 1) or result.stderr.strip():
        raise Deferred('open-file inventory unavailable')
    if result.stdout.strip():
        raise Deferred('candidate has open files')

@contextlib.contextmanager
def idle_lease(policy, path):
    state = canonical(policy['broker_state_dir'])
    contract = json.loads((state / 'contract.json').read_text())
    if contract.get('schemaVersion') != 1 or contract.get('contractVersion') != 1 or contract.get('capacity') != 2:
        raise Deferred('unsupported broker contract')
    handles = []
    try:
        for slot in range(2):
            h = canonical(state / 'capacity' / f'slot-{slot}.lock').open('r+')
            handles.append(h)
            try:
                fcntl.flock(h, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise Deferred('active local/cloud broker lease') from error
        owners_idle(policy)
        process_idle(path)
        yield
    finally:
        for h in handles:
            h.close()

def git_untracked(path):
    result = subprocess.run(['git', '-c', 'core.fsmonitor=false', '-C', str(path.parent),
                             'rev-parse', '--show-toplevel'], capture_output=True, text=True, timeout=15)
    if result.returncode:
        if 'not a git repository' in result.stderr:
            return
        raise Deferred('Git ownership inventory unavailable')
    repository = Path(result.stdout.strip())
    relative = path.relative_to(repository)
    tracked = subprocess.run(['git', '-c', 'core.fsmonitor=false', '-C', str(repository),
                              'ls-files', '--', str(relative)], check=True, capture_output=True, text=True, timeout=15)
    if tracked.stdout.strip():
        raise Deferred('tracked source or evidence inside candidate')


def eligible(entry, policy):
    path = canonical(entry['path'])
    category = entry['category']
    if category not in CATEGORIES:
        raise Deferred('unknown category')
    minimum = float(entry.get('minimum_age_hours', 168))
    if not math.isfinite(minimum) or minimum < (168 if category in {'scratch', 'xcode_derived_data'} else 72):
        raise Deferred('retention below minimum')
    roots = [canonical(p) for p in policy['allowed_roots']]
    if not any(path != p and within(path, p) for p in roots):
        raise Deferred('candidate outside strict allowed roots')
    if category == 'xcode_derived_data' and path.name not in {
            'Index.noindex', 'ModuleCache.noindex', 'CompilationCache.noindex', 'Intermediates.noindex'}:
        raise Deferred('only bounded regenerable DerivedData subdirectories are eligible')
    if category == 'unity_library':
        from workspace_cleanup import _is_unity_project
        if path.name != 'Library' or not _is_unity_project(path.parent):
            raise Deferred('Unity Library requires verified project identity')
    if category == 'model_fitness_workspace' and path.name not in {
            'compile-tree', 'final-tree', 'prepared', 'treatment-fixture', 'workspaces',
            'Library', 'Temp', 'Logs', 'Obj', '__pycache__'}:
        raise Deferred('not an allowlisted generated model-fitness directory name')
    return path, minimum, [canonical(p) for p in policy.get('protected_paths', [])]

def quarantine(entry, policy, apply):
    path, minimum, protected = eligible(entry, policy)
    git_untracked(path)
    before = snapshot(path, protected, minimum)
    result = {'path': str(path), 'category': entry['category'], **before, 'state': 'eligible'}
    with idle_lease(policy, path):
        if snapshot(path, protected, minimum) != before:
            raise Deferred('candidate changed after inventory')
        if not apply:
            return result
        root = canonical(policy['quarantine_root'])
        if not root.is_dir() or root.stat().st_uid != os.getuid() or root.stat().st_mode & 0o077:
            raise Deferred('quarantine must exist with owner-only permissions')
        if within(root, path) or within(path, root) or root.stat().st_dev != path.stat().st_dev:
            raise Deferred('quarantine overlaps source or is on a different filesystem')
        slot = root / uuid.uuid4().hex
        slot.mkdir(mode=0o700)
        fsync_directory(root)
        destination, receipt = slot / 'payload', slot / 'manifest.json'
        record = {'schema_version': 1, 'source': str(path), 'destination': str(destination),
                  'snapshot': before, 'state': 'intent', 'created_at': time.time()}
        write_json(receipt, record)
        owners_idle(policy)
        process_idle(path)
        if snapshot(path, protected, minimum) != before:
            raise Deferred('candidate changed immediately before move')
        git_untracked(path)
        process_idle(path)
        owners_idle(policy)
        try:
            rename_exclusive(path, destination)
            fsync_directory(path.parent)
            fsync_directory(destination.parent)
            if snapshot(destination) != before:
                raise Deferred('post-move content changed')
            record['state'] = 'quarantined'
            write_json(receipt, record)
        except (OSError, Deferred) as error:
            raise Deferred(f'{error}; inspect durable recovery intent {receipt}') from error
        result.update(state='quarantined', manifest=str(receipt), destination=str(destination))
    return result

def restore(receipt, policy):
    root, receipt = canonical(policy['quarantine_root']), canonical(receipt)
    if receipt.name != 'manifest.json' or receipt.parent.parent != root:
        raise Deferred('receipt outside owned quarantine')
    record = json.loads(receipt.read_text())
    source, destination = canonical(record['source']), canonical(record['destination'])
    if destination != receipt.parent / 'payload' or source.exists():
        raise Deferred('restore collision or destination mismatch')
    if not source.parent.is_dir() or source.parent.stat().st_dev != destination.stat().st_dev:
        raise Deferred('original parent missing or different filesystem')
    if not any(source != canonical(p) and within(source, canonical(p)) for p in policy['allowed_roots']):
        raise Deferred('restore source outside allowed roots')
    with idle_lease(policy, destination):
        if snapshot(destination) != record['snapshot']:
            raise Deferred('quarantine payload changed; inspect before restoring')
        process_idle(destination)
        owners_idle(policy)
        rename_exclusive(destination, source)
        fsync_directory(destination.parent)
        fsync_directory(source.parent)
        record['state'] = 'restored'
        write_json(receipt, record)
    return record

def run(policy, *, apply=False, restore_path=None):
    if restore_path is not None:
        return {'mode': 'restore', 'result': restore(restore_path, policy)}
    entries, deferred_categories = [], set()
    for entry in policy['allowlist']:
        category = entry.get('category', 'unknown')
        if category in deferred_categories:
            entries.append({**entry, 'state': 'deferred', 'reason': 'category already deferred'})
            continue
        try:
            entries.append(quarantine(entry, policy, apply))
        except (Deferred, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
            deferred_categories.add(category)
            entries.append({**entry, 'state': 'deferred', 'reason': str(error)})
    return {'mode': 'quarantine' if apply else 'dry_run', 'entries': entries,
            'deferred_categories': sorted(deferred_categories), 'permanent_deletion': False}
