# Workspace Cleanup

`workspace_cleanup.py` removes only regenerable developer artifacts declared by
an explicit JSON configuration. The reusable engine is public and contains no
host paths. Each installation keeps its paths and retention choices in a private
configuration.

The default mode is a dry run:

```bash
python3 Operations/WorkspaceCleanup/workspace_cleanup.py \
  --config /path/to/host-cleanup.json
```

Deletion requires `--apply`. The tool keeps configured roots, rejects a root as
a deletion candidate, never follows symlinks, refuses Unity Library cleanup while
the Unity Editor is running, and refuses DerivedData or simulator cleanup while
Xcode, xcodebuild, or Simulator is active. Simulator `erase_all` shuts down
devices and erases their data while preserving installed runtimes and device
definitions.

Supported configuration sections are:

- `temporary`: age-gated top-level prefixes under one scratch root;
- `scratch`: age-gated children under explicit scratch directories;
- `unity`: discovery and removal of `Library` beside a real
  `ProjectSettings/ProjectVersion.txt`;
- `xcode`: removal of children under an explicit DerivedData root;
- `simulator`: `off`, `report`, `erase_all`, or `delete_all`;
- `model_fitness`: age-gated removal of named generated workspace/cache
  directories while preserving transcripts and receipts;
- `audit_only_paths`: paths whose size is reported and never deleted.

Run the tests with:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s Operations/WorkspaceCleanup/tests
```
