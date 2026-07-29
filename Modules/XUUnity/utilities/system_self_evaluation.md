# XUUnity Utility: System Installation Review

## Goal
Audit one installed `xuunity` system as a corpus and routing graph.

This utility owns installation health. It is separate from model fitness:
- installation health asks whether the right guidance exists, has one owner,
  is reachable, and stays in the correct layer
- model fitness asks whether one exact model and execution surface applies that
  installed guidance on representative fixtures

The legacy command `xuunity system evaluate ...` remains an alias for this
utility.

## Use For
- periodic protocol and installation audits
- post-bootstrap or post-migration checks
- after adding, removing, or moving routers, roles, skills, knowledge, reviews,
  utilities, or project-memory owners
- before team rollout
- before proposing reusable host or project findings for public-core promotion

## Modes
- `quick`: run deterministic inventory, reference, registry, and routing checks
- `full`: run `quick`, then review semantic conflicts, context economics, design
  registry truth, and promotion candidates

This utility is read-only by default. Route approved cleanup through
`utilities/system_protocol_clean_review.md` and approved knowledge promotion
through `utilities/knowledge_integration.md`.

## Deterministic Preflight
When the public audit script is available, run:

```bash
python3 AIRoot/Modules/XUUnity/scripts/system_installation_audit.py \
  --host-root <host-root>
```

Use its JSON as evidence, not as a replacement for semantic review. The script
may prove that a route is missing or duplicated; it cannot prove that two
differently worded rules contradict each other.

The audit composes existing public routing, storage, and entrypoint checks when
they are present. Do not reimplement their rules in this utility.

Add `--output <host-report-path>.json` when machine evidence must persist. That
explicit option atomically replaces the named evidence file; without it the
audit only emits JSON to stdout.

## Evaluation Scope

### Routing And Entrypoints
- repo, protocol, optional host-overlay, project, and project-memory load order
- shorthand command ownership and specific-before-generic routing
- entrypoint head/tail marker integrity
- alternate router entrypoints being symlinks or thin pointers

### Corpus Coverage
- primary and support roles
- codestyle owners
- task and review routes
- utility indexes and command routes
- skill-family registry coverage and family sub-router reachability
- shared and host-overlay knowledge reachability
- platform and product overlays
- project `SkillOverrides/` precedence

### Conflicts And Dead Paths
- duplicated source-of-truth rules
- one command or capability routed to conflicting owners
- files with no realistic inbound route
- broken references, stale aliases, and archived files still treated as live
- prompt files that add context cost without changing behavior

### Layer And Storage Boundaries
- public-safe reusable guidance in `AIRoot/Modules/XUUnity/`
- host-specific reusable guidance in an optional host overlay
- project-only truth and overrides in the host-declared project-memory layer
- generated reports and mutable evidence outside public protocol sources
- local routers referencing, rather than restating, the repo storage contract

### Public Design Registry
For a full review:
- reconcile every live and archived row against files, scripts, tests, and
  current CLI behavior
- verify status, implementation, importance, remaining effort, and
  `Left to 100%`
- verify that live rows are sorted by importance descending, then remaining
  effort ascending
- identify retired or fully consumed designs as archive candidates; route any
  approved move through the cleanup owner and never delete
- keep public provenance free of host or project identifiers

## Scoring
Score each evidence-backed area from `1` to `5`:
- `routing_stability`
- `reachability`
- `boundary_integrity`
- `execution_efficiency`

Overall installation score:
- `18-20`: strong
- `14-17`: workable but needs targeted cleanup
- `10-13`: noisy or inconsistent
- `<10`: requires structural correction

This score is advisory. A score never overrides a deterministic failure or a
high-severity semantic conflict, and it is never averaged with model fitness.

## Process
1. Resolve the active host root and installed public-core root.
2. Inspect active routers first and record the effective load order.
3. Run deterministic preflight and classify each result as `pass`, `finding`,
   `not_applicable`, or `invalid`.
4. Trace reachability from routers and indexes through roles, skills,
   knowledge, utilities, reviews, overlays, and project memory.
5. Identify canonical owners, duplicates, semantic conflicts, and dead-path
   candidates.
6. In `full` mode, reconcile the public design registry against live evidence.
7. Classify each reusable finding:
   - `public`: reusable across unrelated repos and public-safe
   - `internal`: reusable only inside the current host
   - `project`: meaningful only to one project
   - `no_change`: evidence is weak, duplicated, stale, or not pedagogically
     valuable
8. Score installation health and propose the smallest corrections first.

## Public Promotion Gate
A promotion candidate must include:
- source layer
- distilled claim
- evidence scope
- conflicting owners or `none`
- proposed destination
- public-safety status
- action: `keep` | `merge` | `move` | `delete_candidate` | `promote`
- approval state

Do not promote raw host evidence, project symbols, customer context, secrets, or
model transcripts. A candidate does not authorize its own integration.

## Output
- `mode`: `quick` | `full`
- deterministic audit status and evidence pointer
- effective load-order map
- findings ordered by severity
- corpus coverage by roles, skills, knowledge, reviews, and utilities
- conflicts and dead-path candidates
- public/core versus internal/project boundary status
- storage consistency status
- design registry reconciliation status or `not_run`
- installation score table
- public promotion candidates
- recommended fixes
- what should remain unchanged
- validation gaps

### Design Registry Reconciliation Template

```md
**Design Registry Reconciliation**
- `registry`: `AIRoot/Design/README.md`
- `designs_total`: `<n>`
- `live`: `<n>` · `archived`: `<n>`
- `status_breakdown`: `implemented=<n> active=<n> draft=<n> planned=<n>`
- `resorted`: `yes` | `no`
- `drift_detected`:
  - `<design — declared vs verified status/impl, or none>`
- `archive_candidates`:
  - `<design — reason, or none>`
- `evidence_date`: `YYYY-MM-DD`
- `result_summary`: `<short factual summary>`
```

Use `drift_detected: none` only after every registry row and design file was
checked against live evidence.
