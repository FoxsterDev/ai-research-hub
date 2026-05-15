# XUUnity Unity MCP Evaluation And Adapter Design

Date: `2026-05-04`
Status: `top-level design`
Scope: choose and integrate the best Unity MCP path for `xuunity`, with a scoring model, adapter target, and phased rollout

## Goal

Define how `xuunity` should evaluate Unity MCP solutions so it can:
- choose a primary Unity MCP path with defensible evidence
- reject weak or unsafe candidates early
- add a thin `xuunity` adapter layer instead of coupling prompt logic to one vendor tool surface
- improve Unity-aware validation, inspection, and execution without falling back to misleading shell-based substitutes

This design is intentionally top-level.
It is the selection and integration framework that should be used before the final MCP choice and before writing the concrete adapters.

## Why This Matters Now

Current repo constraints already treat Unity-aware MCP as strategically important:

- `host-local Unity validation boundary docs`
  - if a project requires Unity validation through MCP, direct Unity CLI is a hard must-not
- `host-local project validation boundary docs`
  - `ConsumerProject` is currently on a pre-MCP validation posture
  - `*.csproj` compile is only a partial signal
  - stronger Unity-aware validation should move to Unity MCP once available
- `AIRoot/Modules/XUUnity/tasks/start_session.md`
  - validation-path constraints must be respected during task assembly

So the problem is no longer "should `xuunity` care about MCP?"
It already does.
The real problem is: which Unity MCP path should become the primary one, and how should `xuunity` sit on top of it?

## External Snapshot As Of 2026-05-04

### MCP ecosystem signals

- Official MCP transports are `stdio` and Streamable HTTP.
- MCP guidance still treats `stdio` as the default local-client baseline.
- HTTP authorization is standardized, while `stdio` servers should use local environment-based credential handling.
- MCP design continues to prefer composable primitives:
  - tools
  - resources
  - prompts
  - tasks

### Unity-specific market signals

- Unity now documents an official `Unity MCP` path in `com.unity.ai.assistant@2.6.0-pre.1`.
- Unity's design uses:
  - Unity Editor bridge inside the editor
  - local relay binary under `~/.unity/relay/`
  - `stdio` MCP exposure to external AI clients
  - explicit first-connection approval for direct external clients
  - built-in plus custom MCP tools
  - multiple concurrent clients
  - targeting of a specific Unity project path or editor PID
- A previously visible community server (`Union`) is now archived and explicitly marked deprecated in favor of Unity's official MCP server.
- Active community alternatives still exist, but they should now be treated as fallback or comparison candidates, not as the default first assumption.

## Core Recommendation

Use a two-layer model:

1. choose one primary Unity MCP server or bridge
2. put a thin `xuunity` adapter contract above it

Do not let `xuunity` couple directly to raw vendor tool names as its stable working contract.

The selected MCP solution should provide the transport, editor bridge, and basic Unity capabilities.
`xuunity` should provide:
- workflow shaping
- safe task-level abstractions
- stable naming for high-value operations
- project-aware validation policy
- fallback and evidence labeling rules

## Design Principles

### 1. Validation honesty over fake coverage
- no shell compile path should be presented as equivalent to real Unity validation
- if MCP is unavailable, the validation gap must remain visible

### 2. Official-first, not official-only
- Unity's official MCP should be the default benchmark candidate
- but it should still be evaluated against `xuunity` needs, not accepted blindly

### 3. Thin adapters over deep rewrites
- prefer a vendor MCP that already exposes the right primitives
- add `xuunity` adapters only where workflow control or safety meaningfully improves

### 4. Read-first, then constrained writes
- initial success criteria are inspection, validation, logs, tests, and context gathering
- broad editor mutation should come later and stay tightly scoped

### 5. Stable `xuunity` contract over vendor tool churn
- vendor tool names can change
- `xuunity` should expose a smaller stable conceptual layer to itself

### 6. Project targeting is mandatory
- this monorepo has multiple Unity projects
- any serious Unity MCP candidate must support explicit project or instance targeting

## Candidate Taxonomy

### Tier 1: Official Unity MCP
Default first candidate.

Reason:
- vendor-owned Unity integration path
- custom tool registration model exists
- connection approval exists
- explicit multi-client and project-targeting story exists
- current ecosystem signal points toward convergence here

### Tier 2: Mature editor-integrated community MCP
Use as fallback or comparison candidate.

Reason:
- may cover gaps earlier than the official path
- may expose useful tools or lower setup friction

