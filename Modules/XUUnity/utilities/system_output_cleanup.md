# XUUnity Utility: System Output Cleanup

## Goal
Reduce AI-generated clutter and stale reports without deleting durable project truth.
This utility is designed for high-precision cleanup decisions, with a target of at least `97%` precision on preservation decisions by using conservative safety gates while still generating aggressive cleanup candidates in high-churn projects.
Archive is a short-term holding area, not a permanent preservation promise.

## Use For
- cleaning old AI reports from `Assets/AIOutput/`
- cleaning stale host-level system reports from `AIOutput/Reports/`
- reducing duplicate bootstrap artifacts
- archiving superseded reviews and audits
- pruning old archive contents that no longer justify retention
- removing trivial junk such as `.DS_Store`, empty folders, and orphan generated metadata
- keeping project memory trustworthy by separating durable memory from historical noise

## Do Not Use For
- deleting source code, runtime assets, or shared prompts
- substantive rewriting of `Assets/AIOutput/ProjectMemory/` as part of routine cleanup
- removing the only remaining artifact for a project/family without explicit user approval
- deleting files only because they are old

## Cleanup Targets
The utility supports three target scopes:
- `projects`
  - review only project-local outputs under `*/Assets/AIOutput/`
- `reports`
  - review only shared cross-project outputs under `AIOutput/Reports/`
- `all`
  - review both project-local outputs and shared report outputs

Default:
- `xuunity system output cleanup` -> `all`
- `xuunity system cleanup` -> `all`
- `xuunity system cleanup reports` -> `reports`
- `xuunity system cleanup all` -> `all`

## Volatile Project Mode
Use a more aggressive cleanup posture when one or more of the following are true:
- the user explicitly asks for aggressive cleanup
- the project changes weekly or faster
- the output roots contain repeated same-family reports from rapid review or migration cycles
- archive growth is clearly outpacing the value of retained history

In volatile-project mode:
- prefer `all` scope unless the user narrows it
- treat historical AI outputs as low-default-value unless they are current truth, unresolved incident evidence, or explicitly preserved decision records
- prefer one-pass coupled cleanup plans:
  - patch active references
  - archive or delete stale artifacts in the same approved pass
- prefer delete proposals more often for stale archives and superseded bootstrap artifacts
- do not let archive folders grow indefinitely without re-evaluation

## Safety Posture
- Audit-first by default.
- No deletion of any file or folder without explicit user approval.
- Archive before delete for any non-trivial report.
- Hard delete only for near-zero-value artifacts such as junk files, orphan metadata, or exact duplicate generated outputs with a retained canonical copy.
- Treat `Assets/AIOutput/ProjectMemory/` content as protected unless the user explicitly requests a memory cleanup pass.
- Routine cleanup must not delete, truncate, or substantively rewrite `ProjectMemory/` guidance.
- Minimal reference-only rewrites inside `ProjectMemory/` are allowed when they are:
  - small and local
  - explicitly included in the cleanup plan
  - limited to current-replacement links, archive-path links, or explicit historical-only notes
- Keep at least one newest artifact per project and family unless the user explicitly wants full family removal.
- Keep the newest artifact when the utility cannot prove supersession.
- If current memory references a historical artifact only as legacy context, prefer a coupled plan that rewrites the reference and cleans the artifact in the same approved pass.

## Approval Gate
- Deletion is never implicit.
- A cleanup audit may classify files as `delete_candidate`, but execution must stop before deletion until the user explicitly approves.
- For every `delete_candidate`, provide:
  - why the file is safe to remove
  - why removing it is necessary or useful
  - what canonical file or retained evidence remains after deletion
  - whether the action is reversible through archive instead of hard delete
- If the safety case is weak, downgrade the item to `archive` or `manual_review`.

## Protected Paths
Never classify these as routine cleanup targets:
- `Assets/AIOutput/ProjectMemory/`
- `Assets/AIOutput/ProjectMemory/SkillOverrides/`
- `AIModules/`
- `AIRoot/`
- host-declared gameplay bridge entry artifacts under `Assets/AIOutput/`
- host-declared runtime-support bridge schemas under `Assets/AIOutput/`
- host-declared bridge-related asmdefs or narrow support interfaces under `Assets/AIOutput/`
- any `.cs`, `.asmdef`, `.json`, or equivalent runtime-support file still used by the project

