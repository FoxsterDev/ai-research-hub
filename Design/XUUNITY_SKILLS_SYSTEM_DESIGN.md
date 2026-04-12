# XUUnity Skills System Design

## Goal
Design a hierarchical skills system for `XUUnity` so the AI can:
- load shared best practices for all projects
- detect relevant skill packs by task keywords and code signals
- apply project-specific overrides when they exist
- build the minimum correct context before sending the task to the cloud LLM

This system is optimized for:
- Unity `6000+`
- mobile production targets
- zero-crash and zero-ANR engineering posture
- no microfreezes on critical user flows
- strong performance, allocation, thermal, and startup discipline

This document is for architectural review.

## Problem
`XUUnity` already has routing for role, task, platform, review, codestyle, and project memory.
What is still missing is a reusable skill layer for high-value engineering domains such as:
- asynchronous programming in Unity
- UniTask best practices
- `Awaitable` best practices
- .NET `Task` usage in Unity
- Unity UI and screen flows
- editor tooling
- sounds and audio pipeline safety
- FX and VFX integration
- shaders and rendering constraints
- optimization and profiling
- tests and validation strategy
- event systems
- state machines
- scene loading
- mobile startup flows
- bridge design
- error handling

The system needs to support both:
- shared git-based best practices for all projects
- project-specific overrides or constraints

## Core Design Rule
`XUUnity` should not load all skills by default.
It should load only the baseline safety layer plus the skill packs that match the current task.

The loading sequence should be:
1. classify task
2. load baseline safety skills
3. identify required skills by keywords, intent, and code signals
4. load shared skills
5. check project-specific overrides
6. merge shared and project-specific guidance
7. build the final working context
8. only then send the task to the cloud LLM

## Design Principles
- keep the system hierarchical
- keep shared skills reusable and project-agnostic
- keep project-specific behavior outside shared skill files
- prefer operational skill files over long theory dumps
- let project memory override shared rules
- keep routing deterministic and inspectable
- minimize token cost by loading only relevant skill packs
- treat Unity `6000+` runtime behavior as the default baseline
- design for mobile runtime limits first, not desktop convenience
- prioritize zero unhandled exceptions and callback safety
- prefer solutions that do not introduce GC churn, frame spikes, ANRs, or hidden synchronization stalls
- validate critical flows before optimizing for elegance

## Proposed Directory Structure

```text
AIRoot/
  Modules/
    XUUnity/
      skills/
        README.md
        registry.md
        core/
          README.md
          unity6000_baseline.md
          mobile_runtime_safety.md
          zero_crash_zero_anr.md
          critical_flow_protection.md
        async/
          README.md
          routing.md
          base_async_rules.md
          unitask.md
          awaitable.md
          dotnet_task.md
          cancellation.md
          main_thread.md
          exception_handling.md
        ui/
          README.md
          ugui.md
          ui_toolkit.md
          layout_and_rebuilds.md
          input_and_navigation.md
          popup_and_screen_flows.md
        editor/
          README.md
          tooling_design.md
          import_pipeline.md
          custom_inspectors.md
          validation_tools.md
        audio/
          README.md
          playback_safety.md
          mixer_and_snapshot_usage.md
          streaming_and_memory.md
        fx/
          README.md
          vfx_lifecycle.md
          pooling_and_spawn_budget.md
          overdraw_and_fillrate.md
        shaders/
          README.md
          mobile_shader_rules.md
          variant_control.md
          srp_batcher_and_materials.md
        optimization/
          README.md
          frame_budgeting.md
          allocation_control.md
          loading_and_microfreeze_prevention.md
        profiling/
          README.md
          profiler_workflow.md
          instrumentation.md
          regression_detection.md
        tests/
          README.md
          unit_tests.md
          integration_tests.md
          playmode_tests.md
          smoke_and_release_checks.md
        architecture/
          README.md
          state_management.md
          event_driven_design.md
          dependency_boundaries.md
        mobile/
          README.md
          startup.md
          performance.md
          critical_flows.md
        sdk/
          README.md
          initialization.md
          callback_safety.md
          privacy_compliance.md
        native/
          README.md
          bridge_contracts.md
          callback_lifetime.md
          ownership.md

AIModules/
  XUUnityInternal/
  OtherHostLocalProtocol/
```

