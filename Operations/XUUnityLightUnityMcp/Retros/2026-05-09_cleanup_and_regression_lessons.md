# XUUnity Light Unity MCP Cleanup And Regression Lessons

Date: `2026-05-09`
Status: `public-safe lessons report`
Scope: `refactor discipline, regression discipline, and batch validation lessons`

## Purpose

Capture reusable lessons from cleanup and live regression work without keeping
 consumer-project-specific handoff reports in the public layer.

## Structural Cleanup Lessons

### 1. Extraction slices need live CLI error-path validation

Unit coverage was not enough to catch a real runtime break after helper
extraction. A CLI error path still referenced a moved helper and failed only in
live execution.

Reusable rule:
- after each nontrivial `server.py` extraction slice, run at least one real CLI
  unhappy-path check in addition to host tests

Good candidates:
- invalid request argument path
- tool error summary path
- recovery path after lifecycle reset

### 2. Keep orchestration concentrated until the boundary is clear

Reporting, payload shaping, and polling helpers were safe extraction targets.
Lifecycle orchestration remained the highest-risk concentration point.

Reusable rule:
- split shaping and reporting helpers first
- postpone orchestration splits until the request and recovery contract is
  already well-proven

### 3. Pause cleanup when live project truth turns red

Batch infrastructure work surfaced real project failures during the same pass.
Continuing structural cleanup past that point would have reduced signal quality.

Reusable rule:
- when infrastructure work exposes real consumer failures, stabilize product
  truth first and resume cleanup after the validation baseline is green again

## Batch Validation Lessons

### 4. Batch lanes should distinguish infra proof from project truth

A failing batch run can still mean the infrastructure is correct if it exposed a
real project defect instead of a transport or orchestration defect.

Reusable rule:
- classify failures as:
  - infrastructure failure
  - project/test failure
  - discovery/wiring gap

This prevents infrastructure churn from hiding real consumer regressions.

### 5. Closed-project compile matrix and test lanes are useful independent signals

Compile matrix success proved the batch orchestration lane while a later test
run exposed real test defects.

Reusable rule:
- keep compile-matrix validation and EditMode validation as separate evidence
  lanes
- do not treat compile success as test truth

## Unity Regression Lessons

### 6. Retained fixtures can be the correct cleanup strategy

Deleting transient `.cs` fixtures after fault injection can leave Unity or Bee
with ghost compile references on later passes.

Reusable rule:
- when a fault suite introduces C# files and later compiles depend on stable
  source graphs, prefer retained fixtures over aggressive cleanup unless the
  suite can prove graph convergence afterward

### 7. Sequential suite discipline matters after editor and transport churn

Some wrappers reopen the editor, switch transport, or trigger recovery flows.
Naive all-suite loops are fragile in that state.

Reusable rule:
- run suites sequentially
- re-establish `ensure-ready` before each major suite
- verify final health before starting the next suite

### 8. `unity.editor.quit` acknowledgment is not the same as verified process exit

A host can receive a quit acknowledgment while the Unity process is still alive.

Reusable rule:
- closeout logic should classify acknowledgment separately from verified exit
- recovery guidance should include the next bounded action when closeout is not
  fully proven

This lesson is now reflected in the public closeout classifications and should
remain part of future smoke expectations.

## Suggested Promotion Targets

These lessons belong in public behavior and docs when they are not already
captured:

- smoke and recovery docs
- cleanup/refactor guidance for `templates/server.py`
- closeout and lifecycle validation contracts
