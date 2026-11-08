# Workspace Cleanup

Host-agnostic engine for keeping developer caches bounded. Host paths and
retention choices live in a private JSON config (`schema_version: 2`); this
directory contains no host data.

## Modes

```sh
python3 workspace_cleanup.py --config host.json --report run.json            # dry run (default)
python3 workspace_cleanup.py --config host.json --report run.json --discover # inventory only
python3 workspace_cleanup.py --config host.json --report run.json --apply
python3 workspace_cleanup.py --config host.json --report run.json --restore <quarantine>/<slot>/manifest.json
```

Every run records `volumes_before`, `volumes_after` and `df_freed_bytes`
(statvfs available bytes, the figure `df` shows). Per-path sizes are allocated
blocks (`st_blocks`), with hardlinks counted once. APFS clones share blocks that
no tool can attribute, so only the `df` delta proves reclaimed space.

Exit codes: `0` clean, `3` needs attention (deferral, partial delete, unconfirmed
move, discovery alert), `1` failure (a report is still written), `2` refused
(bad/retired config, another run holds the lock). Schema 1 configs are refused.

## Sections

`discovery` (read-only, never mutates): finds Xcode DerivedData by content
(any directory whose name contains `DerivedData` and that holds `Build`,
`SourcePackages`, `Index.noindex` or `ModuleCache.noindex`), verified Unity
`Library` folders, and `watch` paths (optionally per child). Items under
`evidence_names` folders are flagged. Sizes are stored in `state_path`; alerts
fire for growth over `growth_alert_bytes`, a new item over
`new_item_alert_bytes`, or growth of a `personal: true` watch path over
`personal_growth_alert_bytes`. Personal paths are never cleanup candidates.

`reclaim` (tier A, real deletion of regenerable data). Each rule has:

- `roots` with `targets` globs, or `scan_roots` + `container_kind`
  (`xcode_derived_data`, `unity_library`, `named` + `container_names`) with
  `targets` relative to each container (`.` is the container itself);
- `minimum_age_hours` (>= 24), checked against the newest descendant mtime;
- optional `name_prefixes`, `block_executables` (matched against process
  executable names, never argument text), `ignore_reference_from` (executable
  names whose command lines merely list paths, such as a launcher's recent
  projects), `exclude_names` (globs on the target name), `require_owner`
  (only entries owned by the running user), `skip_dirty_git`,
  `require_unity_project`, `forbid_suffixes`, `use_broker`.

For `unity_library` containers the live-reference check uses the project root,
so an editor opened with `-projectPath <project>` keeps only that project's
Library, while other idle projects stay eligible.

A target is deleted only if it is canonical (no symlinks), outside
`protected_paths`, fully readable, free of `.xcresult/.xcarchive/.ipa`, stale,
untracked by Git, not referenced by a live process command line (target or its
container), and has no open files (one host-wide `lsof` per rule). With
`use_broker`, every Simulator broker capacity slot is held during deletion; a
held slot or an unreadable contract defers the rule, and a missing broker state
directory counts as absent only when no broker process is running. Deletion
renames to a sibling `.reclaim-*` tombstone first; partial failures are reported
and later runs finish them.

`recoverable` (tier B): exact allowlist, reviewed ownership bindings,
content-fingerprinted move into a private same-volume quarantine, restore.
`quarantine_ttl_hours` (>= 24) enables purge: a payload whose manifest is
`quarantined` (or a moved-but-unconfirmed intent) is deleted after the TTL only
if its fingerprint is unchanged. Failed moves mark the manifest `aborted`;
failures after the rename report `moved_unconfirmed` instead of `deferred`.
`max_inventory_entries` / `max_inventory_bytes` bound fingerprinting.

## Tests

Disposable fixtures and mocked process/open-file inventories only:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s Operations/WorkspaceCleanup/tests
```
