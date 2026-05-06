# XUUnity Light Unity MCP Current State Summary

Date: `2026-05-05`
Status: `public current-state summary`

## Scope

This summary captures the current reusable state of the lightweight Unity MCP
service after the latest validation and documentation refresh.

## Current State

The service is now beyond the design-only stage and should be treated as a
working validation-focused MCP lane.

Current reusable surface includes:

- host-side stdio MCP server scaffold
- editor-only Unity bridge package
- capability probing and operation gating
- compile validation
- EditMode test execution
- play mode control
- Game View configure and screenshot
- asynchronous scenario validation, run, and result retrieval
- public reusable smoke runners
- host-side editor-state restore for host-opened validation sessions

## Current Strengths

- small editor-only footprint
- no default player-build contamination
- explicit capability-gated behavior for version-sensitive operations
- stronger lifecycle evidence through bridge session/generation state
- Unity-side settle watchers for refresh, compile, and play mode transitions
- public-safe reusable smoke assets under `templates/scenarios/` and `templates/smoke/`

## Current Operational Contract

The intended operational model is:

1. host process exposes MCP
2. Unity package executes editor operations
3. host wrapper owns editor startup, readiness, retries, and closeout
4. if the host opened Unity only for validation, the host restores the original
   closed state on exit

## Current Limits

This is still not the final target for:

- broad multi-client production proof
- wide host-matrix proof
- runtime diagnostics companion
- device automation and profiling
- deeper project inspection surface
- richer scenario assertions and result utilities

## Residual Engineering Risks

Still worth tracking:

- host `server.py` still carries too much ownership in one file
- editor-session resolution is materially better but still wants a cleaner
  single-owner host-side session model
- proof across more clients, more hosts, and more consumer projects is still
  thinner than the final reusable-baseline target

## Recommended Interpretation

Treat the service as:

- ready for controlled Unity-aware validation work
- not yet the final form of a broad autonomous Unity automation platform

## Canonical References

- `../README.md`
- `../DESIGN.md`
- `../AI_INTEGRATION.md`
- `../SMOKE_TESTS.md`
- `../ROADMAP.md`
