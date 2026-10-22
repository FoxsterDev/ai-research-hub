# Workspace Cleanup

The installed command now defaults to inventory. `--apply` requires an explicit
`recoverable` policy and only moves approved stale cache directories into a
private, same-volume quarantine. Legacy destructive apply is refused. No
Simulator reset, permanent deletion, quarantine expiry or Trash emptying occurs.
The older discovery helpers remain available for read-only inventory; their
legacy mutation functions are not reachable from the CLI.

## Recoverable policy

The private host config uses schema_version1 and a recoverable object:

```json
{
  "schema_version": 1,
  "recoverable": {
    "allowed_roots": ["/physical/approved/cache/root"],
    "allowlist": [{"path": "/physical/approved/cache/root/ModuleCache.noindex", "category": "xcode_derived_data", "minimum_age_hours": 168}],
    "protected_paths": ["/physical/retained/evidence"],
    "quarantine_root": "/physical/private/quarantine",
    "broker_state_dir": "/physical/existing/broker/state",
    "ownership_snapshot": "/physical/fresh-supported-task-inventory.json",
    "maintenance_thread_id": "current-maintenance-thread"
  }
}
```

Use resolved physical paths without symlink components. Quarantine must already
exist, belong to the current user and have mode0700. The allowlist is exact, not
a wildcard. Only independently established regenerable caches belong there.
Unknown/mixed directories remain deferred. A named root is not approval for all
its children. DerivedData is limited to Index.noindex, ModuleCache.noindex,
CompilationCache.noindex and Intermediates.noindex; keep Products and signed
candidates. Retention is at least168h for DerivedData/scratch and72h otherwise,
including newest descendant mtime, not only the parent directory timestamp.

Before each invocation obtain current task state through supported host tools,
not session databases. Save a fresh owner inventory with observed_at (Unix
seconds), coverage="complete", maintenance_thread_id, active_tasks (objects with
id), unavailable_hosts and unavailable_sources. Include local/cloud tasks able
to use this Mac. The engine rejects active tasks other than this maintenance
thread, unavailable coverage, or an inventory older than120seconds. This is a
caller observation, not an authorization or a transactional producer lock.
Do not mark incomplete inventories complete. Refresh between bounded batches.

The engine holds both existing Simulator broker capacity locks across each
move/restore, checks process and open-file inventories immediately before action,
rechecks content identity and retains a durable intent before atomic exclusive
rename. It never creates a replacement broker pool or lowers its capacity.
A cooperating local/cloud broker job cannot enter during the move. An unrelated
manual process does not honor these locks: observed activity blocks the operation,
but these checks do not promise a universal race-free exclusion of arbitrary
future manual starts. Do not move a cache with uncertain ownership.

Hard protections include nested repositories, tracked paths, symlinks/hardlinks,
.xcresult/.xcarchive/.app bundles, evidence/screenshots/Archives/Logs directories,
release archives, and explicit protected-path overlaps. Images/video are kept.
These guards do not identify arbitrary unique evidence by filename: the exact
allowlist review must establish cache provenance. Any uncertainty defers the
whole category for the current run; it does not permit broader fallback deletion.

## Run and restore

```sh
python3 workspace_cleanup.py --config /path/to/policy.json --report /path/to/fresh-dry-run.json
python3 workspace_cleanup.py --config /path/to/policy.json --apply --report /path/to/fresh-apply.json
python3 workspace_cleanup.py --config /path/to/policy.json --restore /path/to/quarantine/entry/manifest.json --report /path/to/fresh-restore.json
```

Read exit status and this run's fresh receipt. Missing/stale receipts are failures.
A defer is not successful cleanup. Moving on the same volume does not free disk
space: report bytes quarantined, never bytes reclaimed. No automatic purge exists.

A manifest records original path, payload path and fingerprint before rename.
If the final journal write fails, the intent remains usable for restore. Restore
requires the payload fingerprint, idle guards and original parent; it refuses to
overwrite any newly created original path. On collision or changed payload leave
both copies intact and request an exact owner decision. Never delete the new
copy to force restoration. This supports normal CLI restoration, not Finder Trash.

Run tests (only disposable fixtures and mocked Simulator commands):

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s Operations/WorkspaceCleanup/tests
```
