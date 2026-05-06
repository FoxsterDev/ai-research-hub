# XUUnity Light Unity MCP Roadmap Baseline

Date: `2026-05-05`
Status: `public baseline report`

## Scope

This report captures the current roadmap shape for the reusable lightweight
Unity MCP effort.

## North Star

Support an autonomous Unity engineering loop that can:

1. inspect project state
2. validate compile and tests
3. drive deterministic play-mode scenarios
4. capture screenshots, logs, and profiler evidence
5. correlate evidence back to code and assets
6. support agent-driven diagnosis

## Roadmap Waves

### Wave 1

Harden the core:

- stable stdio behavior
- structured errors
- request hygiene
- artifact manifests
- multi-client validation

### Wave 2

Expand the read surface:

- asset read/search
- prefab and hierarchy snapshots
- package and define inspection

### Wave 3

Add scenario automation:

- scenario definitions
- scenario execution
- persisted scenario result bundles

### Wave 4

Add optional runtime diagnostics companion:

- frame timing
- memory sampling
- runtime breadcrumbs

### Wave 5

Add device and profiler automation:

- deploy and launch
- device screenshots
- runtime logs
- profiler capture export

### Wave 6

Add analysis layer:

- profiler summary extraction
- bottleneck ranking
- code and asset suspect sets

### Wave 7

Add autonomous CUA support:

- resumable workflows
- long-running session control
- policy bands
- safe handoff and recovery

## Current Best Next Step

The most important next milestone is:

- richer scenario assertions, result utilities, and broader cross-client proof

Reason:

- the base scenario control plane already exists
- the highest remaining leverage is trust, evidence quality, and reuse across consumers

## Canonical Source

For the full current roadmap, use:

- `../ROADMAP.md`
