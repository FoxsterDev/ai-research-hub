# XUUnity Skills Registry

## Purpose
This registry maps skill families to:
- use cases
- trigger keywords
- related task types
- required baseline dependencies
- allowed project override files

## Core
Skill: `core/unity6000_baseline`
Use for:
- Unity `6000+` runtime baseline
- engine assumptions
- default modern mobile posture
Always load: yes

Skill: `core/mobile_runtime_safety`
Use for:
- mobile-safe implementation
- lifecycle safety
- startup and runtime guardrails
Always load: yes

Skill: `core/zero_crash_zero_anr`
Use for:
- exception safety
- callback safety
- ANR prevention
Always load: yes

Skill: `core/critical_flow_protection`
Use for:
- startup
- scene loading
- IAP
- ads
- save/load
- rewards
- remote config
Always load: yes

## Async
Skill family: `async/`
Triggers:
- async
- await
- task
- unitask
- awaitable
- cancellationtoken
- callback
- thread
Use for:
- async implementation
- async refactor
- async review
Project override:
- `Assets/AIOutput/ProjectMemory/SkillOverrides/async.md`

## UI
Skill family: `ui/`
Triggers:
- ui
- screen
- popup
- canvas
- layout
- grid
- adaptive grid
- safe area
- cutout
- notch
- touch target
- rtl
- localization
- font scale
- accessibility
- infinite scroll
- virtualized list
- virtualized grid
- pooling
- inventory
- store
- gallery
- collection
- scrollrect
- button
- navigation
- textmeshpro
- ugui
- uitoolkit
Use for:
- screen flows
- popup work
- layout-heavy UI
- input and navigation behavior
- adaptive grid and collection layout work
- mobile UX quality and readability review
Project override:
- `Assets/AIOutput/ProjectMemory/SkillOverrides/ui.md`

Key files:
- `ui/adaptive_grids.md`
- `ui/mobile_ux_quality.md`
- `ui/virtualized_scrollrect.md`

## UI Tweens
Skill family: `ui_tweens/`
Triggers:
- tween
- tweens
- primetween
- dotween
- sequence
- ui animation
- fade
- scale tween
- move tween
Use for:
- tween-library-specific UI work
- tween target lifetime bugs
- animation ownership and interrupt handling
- popup and screen close-order issues involving tweens
Project override:
- `Assets/AIOutput/ProjectMemory/SkillOverrides/ui_tweens.md`

Key files:
- `ui_tweens/primetween.md`

## Editor
Skill family: `editor/`
Triggers:
- editor
- inspector
- propertydrawer
- menuitem
- importer
- validation tool
- build pipeline
Use for:
- editor tooling
- content validation
- import workflow

## Audio
Skill family: `audio/`
Triggers:
- audio
- sound
- music
- mixer
- snapshot
- audioclip
- streaming
Use for:
- playback behavior
- mixer policy
- audio memory strategy

## FX
Skill family: `fx/`
Triggers:
- fx
- vfx
- particle
- trail
- spawn
- overdraw
Use for:
- effect lifecycle
- spawn budget
- mobile GPU-sensitive VFX

## Shaders
Skill family: `shaders/`
Triggers:
- shader
- material
- keyword
- variant
- urp
- srp batcher
- fillrate
Use for:
- mobile shader policy
- material discipline
- variant control

## Optimization
Skill family: `optimization/`
Triggers:
- optimize
- performance
- perf
- gc
- alloc
- microfreeze
- frame spike
- startup
- loading
- thermal
- battery
- anr
Use for:
- frame budget
- allocation control
- startup and loading smoothness
Project override:
- `Assets/AIOutput/ProjectMemory/SkillOverrides/performance.md`

Key files:
- `optimization/frame_budgeting.md`
- `optimization/allocation_control.md`
- `optimization/loading_and_microfreeze_prevention.md`
- `optimization/bridge_performance.md`

## Profiling
Skill family: `profiling/`
Triggers:
- profiler
- profiling
- marker
- timeline
- memory profiler
- regression
Use for:
- evidence-based performance work
- instrumentation
- regression analysis

## Tests
Skill family: `tests/`
Triggers:
- test
- tests
- playmode
- editmode
- smoke
- release check
- integration test
Use for:
- unit tests
- integration tests
- playmode tests
- release validation
Project override:
- `Assets/AIOutput/ProjectMemory/SkillOverrides/tests.md`

Key files:
- `tests/playmode_tests.md`
- `tests/runtime_service_testability.md`

