# XUUnity Product Protocol: Project Health Audit

## Use For
- assess whether a project is AI-ready
- find missing project structure or missing context
- identify blockers before relying on AI workflows heavily
- compare structural readiness with practical answer-readiness
- decide whether the next step should be feature work, memory refresh, or setup cleanup

## Inputs
- project router
- repo router when routing or storage context matters
- `Assets/AIOutput/ProjectMemory/`
- `Assets/AIOutput/ProjectMemory/SkillOverrides/` if present
- relevant `Assets/AIOutput/` reports when they help readiness judgment
- source code when the audit claims current-readiness confidence

## Process
1. Verify routing readiness:
   - confirm the project has an active `Agents.md`
   - confirm the router points at the current shared module model
   - confirm storage expectations do not contradict the repo router
2. Review project memory structure:
   - confirm `Assets/AIOutput/ProjectMemory/` exists
   - identify whether the folder contains durable files that are specific enough to guide work
   - confirm whether `SkillOverrides/` exist when project-local skill constraints matter
3. Review project memory usability:
   - identify whether the memory is organized enough to answer common engineering and product questions
   - identify whether important rules are discoverable without archaeology across old reports
4. Review project memory freshness at a high level:
   - check whether the most important current-truth claims still look aligned with source code and current project layout
   - do not perform a full freshness audit here; only identify whether freshness confidence is strong, mixed, or weak
5. Review report availability:
   - identify whether relevant prior outputs, audits, SDK reviews, and architecture notes exist in `Assets/AIOutput/`
   - distinguish useful historical evidence from clutter
6. Assess answer-readiness:
   - engineering AI readiness
   - product AI readiness
   - whether current code-backed answers are realistic without major manual reconstruction
7. Score the project using the report format score areas.
8. Classify findings as:
   - blockers
   - risks
   - missing context
   - recommended next actions

## Score Areas
- routing readiness
- project memory completeness
- project memory usability
- project memory freshness
- report availability
- engineering AI readiness
- product AI readiness

## Score Anchors
Use `0-5` scoring for each area:
- `0`
  - absent or unusable
- `1`
  - severe gap; workflow is blocked or highly misleading
- `2`
  - weak and fragile; usable only with heavy manual reconstruction
- `3`
  - usable with visible limitations
- `4`
  - strong and practical for normal work
- `5`
  - strong, current, and easy to trust in repeated use

## Readiness Bands
- `blocked`
  - routing is broken, required project memory is absent, or the project cannot support reliable AI-assisted work
- `fragile`
  - no hard block, but major gaps or stale context mean answers are likely to require heavy manual verification
- `usable`
  - normal AI-assisted work is practical, with some caveats or missing polish
- `strong`
  - the project is well-structured for repeatable engineering and product-facing AI workflows

## Decision Rules
- Use `blocked` if:
  - routing readiness is `0-1`
  - or project memory completeness is `0-1` for a project that depends on memory-first workflows
- Use `fragile` if:
  - no hard blocker exists
  - but two or more score areas are `2` or below
  - or freshness confidence is too weak for trustworthy product answers
- Use `usable` if:
  - no blocker exists
  - and the project can support normal engineering and product-facing flows with explicit caveats
- Use `strong` if:
  - no blocker exists
  - the important score areas are mostly `4-5`
  - and the report can defend current-readiness claims with source-backed verification where needed

## Verification Rules
- If the audit claims current behavior or current readiness with high confidence, verify the critical claim in source code.
- If project memory and source code disagree, source code wins for current readiness.
- Treat historical reports in `Assets/AIOutput/` as supporting evidence, not default truth.
- Call out when a score is based mainly on project memory versus verified in source.

## Output
Use `output/project_health_report_format.md`.