Protected means `not a cleanup target`.
It does not forbid the minimal reference-only rewrites defined in `First-Class Coupled Cleanup`.

Within `AIOutput/Reports/`, treat these as protected by default:
- `AIOutput/Reports/ReviewArtifacts/README.md`
- `AIOutput/Reports/System/README.md`
- `AIOutput/Reports/System/Smoke/README.md`
- `AIOutput/Reports/System/knowledge_extraction_eval_latest_summary.json`
- latest regression or evaluation summary for an active protocol pipeline
- latest canonical research-watch, system-health, and system-progress report when no newer canonical replacement exists

## Cleanup Classes
Classify each candidate into exactly one bucket:
- `keep`
  - current durable truth, still-valuable history, newest retained artifact in family, or ambiguous artifacts
- `archive`
  - old but potentially useful reports that are superseded, duplicated, or low-value for daily work
- `delete_candidate`
  - trivial junk or near-certain zero-value generated leftovers
- `manual_review`
  - anything with mixed signals, unclear ownership, or possible historical value

## Retention Unit Hierarchy
Use one canonical retention unit hierarchy for all cleanup decisions:
1. `project`
2. `family`
3. optional `branch_or_feature_slice`
4. newest `N`

Definitions:
- `family`
  - the same artifact purpose within one project, for example:
    - `ProjectMemory_Freshness_Report_*`
    - `Surveyor_Report*`
    - one code-review line for the same feature, branch, or review thread
- `branch_or_feature_slice`
  - an optional narrower dimension inside a family when the family naturally splits by branch, feature area, or incident thread
- `category`
  - summary/reporting label only; do not use it as the primary retention unit

Decision rule:
- score keep/archive/delete at the `family` level
- use `branch_or_feature_slice` only when needed to avoid mixing unrelated review lines inside the same family
- never keep or delete solely because something is the latest in a broad `category`

## First-Class Coupled Cleanup
Treat `ProjectMemory historical reference rewrite` as a first-class cleanup step, not as incidental follow-up work.

Use it when:
- active `ProjectMemory` or current freshness reports still mention stale artifacts only as historical context
- the stale artifact blocks otherwise-safe archive or delete actions
- the required rewrite is small and local

Expected shape:
1. identify the minimal active references that still point at the stale artifact
2. rewrite those references to:
   - a current-truth replacement
   - an archive path
   - or an explicit historical-only note
3. re-score the stale artifact in the same cleanup plan
4. when approved, apply the rewrite before archive or delete actions

Do not leave obviously stale artifacts in `manual_review` only because a small reference rewrite is needed first.

## Uselessness Criteria
An artifact is not useless from age alone.
Mark it as low-value only when one or more of the following signals exist:

### Strong Signals
- a newer report of the same family and scope exists
- the file is an exact duplicate by content or clearly redundant copy by naming and purpose
- the file is a transient bootstrap artifact that has been absorbed into `ProjectMemory/`
- the file is already archived and no longer serves as the newest retained evidence for its family
- the file is a machine-generated junk file such as `.DS_Store`
- the file is an orphan `.meta` whose primary asset no longer exists
- the file lives in an output area but is empty, placeholder-only, or structurally broken

### Medium Signals
- the file has not been modified for `30+` days
- the file belongs to a noisy phase-output family such as `Surveyor_Report`, `Analyst_Report`, `Architect_Plan`, `Reviewer_Report`, `Integrator_Report`, `EditorTool_Report`, `AsmDefSetup_Report`, or similar one-shot onboarding artifacts
- a stronger canonical artifact now exists in a structured folder such as `Audits/`, `CodeReviews/`, `SDKReviews/`, `Architecture/`, or `IncidentReports/`
- a draft artifact exists in `KnowledgeDrafts/` and a later integrated artifact already captures the same decision
- the report is a freshness snapshot and newer freshness reports already exist
- the project shows repeated weekly churn in the same report family
- the archive already contains multiple same-family artifacts with no current-truth dependency