## Architecture
Skill family: `architecture/`
Triggers:
- state
- service
- event bus
- facade
- presenter
- model
- lifecycle
- boundary
Trigger note:
- prefer this family when the task is primarily about target-shape design, subsystem boundaries, ownership model, or event-flow design, not about safely migrating existing code in place
Use for:
- subsystem design
- event flows
- dependency boundaries
Do not use for:
- behavior-preserving cleanup or seam-first migration of an existing implementation
- local refactors where the target architecture is already known and the main risk is safe transition
Project override:
- `Assets/AIOutput/ProjectMemory/SkillOverrides/architecture.md`

Key files:
- `architecture/routing.md`
- `architecture/dependency_boundaries.md`
- `architecture/state_management.md`
- `architecture/event_driven_design.md`

## Refactoring
Skill family: `refactoring/`
Triggers:
- refactor
- refactoring
- cleanup
- simplify
- extract
- extract service
- extract interface
- extract wrapper
- extract presenter
- split
- split class
- split presenter
- split service
- decouple
- untangle
- migration
- staged migration
- incremental migration
- strangler
- legacy cleanup
- move ownership
- ownership split
- dependency seam
- seam
- thin adapter
- adapter-backed transition
- replace global access
- isolate sdk
- isolate platform
Trigger note:
- broad words such as `cleanup`, `simplify`, or `split` are not enough by themselves; prefer this family only when the request also implies structural change, ownership movement, seam creation, or staged migration
Use for:
- behavior-preserving structure work
- incremental migration
- dependency seam creation
- safe legacy cleanup
Do not use for:
- target-shape architecture design when the main question is what the subsystem boundaries or ownership model should be
- pure bug fixing with a local minimal-diff fix and no boundary or ownership change
- generic code review with no proposed structural change
- pure performance tuning when there is no structural migration or seam work
- simple naming, formatting, or file-move cleanup without behavioral risk
Project override:
- `Assets/AIOutput/ProjectMemory/SkillOverrides/refactoring.md`

Key files:
- `refactoring/behavior_preservation.md`
- `refactoring/incremental_migration.md`
- `refactoring/dependency_seams.md`
- `refactoring/presenter_lifetime_split.md`
- `refactoring/progression_snapshot_reconciliation.md`
- `refactoring/reward_grant_idempotency.md`
- `refactoring/startup_bridge_narrowing.md`
- `refactoring/state_stream_simplification.md`

## Mobile
Skill family: `mobile/`
Triggers:
- lifecycle
- focus
- startup
- suspend
- interruption
- background
- foreground
- resume
- pause
- thermal
- battery
- lowmemory
- low memory
- critical flow
- vulkan
- opengles
- graphics api
Use for:
- Unity mobile lifecycle boundaries
- pause and focus modeling
- mobile persistence triggers
- interruption-safe runtime behavior
- startup
- mobile runtime posture
- critical user flows
- Android graphics API choice and validation posture
Project override:
- `Assets/AIOutput/ProjectMemory/SkillOverrides/mobile.md`

Key files:
- `mobile/lifecycle_boundaries.md`
- `mobile/lifecycle_boundary_review.md`
- `mobile/startup.md`
- `mobile/critical_flows.md`
- `mobile/performance.md`
- `mobile/android_manifest_stability.md`
- `mobile/graphics_api_selection.md`

## SDK
Skill family: `sdk/`
Triggers:
- sdk
- appsflyer
- firebase
- onesignal
- adjust
- attribution
- callback
- consent
- privacy
Use for:
- sdk initialization
- callback safety
- privacy compliance
- store submission compliance
Project override:
- `Assets/AIOutput/ProjectMemory/SkillOverrides/sdk.md`

Key files:
- `sdk/initialization.md`
- `sdk/callback_safety.md`
- `sdk/privacy_compliance.md`
- `sdk/store_compliance.md`
- `sdk/discovery_and_inventory.md`
- `sdk/wrapper_design.md`

## Native
Skill family: `native/`
Triggers:
- jni
- java
- kotlin
- swift
- objective-c
- objective-c++
- native plugin
- pinvoke
- bridge
Use for:
- bridge contracts
- callback lifetime
- ownership across native boundaries
Project override:
- `Assets/AIOutput/ProjectMemory/SkillOverrides/native.md`

Key files:
- `native/bridge_contracts.md`
- `native/callback_lifetime.md`
- `native/ownership.md`
- `native/android_jni.md`
- `native/ios_bridge.md`
