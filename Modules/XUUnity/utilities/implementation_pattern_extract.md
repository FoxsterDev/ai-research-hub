# XUUnity Utility: Implementation Pattern Extract

## Goal
Extract a reusable development pattern from two or more real code implementations that share the same architectural style.

Use this utility when the user wants to learn how the repo actually builds a kind of system, such as:
- presenter-driven UI
- startup orchestration
- SDK wrapper shape
- popup flows
- screen navigation
- feature composition around a shared base framework

Prefer this utility over generic `knowledge_extraction_triage.md` when:
- the source is primarily code, not prose
- the user wants implementation style, not only durable rules
- the pattern must be compared across multiple implementations
- the extraction should explicitly separate reusable invariants from local feature logic and legacy quirks

If there is only one implementation, or the source does not form a repeated pattern, fall back to `knowledge_extraction_triage.md`.

## Entry Commands
- `xuunity extract implementation pattern ...`
- `xuunity extract presenter pattern ...`
- `xuunity system extract implementation pattern ...`
- `xuunity system extract presenter pattern ...`

## Inputs
- two or more concrete implementations
- the shared base abstraction or framework they rely on
- nearby model, view, or composition types only when needed to explain the pattern
- optional project memory or audits when they clarify whether a rule is reusable or only local

## Process
1. Identify the pattern family and the comparison goal.
2. Read the shared base abstraction before drawing pattern conclusions.
3. Compare the implementations across the same axes:
   - construction and dependency ownership
   - initialization sequencing
   - model versus view responsibility
   - async orchestration and cancellation
   - event subscription and disposal
   - child composition or nested flow handling
   - partial failure behavior and fallback strategy
   - activation, deactivation, and disposal behavior
4. Separate:
   - structural invariants that define the pattern
   - useful local variations
   - legacy quirks or anti-patterns that should not be promoted
   - feature-specific logic that must stay project-local
5. Build a code-first evidence matrix:
   - which source line proves each extracted rule
   - which implementation agrees with it
   - which implementation varies from it
6. Decide the destination layer for each extracted rule:
   - public core
   - internal shared
   - project-local
   - review artifact only
   - no action
7. Produce one review package with:
   - the inferred pattern
   - safe-to-copy invariants
   - non-promoted quirks and anti-patterns
   - destination candidates
   - public-safety, internal-sensitivity, and project-dependency assessment
8. Stop for approval by default.
9. If the user explicitly asked to integrate in the same request, apply only the extracted parts that are clearly approved and correctly routed.

## Output
- Source set summary
- Pattern family and scope
- Shared base abstraction
- Extracted invariants
- Useful variations
- Anti-patterns or non-promoted quirks
- Candidate public-core outputs
- Candidate internal-shared outputs
- Candidate project-local outputs
- Public-safety assessment
- Internal-sensitivity assessment
- Project-dependency assessment
- Recommended destination and apply scope

## Rule
Do not promote a code pattern just because two implementations happen to look similar.
Promote only the parts that are:
- supported by the shared base abstraction
- repeated across the compared implementations
- consistent with current lifecycle and disposal behavior
- clearly better than feature-local accident or legacy habit