### Weak Signals
- the file naming is inconsistent with current export rules
- the artifact sits in the root of `Assets/AIOutput/` instead of the correct typed folder
- the report is small, generic, and not referenced by current project memory

## Decision Rule
Use these thresholds:
- `delete_candidate`
  - at least `1` strong signal and no meaningful preservation signal
  - or junk/orphan status proven directly
  - or in volatile-project mode:
    - at least `1` strong signal or `2` medium signals
    - and no current-truth dependency
    - and no runtime/build relevance
    - and safe to remove = `yes`
- `archive`
  - at least `1` strong signal or `2` medium signals
  - and the artifact is a human-readable report, audit, review, or plan
- `manual_review`
  - mixed strong keep and cleanup signals
  - or possible legacy investigation value
- `keep`
  - latest retained artifact in family
  - protected path
  - referenced by current project memory
  - or insufficient evidence for supersession

## Recommended Retention Policy
Use these defaults unless the user provides stricter rules:

Apply them by `project -> family -> optional branch_or_feature_slice -> newest N`.

### Always Keep
- all files in `ProjectMemory/`
- latest retained artifact in each report family per project
- latest `1` code review per review family by default
- if a code-review family is naturally split by branch or feature area, keep latest `1` inside each active branch_or_feature_slice
- latest `1` project-memory freshness report by default
- latest `2` project-memory freshness reports only when the newest and previous report clearly form an active comparison pair
- latest critical incident report for each unresolved issue

### Usually Archive
- onboarding/bootstrap phase reports older than `14` days when the same project already has stable `ProjectMemory/`
- code reviews older than `21` days when newer reviews cover the same branch or feature area
- draft knowledge artifacts older than `21` days when their content was integrated or superseded
- duplicate architecture notes when a newer canonical architecture note exists
- root-level ad hoc reports that should have lived in typed folders and are older than `14` days

### Usually Delete
- `.DS_Store`
- empty directories
- orphan `.meta` files
- exact duplicate generated outputs when one canonical copy remains
- broken temporary files, partial exports, or placeholder-only artifacts
- archived bootstrap, rollout, or one-shot review artifacts older than `21` days when:
  - a current-truth replacement exists
  - no unresolved issue depends on them
  - no active memory file still points at them

## Archive Review Cadence
Re-score archive roots regularly instead of letting them grow passively.

Default cadence:
- volatile or weekly-changing project:
  - every `7` days
  - or after every meaningful cleanup pass
- normal active project:
  - every `21` days
- host-level system archives:
  - after each new canonical system-health or system-progress report

During archive review:
- keep only the smallest archive slice that still preserves current decision history
- prefer one representative same-family sample rather than retaining long same-family runs by default
- propose deletion, not re-archive, for cold archived artifacts with no active dependency

## Archive Retention
- Do not treat `Assets/AIOutput/Archive/` or `AIOutput/Reports/Archive/` as permanent storage by default.
- Archived artifacts should be re-scored regularly.
- In volatile-project mode, prefer delete proposals for archived artifacts that are:
  - older than `21` days
  - superseded by current-truth memory or newer same-family artifacts
  - not referenced by active memory, current reports, or unresolved incident work

## AIRoot Report Retention Policy
Use extra caution in `AIOutput/Reports/` because these files can be active protocol evidence.

### Always Keep In Host Reports
- `README.md` files that define folder meaning
- the latest canonical `*_latest_summary.json`
- the newest system-health review unless a newer same-family review exists
- the newest system-progress review unless a newer same-family review exists
- unique review artifacts in `ReviewArtifacts/`
- portfolio outputs that are still the current source for index or registry state

### Usually Archive In Host Reports
- older same-family system reviews when a newer same-family report exists
- old evaluation run payloads when a newer canonical summary already exists
- old prompt fixtures for completed eval runs when the run result is preserved elsewhere
- repeated smoke run outputs when a newer smoke cycle supersedes them
- older archived host reports when a newer canonical report and a newer archived same-family sample already exist

### Usually Delete In Host Reports
- `.DS_Store`
- empty directories
- exact duplicate transient summaries when one canonical retained copy exists
- broken temporary run outputs with no evidentiary value
- archived host reports older than `21` days when they are superseded, unreferenced, and no longer needed as the retained same-family sample

