# XUUnity Light Unity MCP Protocol Integration Status

Date: `2026-05-05`
Status: `public progress report`

## Scope

This report tracks the current state of integrating the lightweight Unity MCP
into the reusable `xuunity` protocol surface rather than into a single consumer
project.

## Current Public Position

The service is now documented as:

- reusable
- public-safe
- multi-repo friendly
- agent-agnostic

Public continuation and integration files now exist in:

- `../README.md`
- `../CONTINUATION.md`
- `../AI_INTEGRATION.md`
- `../ROADMAP.md`
- `../Reports/`

## What Is Already In Place

- public design baseline
- public roadmap baseline
- public progress baseline
- agent-agnostic integration guidance
- GitHub package install path
- explicit `devmode` and `prodmode` package-source switching on the host wrapper
- package metadata for external consumption
- first scenario automation layer
- public reusable smoke runners
- validated host-side editor-state restore for host-opened validation runs

## What Still Needs To Happen For `xuunity`

The next `xuunity`-side integration steps are:

1. define the canonical `xuunity` task entrypoints for scenario automation
2. define when `xuunity` should prefer:
   - shell compile
   - direct MCP validation
   - scenario automation
3. add reusable `xuunity` operation recipes for:
   - validation after code changes
   - screenshot capture
   - play-mode smoke
   - scenario replay
4. add protocol-level guidance for capability probe interpretation
5. add project-routing guidance for multi-project hosts
6. add protocol-level closeout guidance for host-opened Unity sessions

## Immediate Next Work For A New Chat

1. add richer scenario steps and richer assertions
2. add scenario result utilities and artifact surfacing
3. broaden public smoke proof across more consumers and clients
4. continue wiring scenario guidance into the shared `xuunity` protocol layer

## Key Non-Goal

Do not let `xuunity` depend on consumer-specific paths, naming, or repo
assumptions.

This MCP should remain reusable across multiple repos and multiple Unity
projects.
