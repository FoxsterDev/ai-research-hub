# XUUnity Validation Lanes

Use this file when validation strategy depends on tool-path selection and evidence quality.
It defines the shared lane model for Unity validation so `xuunity` can choose the narrowest representative path without overclaiming proof.

## Lane Types

### `interactive_mcp`
Use editor-integrated validation through MCP or another host-integrated Unity bridge.

Best for:
- editor state and readiness
- console inspection
- scene snapshot or hierarchy inspection
- play mode entry or exit
- Game View configuration or screenshots
- project-defined editor hooks
- Unity test or compile actions that must stay inside the integrated bridge path

Strengths:
- representative editor state
- access to Unity-only surfaces that shell tools cannot observe directly
- better fit for repos that forbid direct shell-launched Unity validation

Limits:
- depends on editor startup health
- can be blocked by interactive compile errors, package-resolution failures, or Safe Mode
- should not be treated as physical-device proof

### `batch_compile`
Use non-interactive Unity automation such as batchmode compile, build, or test execution when the repo allows it.

Best for:
- compile verification
- define-matrix verification
- build-target verification
- deterministic narrow test execution that does not depend on interactive editor state

Strengths:
- good for fail-fast compile health
- good for matrix-style target checks
- avoids interactive editor focus and lifecycle churn

Limits:
- not suitable for play mode choreography, Game View, screenshots, or scene-state observation
- not equivalent to interactive runtime proof
- must not be used when repo or project rules require MCP or another integrated path instead

### `scenario`
Use an integrated, persisted multi-step automation lane for ordered runtime evidence.

Best for:
- play mode transition sequences
- screenshot capture after a state change
- runtime setup plus evidence capture
- project-defined validation hooks that depend on sequence and timing
- automation that must survive editor update ticks or domain reload boundaries

Strengths:
- explicit sequencing
- durable result bundles
- better fit for automation that needs more than one tool call to become meaningful

Limits:
- slower than narrow one-shot checks
- still editor-integrated rather than device-native
- should not replace device profiling, device screenshots, or native observability when those are the real requirement

## Selection Rules
- Choose one primary validation lane before running tools when the task needs evidence beyond source inspection.
- Add a secondary lane only when the first lane cannot answer the full question alone.
- Keep `required_validation` and the chosen lane aligned. Do not ask a batch lane to prove an interactive runtime claim.
- Use `interactive_mcp` when the question depends on live editor state, console state, scene state, Game View, play mode, or a host-integrated Unity contract.
- Use `batch_compile` when the question is mainly compile health, define coverage, target coverage, or deterministic non-interactive test execution and direct shell automation is permitted.
- Use `scenario` when the proof depends on ordered steps, waiting for state transitions, or persisted runtime evidence.
- If repo or project rules require integrated validation, treat that as a hard override against `batch_compile` even if Unity CLI is available.
- If interactive startup fails because of compile blockers, package-resolution failure, or Safe Mode gating, either:
  - fix the blocker first
  - switch to `batch_compile` only when that lane is allowed and the claim tolerates it
  - or report the remaining validation gap explicitly
- Do not treat `batch_compile` success as proof of:
  - play mode behavior
  - scene-state correctness
  - Game View rendering
  - device or native bridge behavior
- Do not treat `scenario` or `interactive_mcp` success as proof of:
  - physical-device performance
  - native profiler truth
  - release-ready store or OEM matrix coverage

## Output Contract
When lane selection matters, include these fields in the execution contract or validation plan:
- `primary_validation_lane`
- `secondary_validation_lane`
- `lane_selection_reason`

Keep them short and concrete.