### Host-Report Heuristics
- `knowledge_extraction_eval_latest_summary.json`
  - always keep unless replaced by a clearly newer canonical `latest_summary`
- `knowledge_extraction_eval_*_prompts/`
  - prefer `archive`, not delete, unless duplicated or intentionally regenerated elsewhere
- `ReviewArtifacts/`
  - never auto-delete review artifacts; archive only if a stronger canonical artifact supersedes them
- `System/Smoke/`
  - keep the newest smoke summary set; archive older smoke runs when superseded

## Project-Specific Heuristics
Apply extra caution to these families:
- `Surveyor_Report`, `Analyst_Report`, `Architect_Plan`
  - if a same-project equivalent exists in `ProjectMemory/`, prefer a coupled cleanup plan:
    - patch active references
    - archive or delete the root `Assets/AIOutput/` copy in the same approved pass
- `ProjectMemory_Freshness_Report_*`
  - keep the latest `1` by default
  - keep the latest `2` only when the newest pair still has active comparison value
- reports placed in the root of `Assets/AIOutput/` that now have canonical typed folders
  - prefer moving or archiving first, but propose deletion when the archived copy has already cooled off and no active references remain
- review or incident artifacts tied to regressions, outages, SDK failures, or release decisions
  - never auto-delete; archive only if clearly superseded
- if active memory references a stale artifact only to say it is historical or stale:
  - do not freeze the artifact at `manual_review`
  - propose the minimal reference rewrite required
  - then score the artifact again for archive or delete

## Process
1. Determine the cleanup target scope: `projects`, `reports`, or `all`.
2. Inventory the selected target roots:
   - project scope -> `*/Assets/AIOutput/`
   - reports scope -> `AIOutput/Reports/`
   - include archive folders inside those roots; do not exclude them from scoring
3. Exclude protected paths and runtime-support files immediately.
4. Group candidates by report family, feature scope, and date.
5. Detect duplicates, superseded artifacts, junk files, and orphan metadata.
6. Detect whether the project should be treated as high-churn or volatile for this run.
7. Score each candidate with `system_output_cleanup_scorecard_template.md`.
8. When stale artifacts are still referenced only as historical context, add a coupled reference-rewrite action to the cleanup plan instead of stopping at `manual_review`.
9. Produce a cleanup plan with `keep`, `archive`, `delete_candidate`, and `manual_review`.
10. Prefer archive destinations under:
   - project scope -> `Assets/AIOutput/Archive/`
   - reports scope -> `AIOutput/Reports/Archive/`
11. For each `delete_candidate`, write a short safety justification that explains why removal is safe and why it should happen.
12. Do not execute archive or deletion actions unless the user explicitly asks to apply the plan.

## Output
- cleanup execution contract:
  - `cleanup_mode`
  - `volatile_project_mode`
  - `reference_rewrites_required`
  - `archive_recheck_required`
- filled candidate scorecards using `system_output_cleanup_scorecard_template.md`
- one summary scorecard using `system_output_cleanup_scorecard_template.md`
- summary by project
- retention-family summary
- protected files skipped
- keep list
- archive plan
- delete candidates
- manual review items
- coupled reference rewrites required for aggressive cleanup
- rationale per decision
- estimated disk-noise reduction
- confidence note:
  - `high`
  - `medium`
  - `low`

## Precision Rules
To preserve the `97%` precision target:
- never delete on age alone
- require supersession or junk proof for deletion
- require archive-first for meaningful markdown reports
- keep ambiguous artifacts by default unless the ambiguity can be resolved by a small same-pass reference rewrite
- keep at least one newest retained artifact per family
- treat historical incident and release-decision reports as non-trivial
- treat missing user approval as an automatic stop condition for any delete action

## Recommended Short Commands
- `xuunity system output cleanup`
- `xuunity system cleanup`
- `xuunity system cleanup projects`
- `xuunity system cleanup reports`
- `xuunity system cleanup all`
- `xuunity system cleanup aggressive`
- `xuunity system cleanup all aggressive`
- `xuunity system cleanup stale reports`
- `xuunity system cleanup ai outputs`
- `xuunity system archive old reports`
- `xuunity system prune old archives`
- `xuunity system audit ai clutter`