### Tier 3: Runtime-heavy, experimental, or architecture-divergent MCP
Use only if there is a clear capability gap that Tier 1 and Tier 2 cannot close.

Reason:
- higher integration cost
- weaker fit for editor validation workflows
- larger risk of `xuunity`-specific glue code growth

## Hard Disqualifiers

A candidate should be rejected before detailed scoring if any of the following is true:

1. archived, deprecated, or explicitly superseded by its maintainer
2. no practical way to target a specific Unity project or editor instance
3. no custom tool extension path
4. no safe local transport path compatible with our clients
5. no approval or trust boundary for direct external clients
6. requires `xuunity` to depend on free-form code execution for routine workflows
7. no usable troubleshooting or operational diagnostics story
8. weak maintenance signal plus no clear ownership path

## Scoring Model

Score on `100`.
Anything below `75` is not a primary candidate.
Anything below `85` should not become the default `xuunity` path without a strong compensating reason.

| Category | Weight | What good looks like |
| --- | ---: | --- |
| `xuunity` workflow coverage | `25` | Console access, scene and asset inspection, test execution, validation hooks, project state inspection, useful editor actions |
| Integration fitness | `20` | Works with Codex/Rider and other MCP clients, `stdio` support, project targeting, multi-project usability, low setup friction |
| Safety and trust boundaries | `20` | Explicit approval, least privilege, auditable scope, no hidden shell escalation, clean client trust model |
| Extensibility for adapters | `15` | Custom tool registration, typed schemas, stable inputs/outputs, easy wrapping by `xuunity` |
| Operational robustness | `10` | Reliable startup, reconnect, troubleshooting, logging, compile-error behavior, resilience during domain reloads |
| Product maturity and convergence | `10` | Active ownership, ecosystem adoption signals, documentation quality, non-deprecated trajectory |

## `XUUnity`-Specific Acceptance Harness

This harness is more important than marketing claims.
Every serious candidate should pass it.

### Track A: Read-only inspection
1. connect to the intended project in a multi-project monorepo
2. read console warnings and errors
3. inspect active scene or scene hierarchy
4. inspect asset or prefab metadata
5. return structured results that an agent can summarize reliably

### Track B: Validation and proof
1. run a Unity-aware validation path
2. run editmode tests
3. run playmode tests if supported
4. survive or clearly report compile-error states
5. distinguish:
   - tool unavailable
   - bridge unavailable
   - compile broken
   - tests failed

### Track C: Adapter extensibility
1. register one custom `xuunity` tool
2. expose typed input schema
3. invoke it from the MCP client
4. receive a structured result
5. keep the implementation independent from one agent product

### Track D: Safety and operations
1. first connection requires explicit approval or equivalent trust decision
2. targeting the wrong project instance is detectable and fixable
3. reconnect after Unity restart is understandable
4. logs are accessible enough to debug bridge failure

### Track E: Agent usefulness
1. the returned tool surface is not too raw
2. the agent can choose the right tool without brittle prompt hacks
3. tool names and schemas are descriptive enough for routine `xuunity` workflows

## Preferred Adapter Architecture

```text
User
  -> xuunity routing
    -> xuunity workflow adapter
      -> selected Unity MCP client config
        -> Unity MCP server / relay / bridge
          -> Unity Editor
            -> built-in tools
            -> xuunity custom tools
```

### Layer responsibilities

#### Layer 1: vendor MCP surface
Owns:
- transport
- connection lifecycle
- project targeting
- raw Unity tool invocation

Should not own:
- `xuunity` validation policy
- `xuunity` naming conventions
- `xuunity` review semantics

#### Layer 2: `xuunity` adapter surface
Owns:
- stable high-value tool grouping
- evidence labeling
- fallback labeling
- project-aware workflow rules
- translation from raw vendor outputs to agent-useful summaries

#### Layer 3: project-local custom tools
Owns:
- monorepo-specific high-value diagnostics
- project-aware validation helpers
- narrow runtime or editor queries worth exposing as first-class tools

## Preferred Use Of MCP Primitives

### Tools
Use tools for actions:
- read console
- run tests
- query scene state
- query build or validation status
- execute narrow editor operations

### Resources
Use resources for stable read-only context:
- project capability snapshots
- generated validation reports
- cached scene or hierarchy snapshots
- tool capability manifests

### Prompts
Use prompts for reusable workflows, not raw execution:
- "diagnose Unity compile failure"
- "review startup validation results"
- "summarize failing test batch"

