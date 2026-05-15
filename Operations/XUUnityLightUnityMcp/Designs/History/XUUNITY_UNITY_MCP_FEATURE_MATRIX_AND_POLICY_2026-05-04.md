# XUUnity Unity MCP Feature Matrix And Policy

Date: `2026-05-04`  
Status: `policy draft for adapter implementation`  
Primary backend context: `IvanMurzak/Unity-MCP`

## Purpose

This document translates the raw feature surface of `IvanMurzak/Unity-MCP` into an `xuunity` working policy:
- what should be used daily
- what should be allowed only with guardrails
- what should be disabled by default

The goal is not to maximize tool count.
The goal is to maximize `quality`, `trust`, and `operator confidence` for Unity work.

## Policy Bands

### Band A: Core daily path

Safe to expose as first-class `xuunity` operations.

### Band B: Guarded path

Useful, but should require stronger intent, clearer scoping, or extra validation.

### Band C: Disabled by default

Technically available, but too risky, too broad, or too unstable for normal `xuunity` operation.

## Matrix

| Feature area | Examples | Band | Why |
| --- | --- | --- | --- |
| Editor readiness and state | `editor-application-get-state`, connection status | A | High signal, low mutation, strong validation value |
| Console inspection | `console-get-logs`, `console-clear-logs` | A for read, C for clear | Log reading is core validation evidence; clearing logs destroys evidence |
| Scene snapshot and opened-scene inspection | `scene-get-data`, `scene-list-opened`, active scene state | A | Strong Unity-aware validation path with low blast radius |
| EditMode test execution | `tests-run` | A | Highest value validation operation for `xuunity` |
| Asset/project read operations | `assets-find`, `assets-get-data`, `package-list`, `package-search`, `script-read` | A | Good discovery surface with acceptable risk |
| Object/component read operations | `object-get-data`, `gameobject-find`, `gameobject-component-get`, `editor-selection-get` | A | Good inspection path for debugging and review |
| Screenshots | `screenshot-scene-view`, `screenshot-game-view`, `screenshot-camera` | B | Very useful, but visual evidence can be incomplete or misleading without context |
| Narrow scripted writes | `script-update-or-create`, `assets-create-folder`, `assets-refresh` | B | Useful for implementation, but must be paired with validation |
| Scene/object mutations | `gameobject-create`, `gameobject-modify`, `gameobject-component-add`, `set-parent`, prefab instantiate/save | B | Powerful, but easy to create noisy or partial changes |
| Asset mutations | `assets-modify`, `assets-move`, `assets-copy`, `assets-delete`, material/prefab creation | B/C | Some are useful, some are too destructive; must be tightly gated |
| Package mutations | `package-add`, `package-remove` | C | High blast radius, triggers reload/compile/dependency churn |
| Dynamic script execution | `script-execute` | C | Extremely powerful but too unconstrained for default use |
| Reflection method call | `reflection-method-find`, `reflection-method-call` | C | Deep access, bypasses normal tool contracts, high misuse risk |
| Tool toggling and generation | `tool-list`, `tool-set-enabled-state`, `skills-create`, `skills-generate` | B/C | Useful administratively, not for normal project work loops |
| Runtime in-game MCP connection | `UnityMcpPluginRuntime.Initialize(...).Build()` | C | Valuable for special products, but not part of standard editor validation loop |

## Recommended XUUnity Surface

For the first stable `xuunity` integration, expose only this normalized surface:

1. `unity.status`
2. `unity.console.tail`
3. `unity.scene.snapshot`
4. `unity.tests.run_editmode`

Second wave candidates:

5. `unity.assets.find`
6. `unity.assets.read`
7. `unity.object.inspect`
8. `unity.screenshot.capture`

Anything broader should wait until the first validation slice is operationally stable.

## Feature-by-Feature Policy

## 1. Editor state and readiness

Examples:
- `editor-application-get-state`
- backend connection status

Policy:
- expose directly
- use as prerequisite check before any Unity-backed validation

Why:
- low ambiguity
- low mutation
- strong operational value

Adapter implication:
- stays in the core adapter

## 2. Console logs

Examples:
- `console-get-logs`
- `console-clear-logs`

Policy:
- allow read access
- disable log clearing by default

Why:
- logs are core evidence for compile/runtime diagnosis
- log clearing erases context and makes postmortems worse

Adapter implication:
- expose `tail/read`
- do not expose `clear`

## 3. Scene snapshot

Examples:
- `scene-get-data`
- `scene-list-opened`
- active scene metadata

Policy:
- expose directly
- keep first version read-only and lightweight

Why:
- extremely useful for verifying what Unity actually has open
- low blast radius

Adapter implication:
- core `unity.scene.snapshot`

## 4. EditMode tests

Examples:
- `tests-run`

Policy:
- expose directly
- keep output normalized and honest
- never normalize `no tests` into `passed`

Why:
- highest-value validation operation
- strongest confidence multiplier for `xuunity`

Adapter implication:
- core `unity.tests.run_editmode`

## 5. Read-only asset and object inspection

Examples:
- `assets-find`
- `assets-get-data`
- `script-read`
- `object-get-data`
- `gameobject-find`
- `gameobject-component-get`

