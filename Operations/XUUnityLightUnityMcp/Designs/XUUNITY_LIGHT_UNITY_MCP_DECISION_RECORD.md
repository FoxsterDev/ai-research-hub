# XUUnity Light Unity MCP Decision Record

Date: `2026-05-15`
Status: `active source-of-truth decision record`
Scope: public rationale for why `XUUnityLightUnityMcp` exists and why it has its current shape

This document is the curated source of truth for the major design decisions
behind `XUUnityLightUnityMcp`.

It summarizes and supersedes these historical design inputs:

- `History/XUUNITY_UNITY_MCP_EVALUATION_AND_ADAPTER_DESIGN_2026-05-04.md`
- `History/XUUNITY_UNITY_MCP_FEATURE_MATRIX_AND_POLICY_2026-05-04.md`
- `History/XUUNITY_LIGHTWEIGHT_UNITY_MCP_SERVICE_DESIGN_2026-05-05.md`

Keep those history files for detailed background. Use this document when you
need to quickly understand what was decided and why.

## Core Decision

Build and maintain a small public `XUUnityLightUnityMcp` package instead of
standardizing `xuunity` directly on a broad existing Unity MCP backend.

The package should provide:

- a tiny local stdio MCP server
- a tiny editor-only Unity bridge package
- explicit project targeting
- structured validation evidence
- a narrow, high-trust operation surface
- public reusable templates and setup docs
- host-local wrappers outside public `AIRoot`

Existing public Unity MCP projects remain valuable reference material, but they
are not the runtime dependency for the standard `xuunity` validation path.

## Why Not Use A Broad Existing Backend Directly

Broad Unity MCP packages proved useful for research and feature discovery, but
they did not match the desired default `xuunity` shape.

Main concerns:

- too much dependency mass for a validation-first workflow
- possible player-build/runtime footprint
- capability surfaces that invite mutation before trust is established
- dynamic script execution and reflection-style escape hatches
- package mutation and broad asset mutation capabilities
- more setup and lifecycle machinery than the daily workflow needs
- raw vendor tool names would leak into stable `xuunity` behavior

The conclusion was not "avoid MCP." The conclusion was:

- use MCP for real Unity-aware validation
- keep the default bridge small
- keep broad vendor surfaces as references and comparison points
- expose only the operations that produce reliable engineering evidence

## Why A Lightweight Custom Package Is The Better Default

The daily `xuunity` loop needs a dependable Unity-aware proof path, not a
generic AI game platform.

The default package optimizes for:

- trust
- clarity
- small blast radius
- fast onboarding
- stable structured evidence
- easy removal
- no player-build impact by default

This supports the most common engineering questions:

- Is the intended Unity project open and reachable?
- Is the editor healthy or busy?
- What does the console say?
- What scene is active?
- Can Unity compile this target/profile path?
- Do selected EditMode or PlayMode tests pass?
- Can an ordered scenario produce durable evidence?

## Architecture Decision

Use two parts:

1. external MCP server process
2. Unity Editor bridge package

Do not add a third service, runtime game component, cloud relay, or dependency
stack in the base design.

High-level shape:

```text
MCP client
  -> local stdio MCP server
    -> project-scoped request broker
      -> Unity Editor bridge
        -> Unity Editor APIs
```

Responsibilities:

- External server:
  - speak MCP over stdio
  - validate project targeting
  - normalize tool inputs and outputs
  - manage request IDs and timeouts
  - expose the public tool surface
- Unity bridge:
  - run only in the Unity Editor
  - publish heartbeat, health, capabilities, and lifecycle state
  - execute registered operations
  - write structured results and durable artifacts

## Transport Decision

Start with local file IPC under:

- `<Project>/Library/XUUnityLightMcp/`

Reason:

- zero network stack
- zero auth/token setup for same-user local use
- no SignalR, WebSocket, relay, or HTTP dependency
- easier debugging from disk
- lower implementation risk during Unity reloads
- all mutable bridge state stays outside source and outside `Assets/`

The design later added a loopback TCP transport as an operational improvement,
but the base trust model remains same-host, same-user, explicitly targeted
Unity editor work.

HTTP or remote transports are not the default. They may be future extensions,
but they should not change the base package's local-first trust boundary.

## Packaging Decision

The Unity package must be editor-only.

Base rules:

- package id: `com.xuunity.light-mcp`
- public source: `AIRoot/Operations/XUUnityLightUnityMcp/templates/unity-package`
- no runtime asmdef in the base package
- no generated source under `Assets/`
- no player-build footprint by default
- no package mutation beyond the project manifest entry
- all bridge state under `Library/XUUnityLightMcp/`

Host-local development may use a local `file:` dependency. Production project
wiring should pin to a published public git commit.

## Tool Surface Policy

The tool surface is intentionally small. The goal is not maximum tool count.
The goal is high-confidence Unity evidence.

### Band A: Daily Core

Expose as first-class operations:

- editor readiness and status
- health and capabilities
- console read/tail
- active scene snapshot
- active scene assertion
- EditMode tests
- PlayMode tests where configured
- player-script compile gates
- ordered scenario execution
- Game View screenshot as supporting evidence

These operations are low mutation, high signal, and useful in normal feature,
bugfix, review, and SDK validation work.

### Band B: Guarded Extensions

Useful, but only behind explicit intent and narrow scope:

- bounded asset and object inspection
- screenshot and Game View configuration
- project-defined hooks
- profile/environment apply hooks
- local data cleanup hooks
- narrow project-owned scenario actions

These can mutate project/editor state or create misleading evidence if used
casually. They require clear target scope, cleanup expectations, and follow-up
validation.

### Band C: Disabled By Default

Do not expose as normal workflow primitives:

- package add/remove
- arbitrary dynamic C# execution
- broad reflection method calls
- broad scene or hierarchy mutation
- broad asset mutation or delete
- runtime in-game MCP connection
- remote/cloud relay operation

These may be valid for specialized products or one-off investigations, but they
are not part of the standard `xuunity` validation path.

## Evidence Policy

MCP exists here to produce honest Unity evidence.

Rules:

- shell compile or source inspection must not be reported as Unity MCP
  validation
- if MCP is unavailable, the validation gap must remain explicit
- screenshots are supporting evidence, not sole proof
- tests, compile gates, scene assertions, health, and structured scenario
  results are stronger proof
- log clearing is disabled by default because it destroys context
- missing capabilities should become typed gaps or backlog, not hidden success

## Mutation Policy

Read operations come first. Mutations are allowed only when they are narrow,
intentional, and validated.

Mutation requirements:

- one concrete project root
- explicit target scope
- known cleanup or restore behavior
- follow-up status/health/compile/test/scenario evidence where applicable
- fail closed on ambiguous project, missing hook, missing cleanup, or unsafe
  secret input

Project-specific behavior belongs in project hooks and project operation
folders, not in the public bridge core.

## Adapter And Naming Decision

`xuunity` should rely on stable conceptual operations, not raw vendor tool
names.

Preferred conceptual names:

- `unity.status`
- `unity.console.tail`
- `unity.scene.snapshot`
- `unity.scene.assert`
- `unity.tests.run_editmode`
- `unity.tests.run_playmode`
- `unity.compile.player_scripts`
- `unity.scenario.run`

MCP-facing names may be client-friendly wrapper names such as:

- `unity_status`
- `unity_console_tail`
- `unity_scene_snapshot`
- `unity_scene_assert`

This keeps prompt/workflow logic stable even if public MCP protocol bindings,
client naming conventions, or underlying implementation details evolve.

## Host-Local Boundary Decision

Public `AIRoot` owns reusable package behavior:

- server templates
- Unity package templates
- public operations
- public design docs
- public setup and validation guidance

Host-local/project-local layers own:

- repo-specific wrapper commands
- project selection shortcuts
- project smoke scenarios
- project-defined hooks
- profile/environment names
- product-specific E2E flows
- confidential or project-bound evidence

Do not move project-specific behavior into the public bridge unless it has been
validated as reusable across projects and can be expressed without private
context.

## Reference Project Policy

Public Unity MCP projects are allowed and useful as public references.

Use them for:

- editor lifecycle research
- test execution quirks
- console capture edge cases
- scene/object serialization boundaries
- MCP client ergonomics
- custom tool registration patterns
- examples of capabilities to keep, hide, or reject

Do not inherit blindly:

- runtime support
- package mutation defaults
- dynamic code execution defaults
- heavyweight dependency graphs
- remote relay infrastructure
- raw broad tool surfaces

## Current Outcome

The current package follows the decision direction:

