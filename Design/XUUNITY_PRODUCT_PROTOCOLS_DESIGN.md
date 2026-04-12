# XUUnity Product Protocols Design

## Goal
Design a product-facing protocol series inside `XUUnity` so product managers, producers, and stakeholders can quickly get:
- implementation details
- feature logic explanations
- flow and dependency understanding
- delivery risk summaries
- rollout and validation implications

The system should answer product questions across Unity projects without forcing non-engineers to navigate raw code, legacy reports, or SDK internals.

## Problem
Current `XUUnity` is already strong for implementation, review, architecture, SDK work, native plugins, and system evolution.
What is still missing is a focused product-facing layer for questions such as:
- how is this feature implemented right now
- what logic decides when this popup, offer, or reward appears
- what systems are touched by changing this flow
- what can break if we change this
- how much work is this request likely to be
- what analytics, ads, saves, progression, or remote config dependencies exist
- what is the safest rollout path

Without a dedicated protocol set, product users will either:
- ask engineering-style questions and get too much code detail
- ask high-level questions and miss technical constraints
- depend on stale tribal knowledge instead of project memory and reports

## Product Protocol Design Principles
- optimize for fast comprehension, not raw code detail
- expose logic, dependencies, and risks in product language
- still remain technically correct and grounded in project memory
- treat project memory as useful context, not guaranteed current truth
- default to critical-flow awareness
- do not hide important technical constraints from product users
- keep answers short, structured, and decision-friendly
- reuse `XUUnity` roles, skills, and project memory instead of creating a separate product-only system

## Proposed Product Protocol Series

```text
AIRoot/
  Modules/
    XUUnity/
      product/
        README.md
        protocols/
          feature_explainer.md
          flow_explainer.md
          implementation_brief.md
          change_impact.md
          delivery_scope.md
          rollout_readiness.md
          dependency_map.md
          bug_impact_brief.md
        output/
          product_summary_format.md
          decision_note_format.md
          rollout_note_format.md

AIModules/
  XUUnityInternal/
  OtherHostLocalProtocol/
```

## Core Product Protocols

### 1. Feature Explainer
Use for:
- "how does this feature work"
- "what is the current logic"
- "when does this screen or popup appear"

Output:
- purpose
- trigger conditions
- user-visible flow
- systems involved
- key risks or edge cases

### 2. Flow Explainer
Use for:
- "explain this user flow end to end"
- "what happens after fail / reward / purchase / return from background"

Output:
- entry point
- state transitions
- dependent systems
- external dependencies
- breakpoints and risk nodes

### 3. Implementation Brief
Use for:
- "how is this implemented"
- "which systems own this"
- "where is the logic split"

Output:
- ownership summary
- main components
- project memory references
- known constraints
- implementation complexity

### 4. Change Impact
Use for:
- "what will change if we modify this"
- "what can break"
- "which systems are touched"

Output:
- affected systems
- critical flows at risk
- analytics, ads, save/load, progression, remote config, SDK impact
- testing and rollout concerns

### 5. Delivery Scope
Use for:
- "how big is this request"
- "is this a small tweak or a cross-system feature"
- "what kind of engineering effort is implied"

Output:
- estimated scope class
- dependency breadth
- likely implementation areas
- risk class
- validation depth needed

### 6. Rollout Readiness
Use for:
- "is this ready to ship"
- "what still needs validation"
- "what are rollout risks"

Output:
- current readiness
- missing validation
- release blockers
- suggested rollout shape

### 7. Dependency Map
Use for:
- "what does this feature depend on"
- "what upstream or downstream systems exist"

Output:
- direct dependencies
- external dependencies
- sensitive integrations
- project memory or report references

### 8. Bug Impact Brief
Use for:
- "what is the product impact of this bug"
- "what user flows are affected"
- "how severe is this for product"

Output:
- affected audience
- affected flow
- severity from product perspective
- likely business impact
- recommended urgency

## Product User Entry Commands
Recommended shorthand:

```text
xuunity product explain this feature
xuunity product explain this flow
xuunity product implementation brief for this system
xuunity product impact of changing this reward flow
xuunity product scope this request
xuunity product rollout readiness for this feature
xuunity product dependency map for this popup
xuunity product impact of this bug
```

Short aliases:

```text
xuunity product feature this
xuunity product flow this
xuunity product brief this
xuunity product impact this
xuunity product scope this
xuunity product rollout this
xuunity product deps this
xuunity product bug this
```

## Routing Model

### Primary role routing
Product protocols should default to:
- `role/product_owner.md` as primary role

Supporting roles by need:
- `role/senior_unity_developer.md`
  - when implementation detail must be accurate
- `role/architect.md`
  - when boundaries or structural ownership matter
- `role/ui_integrator.md`
  - for screen-flow and popup-heavy questions
