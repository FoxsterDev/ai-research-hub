# XUUnity MCP UI Primitives Design

Date: `2026-05-12`
Status: design proposal
Scope: public UI read/action/assert contracts for `XUUnity Light Unity MCP`

## Goal

Define a reusable UI primitive layer for public `XUUnity` MCP so
`user_like_interaction` validation can be honest, typed, and reusable across
projects.

This design is intentionally separate from the reference-watch workflow.
ReferenceWatch tells us which external tools are strongest references and which
failure modes matter. This document defines the actual UI primitive surface we
should build.

Related design:
- `AIRoot/Modules/AIReferenceWatch/design/XUUNITY_MCP_REFERENCE_WATCH_DESIGN_2026-05-12.md`

Canonical location:
- `AIRoot/Operations/XUUnityLightUnityMcp/Designs/XUUNITY_MCP_UI_PRIMITIVES_DESIGN_2026-05-12.md`

## Why UI Primitives Are A Prerequisite

Without UI primitives, a suite like:

- open Play Mode
- dismiss consent
- wait for lobby
- click through tutorial
- claim daily streak
- verify second entry no longer shows tutorial

will be forced into project-specific hooks.

That may still be valuable, but it proves mostly:

- project automation contracts
- state transitions the project itself reports

It does not necessarily prove:

- the visible UI hierarchy was correct
- the real button was clickable
- the actual popup was present
- the user-visible tutorial path advanced as expected

So the validation stack needs an explicit rule:

- `project_action_contract` can run without UI primitives
- `user_like_interaction` cannot be considered honest without either:
  - reusable UI read/action/assert primitives
  - or an explicit downgrade in proof class

UI primitives are therefore not "nice to have" for real E2E. They are the
minimum reusable control plane for user-like flows.

## Reference-Informed Constraint

This design should consume outputs from ReferenceWatch before public contract
approval.

For new UI primitive families or major contract changes:

1. run a `reference-first` review for the focus area
2. identify `overallLeaders` and `capabilityLeaders`
3. record `borrow / reject / differentiate`
4. then finalize the public UI contract

## UI Primitive Program

Design UI primitives as small, typed MCP operations, not one giant `manage_ui`
surface in the first slice.

Recommended first public operations:

- `unity.ui.query`
- `unity.ui.exists`
- `unity.ui.get_text`
- `unity.ui.get_state`
- `unity.ui.wait_for`

Recommended second slice:

- `unity.ui.click`
- `unity.ui.submit`
- `unity.ui.input_text`
- `unity.ui.select`

Recommended third slice:

- `unity.ui.list_children`
- `unity.ui.capture_element`
- `unity.ui.assert`

### Why Start Read-Only

Read-only UI primitives give immediate value:

- verify tutorial is visible
- verify reward text exists
- verify popup is absent on second entry
- verify the correct button is interactable

They are safer than clicks and less likely to create flaky side effects.

### Why Keep Them Narrow

The UI surface should avoid the early trap of `manage_ui` doing everything.

Narrow tools are better because:

- easier schema
- easier failure reporting
- clearer evidence
- easier client usage
- easier comparison with references

## UI Primitive Contracts

Every UI primitive should define:

- supported UI tech:
  - `uGUI`
  - `TMP`
  - optional `UI Toolkit` later
- selector model:
  - name
  - hierarchy path
  - component type
  - text match
  - optional project-defined semantic id
- response payload
- failure taxonomy

Example `unity.ui.query` response:

```json
{
  "matched": true,
  "matchCount": 1,
  "elements": [
    {
      "name": "DailyStreakClaimButton",
      "path": "Canvas/Lobby/DailyStreakPopup/ClaimButton",
      "active": true,
      "interactable": true,
      "text": "Claim"
    }
  ]
}
```

## Safety Rules For UI Actions

UI actions must not be generic blind screen automation.

Required safeguards:

- action requires a resolved selector
- action fails if zero or multiple unsafe matches exist unless the step opts in
  to multi-match handling
- action result records the selected element path
- actions are valid only in `playing` or another explicitly supported state
- actions return explicit precondition failures instead of no-op success

## Relationship To Project Actions

Do not replace project actions entirely.

Recommended split:

- use generic UI primitives for reusable user-facing interactions
- use project actions for domain-specific state changes and assertions

Examples that likely remain project actions:

- switch runtime environment
- clear `SharedAppId`
- inject test account credentials
- assert domain model reward state

Examples that should prefer UI primitives:

- tutorial popup exists
- claim button text is visible
- click next tutorial button
- verify popup disappeared

## Proposed Roadmap

### Phase 0: Reference Baseline

Dependency from the sibling reference-watch design:

- first comparison report for the tracked references exists
- strongest references for `ui_primitives` are identified
- first `reference-first` design artifact exists

Exit criteria:

- `overallLeaders` and `capabilityLeaders` are known for `ui_primitives`
- initial `borrow / reject / differentiate` decisions are recorded

### Phase 1: UI Primitive Design Baseline

Deliver:

- typed spec for read-only UI primitives
- selector model
- response model
- failure taxonomy
- proof that the design fits `uGUI` first

Exit criteria:

- `unity.ui.query`, `exists`, `get_text`, `get_state`, `wait_for` contracts are
  stable enough to implement

### Phase 2: UI Read Primitive Implementation

Deliver:

- first MCP UI read operations in the Unity package
- scenario/compiler integration for read-only UI assertions
- evidence in scenario results

Exit criteria:

- `user_like_interaction` suites can honestly prove:
  - tutorial visible
  - tutorial absent
  - reward label text
  - button state

### Phase 3: UI Action Primitive Implementation

Deliver:

- `click`
- `submit`
- `input_text`
- `select`

Exit criteria:

- tutorial click-through no longer requires a single project-owned
  `complete_tutorial` hook

### Phase 4: Validation Suite Integration

Deliver:

- validation suite compiler understands `unity.ui.*`
- compiler can downgrade or block flows based on missing UI capabilities
- project suites can report exactly which steps are covered by UI primitives and
  which still require project actions

## What To Copy From References And What Not To Copy

Safe to borrow:

- command naming inspiration
- selector patterns
- response schema ideas
- failure taxonomy
- evidence model ideas

Do not copy blindly:

- giant grouped UI tools with weak contracts
- blind UI automation
- unstable action semantics
- project-specific selectors masquerading as generic contracts

## Immediate Next Steps

1. Run `reference-first` review for `ui_primitives`.
2. Lock the read-only contract set.
3. Decide selector resolution rules and ambiguity handling.
4. Add evidence payload shape for UI results.
5. Implement `query`, `exists`, `get_text`, `get_state`, `wait_for`.
