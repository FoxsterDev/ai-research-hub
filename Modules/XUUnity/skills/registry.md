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
Project override:
- `Assets/AIOutput/ProjectMemory/SkillOverrides/ui.md`

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
Use for:
- subsystem design
- event flows
- dependency boundaries
Project override:
- `Assets/AIOutput/ProjectMemory/SkillOverrides/architecture.md`

## Mobile
Skill family: `mobile/`
Triggers:
- startup
- resume
- pause
- thermal
- battery
- low memory
- critical flow
- vulkan
- opengles
- graphics api
Use for:
- startup
- mobile runtime posture
- critical user flows
- Android graphics API choice and validation posture

Key files:
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