### Tasks
Use tasks later, only if long-running Unity operations prove worth formalizing.

## Adapter Packs To Build After Selection

### Pack 1: Validation Adapter
Stable `xuunity` operations:
- `xuunity_unity_validate_editor_state`
- `xuunity_unity_run_editmode_tests`
- `xuunity_unity_run_playmode_tests`
- `xuunity_unity_collect_console_errors`
- `xuunity_unity_capture_validation_gap`

Purpose:
- convert raw Unity MCP capabilities into honest validation evidence for `xuunity`

### Pack 2: Project Snapshot Adapter
Stable operations:
- `xuunity_unity_project_snapshot`
- `xuunity_unity_scene_snapshot`
- `xuunity_unity_asset_snapshot`

Purpose:
- give the agent structured context without forcing broad free-form probing

### Pack 3: Diagnostics Adapter
Stable operations:
- `xuunity_unity_get_compile_state`
- `xuunity_unity_get_pending_client_state`
- `xuunity_unity_get_bridge_health`

Purpose:
- reduce time lost on "is the bridge broken or is the project broken?"

### Pack 4: Monorepo-Specific Review Tools
Candidate custom tools:
- startup contract snapshot
- consent and SDK initialization inspection
- package inventory and risky dependency diff
- project routing or identity sanity checks

Purpose:
- encode repeated high-value portfolio checks into typed tools

## Selection Process

### Phase 0: Candidate shortlist
Start with:
1. Unity official MCP
2. one strong editor-integrated community fallback
3. optional third candidate only if it covers a missing capability family

### Phase 1: Static review
For each candidate, record:
- ownership
- maintenance status
- transport model
- project targeting story
- approval or trust model
- custom tool story
- troubleshooting maturity

### Phase 2: Smoke install
Check:
- install friction
- startup reliability
- ability to connect from our main client environment

### Phase 3: Acceptance harness
Run Tracks A-E above.
Do not skip this step because docs look good.

### Phase 4: Adapter spike
Build one thin `xuunity` adapter pack:
- validation adapter only

If the adapter already feels heavy or brittle, the candidate is a weak fit even if the raw tool list looks impressive.

### Phase 5: Decision
Choose:
- primary
- fallback
- rejected candidates with reasons

## Decision Rule

Pick the primary candidate only if all of the following are true:

1. no hard disqualifier triggered
2. total score `>= 85`
3. validation adapter spike stays thin
4. multi-project targeting works reliably
5. first-line troubleshooting is practical for normal engineering work

Choose a fallback candidate if:
- the primary is promising but blocked by package maturity, client compatibility, or project-specific operational instability

## Initial Directional Recommendation

As of `2026-05-04`, the default benchmark candidate should be Unity's official MCP path.

Reason:
- current Unity documentation exposes a real editor bridge, relay, approval model, and custom tool registration path
- the ecosystem signal has already started converging around it
- one visible community alternative is explicitly deprecated in its favor
- this direction best matches `xuunity`'s need for Unity-aware validation rather than shell-based substitutes

That is not a final winner declaration.
It is the correct first candidate to evaluate deeply.

The first fallback benchmark should be one active editor-integrated community server, not an archived or deprecated one.

## What Not To Do

- do not start by building a custom Unity MCP from scratch
- do not bind `xuunity` prompts directly to one vendor's raw tool names
- do not treat "can execute arbitrary C# in Unity" as sufficient proof of workflow fit
- do not replace honest validation reporting with synthetic shell-side success signals
- do not evaluate candidates only on tool count

## Deliverables For The Next Step

1. Create a shortlist report with 2-3 concrete candidates.
2. Fill the scoring table for each candidate.
3. Run the acceptance harness on the top 2.
4. Build one `xuunity` validation adapter spike against the top candidate.
5. Decide primary and fallback.

## Evidence Base

### Internal repo artifacts
- `host-local Unity validation boundary docs`
- `host-local project validation boundary docs`
- `AIRoot/Modules/XUUnity/tasks/start_session.md`
- `AIRoot/Design/AI_TOOLING_AUTOMATION_DESIGN.md`
- `host-local MCP security audit`

### External sources reviewed on 2026-05-04
- Model Context Protocol specification overview
- MCP transports specification
- MCP authorization and security guidance
- MCP registry overview
- Unity official MCP docs under `com.unity.ai.assistant@2.6.0-pre.1`
- candidate community Unity MCP repositories used for market comparison
