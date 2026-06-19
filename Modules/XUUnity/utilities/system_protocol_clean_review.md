# XUUnity Utility: System Protocol Clean Review

## Goal
Run one sanitary review-and-fix pass over public `XUUnity` protocol, design,
template, and review artifacts so public `AIRoot` stays coherent, public-safe,
and easy for future agents to route.

This is an orchestration utility. It does not replace narrower utilities; it
loads them in a deterministic order, deduplicates their findings, and applies
small safe fixes when the requested task includes cleanup or repair.

## Use For
- public `AIRoot` protocol sanitation
- checking whether design-review artifacts are still truthful
- cleaning public/private boundary drift in protocol docs
- moving operational prompt templates out of design registries
- fixing stale links after moving, deleting, or archiving docs
- verifying that design registry counts match files on disk
- checking that public docs match code-owned behavior
- final review after old-report cleanup changes touch public protocol docs

Short commands:
- `xuunity system protocol clean review`
- `xuunity system protocol cleanup review`
- `xuunity system clean protocol review`
- `xuunity system sanitary review`
- `xuunity system public core sanitation`

## Do Not Use For
- deleting generated reports without the cleanup approval flow
- editing project runtime code
- replacing a production code review
- promoting private host knowledge into public core without public-safety review
- broad roadmap planning when no protocol/doc/template sanitation is needed

## Load Order
Load these in order:

1. `utilities/system_health_review.md`
2. `utilities/design_retro_review.md` when `Design/` or design registry claims are in scope
3. `utilities/protocol_consistency_checklist.md` when shared prompts, tasks, reviews, utilities, templates, or indexes changed
4. `reviews/git_change_review.md` for the final current-diff review
5. `utilities/system_output_cleanup.md` only when `AIOutput/Reports/`, project AI outputs, or report retention are in scope
6. `utilities/system_output_cleanup_apply.md` only after explicit user approval of exact archive/delete actions

Also load:
- `knowledge/decision_rules.md` for public-vs-host-local placement decisions
- `knowledge/severity_matrix.md` for finding severity
- `reviews/review_artifact_contract.md` when saved review artifacts are produced

## Review Scope
Inspect the current changed files plus any directly related indexes or owners:

- `Design/README.md`
- `Design/` and `Design/Archived/`
- `Templates/`
- `Modules/XUUnity/tasks/start_session.md`
- `Modules/XUUnity/utilities/README.md`
- `Modules/XUUnity/README.md`
- `Modules/XUUnity/reviews/`
- `Modules/XUUnity/utilities/`
- `Operations/` docs that describe protocol evidence or canonical baselines
- `Roadmaps/` docs that name protocol approval or evidence flows

If the task names a narrower scope, keep the pass narrow but still run the
mandatory consistency checks for files touched by the cleanup.

## Required Checks

### Public / Host-Local Boundary
- Public `AIRoot` files must not contain concrete private host paths, private
  project names, customer details, logs, dated private evidence artifacts, or
  generated host-local report paths.
- Public templates may describe host-local inputs and outputs only through
  placeholders such as `<host-output-root>`, `<incident-report-path>`, and
  `<output-path>`.
- Host-local workflows belong under host output such as `AIOutput/...`, not as
  concrete public-core evidence.
- Optional private module support may mention generic `AIModules/` or
  user-local cache concepts when the owning design requires it, but public
  review artifacts must not cite a specific private pack path as evidence.

### Placement
- Cross-cutting architecture and protocol designs belong in `Design/`.
- Public prompt and scaffold templates belong in `Templates/`.
- Public tool-specific designs belong under `Operations/<ToolOrSurface>/Designs/`.
- Host-local or private designs belong in host-local output, not public
  `AIRoot`.
- If a file is moved, fix all inbound references in the same pass.

### Design Registry
- Count live design files and archived design files from disk.
- Verify `Design/README.md` counts and registry rows match those files.
- Flag any registry row with no file, any file with no row, and any archived doc
  still listed as live.
- Verify lifecycle labels: `implemented`, `active`, `draft`, `planned`,
  `archived`.
- Keep operational templates out of the design registry; link them as related
  public templates instead.
- Keep provenance public-safe. Do not use host-local paths as public evidence.

### Protocol Consistency
- Identify the canonical owner for each changed concept.
- Avoid broad restatements when a task, utility, review, or knowledge file can
  reference the owner.
- Update indexes and routing hints when adding, moving, or renaming a protocol
  file.
- Keep shorthand command routing deterministic in `tasks/start_session.md`.

### Evidence And Code Contract Alignment
- Docs that describe tool behavior must match the code's actual selector,
  filename, schema, or command contract.
- When code supports only one canonical pointer, docs must not imply that a
  looser "latest dated" selector is valid.
- If docs intentionally describe future behavior, label it as future work or a
  gap, not the current operating rule.

### Git Change Review
- Review the final diff after cleanup.
- Confirm moved files are represented as intentional moves or delete/add pairs
  that `git add -A` can stage safely.
- Run at minimum:
  - `git status --short --branch`
  - `git diff --check`
  - targeted `rg` checks for stale names, private path fragments, and moved
    file references
- If tests are relevant and available, run the narrowest test or lint suite that
  validates the changed protocol/tooling surface.

## Safe Auto-Fix Scope
When the user asks to fix findings, this utility may apply these non-destructive
changes without a separate approval round:

- move a public-safe prompt template from `Design/` to `Templates/`
- update indexes and routing maps for a moved or added public protocol file
- remove stale registry rows for files no longer in `Design/`
- replace concrete host-local evidence paths in public templates with
  placeholders
- correct design registry counts when they are mechanically verifiable
- align docs with an existing code-owned canonical filename or selector
- fix dead links caused by the current cleanup
- add a small README entry for discoverability

## Requires Explicit Approval
Stop and ask before:

- deleting any generated report or historical artifact
- deleting or archiving design files not already proven retired by the reviewed
  plan
- editing `Assets/AIOutput/ProjectMemory/` beyond an explicitly requested
  minimal reference rewrite
- changing runtime code, scripts, schemas, or CLI behavior when the user only
  requested protocol sanitation
- promoting host-local/private knowledge into public core

## Output
Produce findings first, then the cleanup result:

- `verdict`: `clean` | `fixed` | `needs_approval` | `blocked`
- high-severity findings
- public/private boundary status
- design registry status
- template placement status
- protocol consistency status
- evidence/code contract status
- git diff safety status
- files changed
- validation commands and results
- residual risks or `none`

## 10/10 Exit Criteria
Report `clean` or `fixed` only when all are true:

- no stale references to moved or deleted files remain in the reviewed scope
- no concrete host-local evidence paths remain in public review artifacts or
  public templates, except generic documented concepts owned by a public design
- design registry counts match disk
- operational templates are indexed under `Templates/`, not as active design
  rows
- changed docs match current code-owned behavior
- `tasks/start_session.md`, `Modules/XUUnity/utilities/README.md`, and
  `Modules/XUUnity/README.md` reference any new public utility
- `git diff --check` passes
- the final response clearly names anything not verified

## Rule
Do not declare the public protocol surface clean because individual docs look
reasonable in isolation. A clean verdict requires cross-file routing,
placement, registry, boundary, and code-contract consistency.