Project-specific overrides:

```text
<Project>/Assets/AIOutput/ProjectMemory/
  SkillOverrides/
    README.md
    async.md
    ui.md
    sdk.md
    native.md
    performance.md
    tests.md
    architecture.md
```

## Skill Layer Semantics

### Shared skill files
Shared skill files contain:
- durable best practices
- common pitfalls
- decision rules
- routing hints
- concise implementation guidance

They must not contain:
- project-specific SDK decisions
- project-specific platform caveats
- one-off production incidents

### Project skill overrides
Project overrides contain:
- exceptions to the shared rule
- project-specific constraints
- known incompatibilities
- preferred local pattern choices

They override shared skills only where needed.

## Routing Model

### Layer order inside XUUnity
Recommended full stack:
1. `role/base_role.md`
2. `codestyle/`
3. `tasks/start_session.md`
4. baseline safety skills from `skills/core/`
5. inferred task file
6. relevant skill packs from `skills/`
7. relevant review or utility files
8. platform files
9. project memory
10. project skill overrides
11. relevant prior outputs

### Why `skills/core/` is always loaded
Because Unity `6000+`, mobile safety, crash prevention, ANR prevention, and critical-flow protection are not optional concerns.
They are the default operating posture for all XUUnity work.

### Why task-specific skills sit before project memory
Shared skills define the generic solution space.
Project memory then narrows it with project-specific constraints and local exceptions.

## Skill Discovery Model

### Input sources for routing
The router should infer skills from:
- shorthand command
- task type
- code under inspection
- file names
- namespaces
- symbols
- project memory hints
- engine version signals
- target platform signals
- performance-sensitive call sites such as update loops, startup, scene loading, UI open or close, and SDK callbacks

### Baseline skills that should always load
Always load:
- `skills/core/unity6000_baseline.md`
- `skills/core/mobile_runtime_safety.md`
- `skills/core/zero_crash_zero_anr.md`
- `skills/core/critical_flow_protection.md`

### Example keyword routing

#### Async skill group
Trigger words:
- `async`
- `await`
- `UniTask`
- `Awaitable`
- `Task`
- `CancellationToken`
- `main thread`
- `Forget`
- `fire and forget`
- `timeout`
- `race`
- `concurrent`
- `SwitchToMainThread`
- `PlayerLoop`

Load:
- `skills/async/base_async_rules.md`
- one or more of:
  - `skills/async/unitask.md`
  - `skills/async/awaitable.md`
  - `skills/async/dotnet_task.md`
  - `skills/async/cancellation.md`
  - `skills/async/main_thread.md`
  - `skills/async/exception_handling.md`

#### UI skill group
Trigger words:
- `ui`
- `screen`
- `popup`
- `button`
- `scrollrect`
- `layoutgroup`
- `canvas`
- `TextMeshPro`
- `UGUI`
- `UIToolkit`
- `navigation`

Load:
- `skills/ui/ugui.md`
- optional:
  - `skills/ui/ui_toolkit.md`
  - `skills/ui/layout_and_rebuilds.md`
  - `skills/ui/input_and_navigation.md`
  - `skills/ui/popup_and_screen_flows.md`

#### Editor skill group
Trigger words:
- `editor`
- `inspector`
- `propertydrawer`
- `MenuItem`
- `AssetPostprocessor`
- `importer`
- `build pipeline`
- `validation tool`

#### Audio skill group
Trigger words:
- `audio`
- `sound`
- `music`
- `mixer`
- `snapshot`
- `AudioClip`
- `streaming`

#### FX skill group
Trigger words:
- `fx`
- `vfx`
- `particle`
- `trail`
- `spawn`
- `impact effect`
- `overdraw`

#### Shader skill group
Trigger words:
- `shader`
- `material`
- `keyword`
- `variant`
- `URP`
- `SRP batcher`
- `overdraw`