Policy:
- allow in second wave
- keep request size bounded

Why:
- strong debugging value
- helps build precise patches
- lower risk than mutations

Adapter implication:
- good next adapter slice after validation core

## 6. Screenshots

Examples:
- `screenshot-scene-view`
- `screenshot-game-view`
- `screenshot-camera`

Policy:
- allow behind explicit request
- treat as supporting evidence, not sole truth

Why:
- great for UI/layout checks
- not enough alone for behavior correctness
- can fail due to camera/view state rather than product state

Adapter implication:
- optional `unity.screenshot.capture`

## 7. Narrow scripted writes

Examples:
- `script-update-or-create`
- `assets-create-folder`
- `assets-refresh`

Policy:
- allow with guardrails
- require concrete target path
- require validation follow-up

Why:
- useful for implementation loops
- moderate mutation scope

Adapter implication:
- not in first stable adapter slice
- acceptable in implementation-focused mode later

## 8. Scene and hierarchy mutations

Examples:
- `gameobject-create`
- `gameobject-modify`
- `gameobject-component-add`
- `gameobject-component-modify`
- `gameobject-destroy`
- `assets-prefab-instantiate`

Policy:
- guarded only
- require explicit user intent or bounded automation workflow

Why:
- changes are fast but easy to make incoherent
- Unity scene mutation without downstream review can degrade project hygiene

Adapter implication:
- likely separate mutation-capable adapter mode, not default validation mode

## 9. Asset mutations

Examples:
- `assets-modify`
- `assets-move`
- `assets-copy`
- `assets-delete`
- prefab/material creation

Policy:
- split by risk
- creation and narrow modify can be guarded
- delete and broad modify should stay disabled by default

Why:
- file-level changes can be destructive and wide
- difficult to reason about safely from raw tool access

Adapter implication:
- avoid exposing raw delete/move operations directly through `xuunity`

## 10. Package mutation

Examples:
- `package-add`
- `package-remove`

Policy:
- disabled by default
- allow only in explicit operational onboarding or sandbox workflows

Why:
- high blast radius
- package resolution, compile churn, dependency drift
- can change project behavior far outside the immediate task

Adapter implication:
- keep outside normal project-work adapter
- route through operational tooling instead

## 11. Dynamic script execution

Examples:
- `script-execute`

Policy:
- disabled by default
- use only as last-resort exploratory/admin tool

Why:
- bypasses normal source review path
- weak auditability
- easy to create state changes that are hard to reconstruct

Adapter implication:
- do not expose in daily `xuunity` loop

## 12. Reflection method call

Examples:
- `reflection-method-find`
- `reflection-method-call`

Policy:
- disabled by default
- reserve for deep debugging or controlled admin tasks

Why:
- bypasses explicit tool contracts
- can reach private/internal methods
- high abuse and fragility potential

Adapter implication:
- separate escape hatch, not standard adapter operation

## 13. Skill and tool administration

Examples:
- `tool-list`
- `tool-set-enabled-state`
- `skills-create`
- `skills-generate`

Policy:
- allowed only for MCP administration/onboarding
- not part of day-to-day feature implementation

Why:
- useful for configuring the toolchain
- not useful as stable project execution primitives

Adapter implication:
- operational layer, not project work layer

## 14. Runtime in-game MCP

Examples:
- `UnityMcpPluginRuntime.Initialize(...).Build()`

Policy:
- disabled by default for standard `xuunity`
- allow only in explicit runtime-AI product experiments

Why:
- expands build/runtime surface
- changes security and production posture
- outside standard editor validation scope

Adapter implication:
- separate protocol branch if ever used

## Recommended Guardrails

These guardrails should sit above the raw backend.

### Hard rules

- read operations are preferred over mutation operations
- validation operations are preferred over convenience operations
- destructive operations are disabled by default
- runtime-specific paths are disabled by default
- package mutation is not allowed in standard feature work

### Mutation rules

- require one concrete project root
- require explicit target path/object scope
- require follow-up validation where applicable
- reject broad wildcard mutations

### Evidence rules

- screenshots are supporting evidence only
- tests and editor-state are primary evidence
- log clearing must not happen before evidence capture

## What XUUnity Should Use Daily

Daily reliable path:
- editor status
- console read
- scene snapshot
- edit-mode tests
- bounded asset/script/object reads

This is the useful center of gravity.

## What XUUnity Should Keep But Hide

Available but hidden behind explicit intent:
- screenshots
- narrow writes
- scene/object mutation
- prefab operations

These are valuable, but not good default automation primitives.

## What XUUnity Should Treat As Escape Hatches

- dynamic script execution
- reflection call
- package add/remove
- runtime connect mode
- destructive delete flows

These should exist only as exceptional tools, not as normal workflow components.

## Bottom Line

`IvanMurzak/Unity-MCP` has a broad and genuinely useful surface.

For `xuunity`, the right move is not to expose that full surface directly.

The right move is:
- keep the backend broad
- keep the `xuunity` adapter narrow
- make validation first-class
- make mutation guarded
- keep deep-power tools behind explicit escalation