- public package under `AIRoot/Operations/XUUnityLightUnityMcp/`
- editor-only Unity package
- external server templates
- explicit project targeting
- scenario runner
- health/capability reporting
- scene snapshot and scene assertion
- compile/test primitives
- Game View evidence primitives
- project-defined hook escape valve
- host-local consumer-project profile scenarios kept outside public `AIRoot`

The design is still intentionally conservative. Future expansion should prefer
more evidence and better lifecycle robustness before adding broad mutation.

## Current Implementation Notes

This decision record describes the design direction and policy. The implemented
operation surface is intentionally a little wider than the daily evidence core
because the package also needs operational support tools for setup, recovery,
package refresh, and project-specific validation lanes.

Current core evidence operations include:

- `unity.status`
- `unity.capabilities.get`
- `unity.health.probe`
- `unity.console.tail`
- `unity.scene.snapshot`
- `unity.scene.assert`
- `unity.tests.run_editmode`
- `unity.tests.run_playmode`
- `unity.compile.player_scripts`
- `unity.compile.matrix`
- `unity.scenario.validate`
- `unity.scenario.run`
- `unity.scenario.result`
- `unity.game_view.configure`
- `unity.game_view.screenshot`

Current operational support operations include:

- `unity.build_target.get`
- `unity.build_target.switch`
- `unity.project.refresh`
- `unity.playmode.state`
- `unity.playmode.set`
- `unity.editor.quit`
- `unity.edm4u.resolve`
- `unity.sdk.dependency.verify`

These support operations are not a license for broad mutation. They exist to
make validation lanes deterministic and recoverable:

- `unity.build_target.switch` is used only when a validation lane explicitly
  needs a build target transition.
- `unity.project.refresh` is used to settle Unity after package/profile/config
  mutations.
- `unity.playmode.set` is used by ordered scenarios with explicit state
  assertions.
- `unity.edm4u.resolve` and `unity.sdk.dependency.verify` are SDK validation
  helpers, not general package mutation tools.
- `unity.editor.quit` is an operational lifecycle command and should not be
  treated as routine feature-work behavior.

The Unity package currently depends on Unity's Test Framework package because
test execution is part of the validation core. This is acceptable under the
dependency policy because it is a Unity-owned editor/testing dependency, not a
heavy external runtime stack.

The package still intentionally does not expose:

- arbitrary C# execution
  - Useful for one-off editor diagnostics, emergency repair scripts, or
    exploratory automation when no typed operation exists.
  - Not default because it bypasses typed contracts, reviewable operation
    boundaries, and normal compile/test feedback loops.
- broad reflection method call
  - Useful for inspecting or invoking Unity/editor internals that do not have a
    supported public API.
  - Not default because it is brittle across Unity versions and can bypass
    intended safety checks.
- package add/remove
  - Useful for dependency onboarding, SDK migration experiments, and automated
    package upgrade probes.
  - Not default because it mutates project dependencies, triggers reload/import
    churn, and can break unrelated validation lanes.
- broad asset delete/mutation
  - Useful for asset cleanup, migration, generated content repair, or bulk
    project refactors.
  - Not default because asset changes can be destructive, noisy, and difficult
    to review without precise target scoping.
- broad scene or hierarchy mutation
  - Useful for level-editing automation, prefab repair, generated scene setup,
    or UI hierarchy refactors.
  - Not default because scene/prefab mutations are high blast-radius and often
    require product-specific visual validation.
- runtime in-game MCP connection
  - Useful for live gameplay instrumentation, runtime state inspection, bot-like
    E2E flows, and game-specific debug/control surfaces.
  - Not default because it adds player/runtime footprint and changes the trust
    model from editor validation to in-game control.
- remote/cloud relay operation
  - Useful for remote CI agents, shared lab devices, distributed QA, or hosted
    editor automation.
  - Not default because it introduces network exposure, authentication, routing,
    and multi-user trust concerns that the same-host editor workflow avoids.

## Decision Checklist For Future Changes

Before adding a new MCP capability, answer:

1. Is it editor-only by default?
2. Does it produce evidence or only convenience?
3. Can it target one concrete project/root/object?
4. Is it read-only, or does it have a cleanup/restore contract?
5. Can it fail with a typed, useful gap?
6. Does it avoid player-build footprint?
7. Does it avoid broad dynamic code execution?
8. Does it belong in public core, or should it be a project hook?
9. Does it keep returned data bounded and structured?
10. Does it make the default `xuunity` loop more trustworthy?

If the answer is weak, keep the capability guarded, project-local, or in
backlog/spec form.