#### Optimization skill group
Trigger words:
- `optimize`
- `perf`
- `performance`
- `GC`
- `alloc`
- `microfreeze`
- `frame spike`
- `loading`
- `startup`
- `battery`
- `thermal`
- `ANR`

#### Profiling skill group
Trigger words:
- `profiler`
- `profiling`
- `deep profile`
- `instrumentation`
- `marker`
- `timeline`
- `memory profiler`

#### Tests skill group
Trigger words:
- `test`
- `tests`
- `unit test`
- `integration test`
- `playmode`
- `editmode`
- `smoke test`
- `release check`

#### SDK skill group
Trigger words:
- `sdk`
- `callback`
- `initialization`
- `attribution`
- `OneSignal`
- `AppsFlyer`
- `Firebase`
- `Adjust`

#### Native skill group
Trigger words:
- `JNI`
- `Swift`
- `Objective-C`
- `callback bridge`
- `P/Invoke`
- `native plugin`

#### Architecture skill group
Trigger words:
- `state`
- `service`
- `event bus`
- `facade`
- `presenter`
- `model`
- `lifecycle`

## Registry Model
Use one central registry file:

`AIRoot/Modules/XUUnity/skills/registry.md`

This file should map:
- skill name
- scope
- trigger keywords
- related task types
- related platform files
- allowed project override files
- priority
- always-load status
- core dependencies
- mutually exclusive skills if needed

Example shape:

```text
Skill: async/unitask
Use for:
- UniTask
- async Unity flows
- cancellation
Triggers:
- unitask
- forget
- cancellationtoken
Core dependencies:
- core/unity6000_baseline
- core/zero_crash_zero_anr
Project override:
- Assets/AIOutput/ProjectMemory/SkillOverrides/async.md
```

## Async Skill Family Design

### Why async should be first-class
Async guidance is one of the biggest sources of real engineering leverage and regressions in Unity mobile projects.
It needs explicit structure.

### Proposed async family

```text
AIRoot/Modules/XUUnity/skills/async/
  README.md
  routing.md
  base_async_rules.md
  unitask.md
  awaitable.md
  dotnet_task.md
  cancellation.md
  main_thread.md
  exception_handling.md
```

### Responsibilities
- `base_async_rules.md`
  - cross-cutting rules for async in Unity
- `unitask.md`
  - UniTask-specific patterns and anti-patterns
- `awaitable.md`
  - Unity `Awaitable` usage rules and boundaries
- `dotnet_task.md`
  - when and how to use .NET `Task` safely in Unity contexts
- `cancellation.md`
  - token ownership and cancellation propagation
- `main_thread.md`
  - thread affinity and Unity main-thread constraints
- `exception_handling.md`
  - no unhandled async exceptions, logging, propagation, fail-safe behavior

Async guidance should explicitly cover:
- Unity `6000+` async primitives and scheduling behavior
- `Awaitable` versus `UniTask` versus `.NET Task` selection rules
- cancellation ownership
- timeout policy
- fire-and-forget restrictions
- main-thread affinity rules for Unity objects
- exception propagation and logging policy
- zero-crash handling for background continuations and callbacks
- frame-budget awareness and microfreeze prevention

## Additional Skill Families

### UI and Unity UI
Use for:
- UGUI screens and popups
- layout-heavy interfaces
- navigation flows
- input-safe UI
- avoiding excessive canvas rebuilds and allocation churn

### Editor Tools
Use for:
- custom inspectors
- validation tools
- import pipeline helpers
- content pipeline automation
- safe internal tooling that reduces human error

### Sounds and Audio
Use for:
- playback orchestration
- mixer and snapshot policy
- memory-safe clip loading
- streaming versus preload decisions
- audio behavior that does not hitch gameplay or UI transitions

### FX
Use for:
- particles
- VFX lifecycle
- pooling and spawn budgets
- overdraw-sensitive visuals on mobile

### Shaders
Use for:
- mobile-friendly shader authoring
- material usage rules
- variant control
- SRP batcher compatibility
- overdraw and fill-rate awareness

### Optimization
Use for:
- frame budget control
- allocation reduction
- startup optimization
- loading flow smoothing
- ANR and microfreeze prevention