- `role/qa_manual.md`
  - when validation or rollout quality is central
- `role/researcher.md`
  - when multiple implementation options or uncertain evidence must be compared

### Skill routing
Product protocols should still load relevant skills:
- `skills/core/` always
- `skills/ui/` for screens, popups, reward flows
- `skills/mobile/` for resume, startup, interruptions, critical flows
- `skills/sdk/` for ads, analytics, attribution, notifications, consent
- `skills/native/` if native/plugin ownership affects the answer
- `skills/architecture/` for subsystem boundaries and dependency maps
- `skills/tests/` for rollout readiness and validation depth

### Project memory and reports
Before answering, product protocols should check:
1. `Assets/AIOutput/ProjectMemory/`
2. relevant analysis outputs already in project memory
3. previous outputs only if they help clarify ownership, risks, or current behavior

For gameplay projects, product answers may also use host-local onboarding/bootstrap evidence when the repo router, project router, or project memory rules define that path explicitly.
Curated `ProjectMemory` remains the durable target state.

## Freshness Rule
Project memory may be incomplete or stale.
It must not be treated as automatically current for live implementation details.

Before answering product-facing questions about current behavior, the protocol should:
1. read the relevant project memory and reports
2. identify the most likely source-code ownership points
3. perform a fast source-code verification pass against the current implementation
4. answer only after reconciling project memory with the code

If project memory and source code disagree:
- source code wins for current behavior
- project memory should be treated as historical or partially stale
- the answer should explicitly state that the documentation appears outdated

If the code is unclear or too fragmented to verify quickly:
- say that the answer is partially inferred
- distinguish verified behavior from likely behavior
- recommend updating project memory after clarification

## Verification Model
Product protocols should use a lightweight verification pass, not a full code audit.

The goal is:
- confirm whether the documented logic still matches the current code
- verify ownership and dependencies at a high level
- avoid giving stale product answers

Typical verification targets:
- main entry points
- gating conditions
- key services or presenters
- monetization, analytics, save/load, and remote-config hooks
- critical state transitions

## Output Contract
Every product protocol answer should favor:
- short summary first
- decision-friendly language
- no raw code unless explicitly requested
- technical constraint callouts only when they matter
- verified current behavior over stale documentation

Recommended default sections:
- What it does
- How it works
- What it depends on
- What can break
- What to validate

When useful, also include:
- Verification status
  - verified in source code
  - based on project memory
  - partially inferred

## Product-Safe Language Rules
- avoid deep implementation trivia unless asked
- translate technical dependencies into business or rollout meaning
- keep the answer actionable for roadmap and prioritization decisions
- explicitly call out uncertainty if project memory is incomplete
- distinguish current behavior from inferred behavior
- explicitly call out when project memory appears stale relative to code

## Scope Classification Model
For `delivery_scope.md`, classify requests into:
- `small`
  - isolated UI or logic tweak
- `medium`
  - touches one main flow and one or two dependencies
- `large`
  - cross-system feature, critical flow, or SDK dependency
- `high-risk`
  - startup, monetization, progression, save/load, or native boundary involved

The response should explain why the classification was chosen.

## Product-Facing Risk Model
When summarizing risk, prefer:
- user experience risk
- progression risk
- monetization risk
- data integrity risk
- rollout risk
- validation risk

Map technical causes into one or more of these product-visible buckets.

## Examples

### Example 1
```text
xuunity product explain this feature
Project: <ProjectName>
Feature: rewarded continue after fail
```

Expected answer:
- when the continue offer appears
- which systems decide eligibility
- what ads, progression, analytics, save, and UI dependencies exist

### Example 2
```text
xuunity product impact of changing this reward flow
Project: <ProjectName>
```

Expected answer:
- affected flows
- likely regression areas
- rollout and validation implications

### Example 3
```text
xuunity product rollout readiness for this feature
Project: <ProjectName>
```

Expected answer:
- what is ready
- what evidence is missing
- what still blocks release

## Recommended First Implementation Slice
1. Add `AIRoot/Modules/XUUnity/product/README.md`
2. Add:
   - `protocols/feature_explainer.md`
   - `protocols/change_impact.md`
   - `protocols/delivery_scope.md`
   - `protocols/rollout_readiness.md`
3. Add one shared output format file for product summaries
4. Add shorthand routing to `tasks/start_session.md`
5. Add examples and navigation guidance to `AIRoot/Operations/AI_PROTOCOL_HANDBOOK.md`

## Review Questions
- Should product protocols live under `XUUnity/product/` or under `utilities/` as product-facing utilities?
- Should product protocols always force `role/product_owner.md`, or allow automatic switching to `architect` or `qa_manual` for some queries?
- Should product answers include file references by default, or only on request?
