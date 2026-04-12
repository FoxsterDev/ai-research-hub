# XUUnity Project Health Report Format

## Default Sections
- Scope
- Current readiness
- Scores
- Score interpretation
- Blockers
- Risks
- Missing context
- Freshness findings
- Evidence summary
- Recommended next actions
- Verification status

## Score Areas
- routing readiness
- project memory completeness
- project memory usability
- project memory freshness
- report availability
- engineering AI readiness
- product AI readiness

## Score Scale
- `0`
  - absent or unusable
- `1`
  - severe gap
- `2`
  - weak and fragile
- `3`
  - usable with limitations
- `4`
  - strong and practical
- `5`
  - strong, current, and easy to trust

## Readiness Bands
- `blocked`
- `fragile`
- `usable`
- `strong`

## Evidence Summary Expectations
- list the most important evidence sources used:
  - project router
  - `ProjectMemory`
  - gameplay bootstrap evidence from `Assets/AIOutput/` when relevant
  - relevant `Assets/AIOutput/` artifacts
  - source code checks
- say explicitly when a key score was based more on memory than code

## Freshness Findings Expectations
- identify which claim groups were checked:
  - architecture ownership
  - SDK inventory
  - platform constraints
  - known issues
  - testing strategy
  - release rules
- state the verification depth used:
  - `spot-check`
  - `targeted verification`
  - `broad verification`
- say whether gameplay bootstrap evidence from host-local onboarding artifacts was used:
  - `yes`
  - `no`
- if bootstrap evidence was used, say where the protocol resolved that evidence set:
  - repo router
  - project router
  - local memory rules
- if bootstrap evidence was used, identify which important claims still live only in bootstrap artifacts and should be absorbed into `ProjectMemory/`
- include the resulting trust decision:
  - `safe for product answers`
  - `safe only for engineering ideation`
  - `code-first verification required`
  - `memory update required before use`

## Verification Status Values
- `verified in source code`
- `based on project memory`
- `mixed verification`
- `partially inferred`