### Profiling
Use for:
- finding regressions
- adding profiler markers
- interpreting CPU, GPU, memory, and loading traces
- converting profiling evidence into engineering actions

### Tests
Use for:
- unit, integration, and playmode coverage
- crash-prone and async-prone flow validation
- SDK smoke checks
- release readiness gates for critical flows

## Safety-Critical Routing Rules
- If a task touches startup, scene loading, IAP, rewarded ads, save/load, remote config, or attribution callbacks, load `skills/core/critical_flow_protection.md`.
- If a task contains async work, background callbacks, or any native boundary, load `skills/core/zero_crash_zero_anr.md`.
- If a task affects screen transitions, list virtualization, layout rebuilding, or addressable loading, load `skills/optimization/loading_and_microfreeze_prevention.md`.
- If a task changes runtime rendering, VFX, or shaders on mobile, load optimization and profiling skills together with the domain skill.

## Project Override Model

### Shared vs project-local example
Shared rule:
- `UniTask` is preferred for gameplay-facing Unity async flows.

Project override:
- this project uses `Awaitable` for a specific UI subsystem because of an engine-version constraint

Result:
- shared async skill loads first
- project override updates the final decision
- final answer uses the project-specific rule

### Suggested override structure

`Assets/AIOutput/ProjectMemory/SkillOverrides/async.md`

Contents:
- preferred async primitive by subsystem
- banned patterns
- existing wrappers and helper APIs
- known threading constraints
- migration rules

## Final Request Processing Model

### Example request
`xuunity review this async initialization flow`

### Expected internal flow
1. detect protocol family: `xuunity`
2. detect task type: `code review`
3. load baseline safety skills
4. detect skill group: `async`
5. detect subtopics:
   - initialization
   - exception safety
   - main thread
6. load:
   - role
   - codestyle
   - `tasks/start_session.md`
   - `skills/core/`
   - `tasks/code_review.md`
   - async skill files
   - sdk or mobile startup skill files if relevant
   - project memory
   - project `SkillOverrides/async.md` if present
   - relevant prior outputs
7. assemble context
8. send composed request to cloud LLM

## LLM Efficiency Rules
- never load whole `skills/` by default
- always load only the baseline safety skills plus the triggered skill packs
- prefer small topic files over one huge knowledge dump
- keep registry explicit and human-readable
- use project overrides only when the matching override file exists
- avoid duplicate guidance across skills, codestyle, and knowledge files

## Conflict Resolution
When multiple layers disagree:
1. explicit project override in `SkillOverrides/`
2. project memory in `Assets/AIOutput/ProjectMemory/`
3. shared skill files in `AIRoot/Modules/XUUnity/skills/`
4. generic XUUnity role, task, and platform guidance

Extra rules:
- if a zero-crash, zero-ANR, or critical-flow rule conflicts with convenience guidance, safety wins
- if a project override weakens a shared safety rule, require explicit evidence and rationale in project memory

## Ingestion Model For New Knowledge
When new knowledge is added:
1. classify it as shared or project-specific
2. place it in a draft file
3. connect it in `skills/registry.md`
4. define trigger keywords
5. define allowed project override path
6. verify it does not duplicate an existing skill file

## Review Criteria
Approve this design only if:
- the skill hierarchy stays modular
- XUUnity remains the entry point
- shared skills and project overrides are clearly separated
- routing can be explained deterministically
- async knowledge can be integrated cleanly without bloating every task
- the final system is efficient enough for real LLM context windows
- the baseline posture enforces Unity `6000+` mobile safety, zero-crash, zero-ANR, and no-microfreeze expectations

## Recommended Next Steps
1. Add `AIRoot/Modules/XUUnity/skills/README.md`
2. Add `AIRoot/Modules/XUUnity/skills/registry.md`
3. Implement `skills/core/` first
4. Implement the `async/` family first
5. Add `ui/`, `optimization/`, and `tests/` as the next priority families
6. Add project override template:
   - `Assets/AIOutput/ProjectMemory/SkillOverrides/README.md`
7. Update `tasks/start_session.md` to load skills after task classification
8. Add examples for shorthand skill routing
