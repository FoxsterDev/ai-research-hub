# Knowledge: File-IPC Atomicity (Polled Files Across Processes)

## When To Load
- two processes exchange state through polled files (heartbeat/state JSON, request/response directories, result files)
- a poller intermittently sees truncated/invalid JSON, or responses "disappear" into timeouts on Windows
- designing or reviewing a file-based bridge between an editor/tool process and a host process

## Rules
- Atomicity is a **writer+reader co-design**. Fixing only the writer or only the reader still loses data under version skew: old writers and new readers (and vice versa) coexist across releases, so the reader's tolerance is the compatibility layer.
- Writer: write a temp file **in the same directory**, then rename over the destination (`os.replace` / `File.Replace`+`File.Move`). Cross-directory temp breaks rename atomicity guarantees.
- The temp name must not match any reader's scan glob (`<name>.<uuid>.tmp` never matches `*.json`); otherwise scanners consume partial files by construction.
- Reader: a polled file that fails to open or parse (`OSError`, `ValueError` — covers JSON/Unicode decode and Windows `PermissionError`) is **mid-write, not garbage**. Leave it on disk and keep polling until the operation deadline.
- Reader deletes only after a successful parse. `finally: unlink()` around the read converts one torn read into a permanently lost response plus a full operation timeout.
- On Windows, rename-over can fail transiently while a poller briefly holds the destination open. Contention handling depends on the writer's thread:
  - host/daemon process: bounded sleep-retry, then direct-write fallback
  - UI/editor main thread: immediate retries only, then legacy in-place write — never sleep (see `skills/editor/tooling_design.md`, Background Service Loops)
- Funnel all polled-file writes through one publisher per language and enforce the single-call-site invariant with a contract test; ad-hoc direct writes reintroduce torn reads silently.

## What This Is Not
- Write-temp-then-rename is standard practice, not the contribution here. The durable content is the co-design: reader retry-until-deadline as the skew-compatibility layer, glob-safe temp naming, delete-after-parse, and the thread-context degradation ladder.
- Not a substitute for file locks or databases where multi-writer mutation is required; this pattern assumes one writer per file identity.

## Reference Implementation
`xuunity-mcp` repo — writer: `packages/com.xuunity.light-mcp/Editor/Core/XUUnityLightMcpAtomicFileWriter.cs` and `templates/server_core.py` (`write_json`); tolerant reader: `templates/server_bridge_transport.py` (`FileIpcBridgeTransport.invoke`) and `templates/server_bridge_final_status.py` (`try_take_recovered_response`); contract tests: `tests/test_atomic_ipc_contract.py`.

## Cross-Links
- `skills/editor/tooling_design.md` — Background Service Loops (why the editor-side writer must not wait)
- `knowledge/cross_platform_shell_portability.md` — helper subprocess and process-control discipline on the host side
