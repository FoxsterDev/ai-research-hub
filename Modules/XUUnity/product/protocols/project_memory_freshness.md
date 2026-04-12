# XUUnity Product Protocol: Project Memory Freshness

## Use For
- assess whether project memory is still trustworthy
- detect stale project rules and reports
- decide whether product-facing or engineering answers need code-first verification
- confirm that historical reports live in `Assets/AIOutput/` and are not being treated as default project memory
- identify which memory files should be refreshed first
- decide whether the project is safe for memory-first workflows or requires code-first fallback

## Inputs
- current-truth files in `Assets/AIOutput/ProjectMemory/`
- `Assets/AIOutput/ProjectMemory/SkillOverrides/` when project-specific skill constraints matter
- for gameplay projects, any host-local onboarding/bootstrap evidence defined by the repo router, project router, or project-local memory rules when the task is the first meaningful memory refresh or when `ProjectMemory/` is sparse
- relevant historical reports in `Assets/AIOutput/` only when drift or legacy comparison matters
- source code and current project structure
- project router when memory usage rules need confirmation

## Audit Units
Check the most important claims across these units:
- architecture ownership
- SDK inventory
- platform constraints
- known issues
- testing strategy
- release rules

## Verification Depth
Choose the minimum useful verification depth and say which one was used:
- `spot-check`
  - verify only the highest-risk or most frequently reused claims
- `targeted verification`
  - verify the claims most likely to break product answers or risky engineering decisions
- `broad verification`
  - verify most important claim groups across the project memory set

## Process
1. Read current-truth files in `Assets/AIOutput/ProjectMemory/` first.
2. If the project is a gameplay project and `ProjectMemory/` is missing, thin, or clearly still in onboarding shape, inspect relevant host-local onboarding/bootstrap artifacts in `Assets/AIOutput/`.
   - Use them as seed evidence for the first durable-memory refresh.
   - Do not treat them as equivalent to already-curated `ProjectMemory/`.
   - Resolve what counts as bootstrap evidence from the repo router, project router, and any project-local memory guidance before assuming specific artifact names.
3. Confirm whether historical reports already live in `Assets/AIOutput/`.
   - If they do, say so directly when it matters.
4. Do not rely on historical reports by default.
   - Use them only for current-vs-past behavior drift, legacy reconstruction, old bug research, or bootstrap absorption on the first gameplay refresh.
5. Identify the most important current-truth claims from the audit units.
6. If bootstrap evidence was used, split the findings into:
   - already durable in `ProjectMemory/`
   - supported only by bootstrap evidence in `Assets/AIOutput/`
   - missing from both durable memory and bootstrap evidence
7. Choose verification depth:
   - `spot-check`
   - `targeted verification`
   - `broad verification`
8. Perform source-code verification on the claims most likely to cause wrong answers if stale.
9. Classify each important claim as:
   - `verified current`
   - `partially stale`
   - `likely stale`
   - `unverifiable from current context`
10. Classify the overall project memory freshness.
11. Report where stale memory would cause wrong product or engineering answers.
12. Recommend which files should be updated first.
13. If bootstrap artifacts contain durable guidance that is not yet represented in `ProjectMemory/`, call that out explicitly as a memory-absorption gap.

## Bootstrap Evidence Rules
- Host-local gameplay onboarding/bootstrap artifacts are valid seed evidence for gameplay-project memory refresh.
- Runtime-support artifacts in `Assets/AIOutput/` may be used as current evidence for integration shape or flow coverage even when they are not themselves durable `ProjectMemory/`.
- Onboarding reports, surveys, analysis outputs, reviewer outputs, and setup reports are bootstrap evidence, not default current truth.
- When bootstrap evidence remains the only source for a repeatedly needed claim, recommend absorbing the durable part into `ProjectMemory/`.
- Once strong `ProjectMemory/` exists, bootstrap artifacts should drop back to secondary evidence unless the task is specifically about onboarding history or gameplay-bridge integration drift.

## Freshness Classes
- `verified current`
  - the claim matches current source evidence closely enough to trust in normal use
- `partially stale`
  - the claim still helps, but some details or constraints appear outdated
- `likely stale`
  - the claim is mismatched with current code or project layout strongly enough to mislead work
- `unverifiable from current context`
  - current source evidence is too weak or too broad to confirm the claim safely

## Trust Decisions
Use these outcome labels in the report:
- `safe for product answers`
  - key product-facing claims are current enough to answer normal behavior questions without major freshness risk
- `safe only for engineering ideation`
  - memory is still useful for orientation, but current behavior claims should not be treated as settled without code checks
- `code-first verification required`
  - memory may still help navigation, but current answers should start from code rather than memory
- `memory update required before use`
  - the memory is stale enough that relying on it would actively mislead engineering or product work

## Update Priority Rules
- update first any file whose stale content would create wrong product explanations or rollout decisions
- update second any file whose stale content would misroute risky engineering work, reviews, or SDK decisions
- update third files that are incomplete but less likely to cause high-cost wrong answers

## Verification Rules
- If current code and project memory disagree, code wins for current behavior.
- If the protocol cannot verify a claim safely, mark it `unverifiable from current context` instead of guessing.
- Distinguish clearly between:
  - memory-backed claim
  - bootstrap-evidence-backed claim
  - code-verified claim
  - historical-context-only claim
- Call out when a stale file affects product answers differently from engineering workflows.
- If a bootstrap artifact is carrying durable operational knowledge that should have been absorbed into `ProjectMemory/`, flag that as a structure problem, not only a freshness problem.

## Output
Use `output/project_health_report_format.md`.
