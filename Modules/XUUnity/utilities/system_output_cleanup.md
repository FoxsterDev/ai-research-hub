# XUUnity Utility: System Output Cleanup

## Goal
Reduce AI-generated clutter and stale reports without deleting durable project truth.
This utility is designed for high-precision cleanup decisions, with a target of at least `97%` precision on preservation decisions by using conservative routing, multi-signal scoring, and archive-first handling.

## Use For
- cleaning old AI reports from `Assets/AIOutput/`
- cleaning stale host-level system reports from `AIOutput/Reports/`
- reducing duplicate bootstrap artifacts
- archiving superseded reviews and audits
- removing trivial junk such as `.DS_Store`, empty folders, and orphan generated metadata
- keeping project memory trustworthy by separating durable memory from historical noise

## Do Not Use For
- deleting source code, runtime assets, or shared prompts
- rewriting `Assets/AIOutput/ProjectMemory/` as part of routine cleanup
- removing the only remaining artifact for a project/category without explicit user approval
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
- `xuunity system cleanup` -> `projects`
- `xuunity system cleanup reports` -> `reports`
- `xuunity system cleanup all` -> `all`

## Safety Posture
- Audit-first by default.
- No deletion of any file or folder without explicit user approval.
- Archive before delete for any non-trivial report.
- Hard delete only for near-zero-value artifacts such as junk files, orphan metadata, or exact duplicate generated outputs with a retained canonical copy.
- Treat `Assets/AIOutput/ProjectMemory/` as protected unless the user explicitly requests a memory cleanup pass.
- Keep at least one newest artifact per project and category.
- Keep the newest artifact when the utility cannot prove supersession.

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
  - current durable truth, still-valuable history, newest report in category, or ambiguous artifacts
- `archive`
  - old but potentially useful reports that are superseded, duplicated, or low-value for daily work
- `delete_candidate`
  - trivial junk or near-certain zero-value generated leftovers
- `manual_review`
  - anything with mixed signals, unclear ownership, or possible historical value

## Uselessness Criteria
An artifact is not useless from age alone.
Mark it as low-value only when one or more of the following signals exist:

### Strong Signals
- a newer report of the same category and scope exists
- the file is an exact duplicate by content or clearly redundant copy by naming and purpose
- the file is a transient bootstrap artifact that has been absorbed into `ProjectMemory/`
- the file is a machine-generated junk file such as `.DS_Store`
- the file is an orphan `.meta` whose primary asset no longer exists
- the file lives in an output area but is empty, placeholder-only, or structurally broken

### Medium Signals
- the file has not been modified for `30+` days
- the file belongs to a noisy phase-output family such as `Surveyor_Report`, `Analyst_Report`, `Architect_Plan`, `Reviewer_Report`, `Integrator_Report`, `EditorTool_Report`, `AsmDefSetup_Report`, or similar one-shot onboarding artifacts
- a stronger canonical artifact now exists in a structured folder such as `Audits/`, `CodeReviews/`, `SDKReviews/`, `Architecture/`, or `IncidentReports/`
- a draft artifact exists in `KnowledgeDrafts/` and a later integrated artifact already captures the same decision
- the report is a freshness snapshot and newer freshness reports already exist

### Weak Signals
- the file naming is inconsistent with current export rules
- the artifact sits in the root of `Assets/AIOutput/` instead of the correct typed folder
- the report is small, generic, and not referenced by current project memory

## Decision Rule
Use these thresholds:
- `delete_candidate`
  - at least `1` strong signal and no meaningful preservation signal
  - or junk/orphan status proven directly
- `archive`
  - at least `1` strong signal or `2` medium signals
  - and the artifact is a human-readable report, audit, review, or plan
- `manual_review`
  - mixed strong keep and cleanup signals
  - or possible legacy investigation value
- `keep`
  - latest in category
  - protected path
  - referenced by current project memory
  - or insufficient evidence for supersession

## Recommended Retention Policy
Use these defaults unless the user provides stricter rules:

### Always Keep
- all files in `ProjectMemory/`
- latest report in each major category per project
- latest `2` code reviews per active branch or review family if they exist
- latest `2` project-memory freshness reports
- latest critical incident report for each unresolved issue

### Usually Archive
- onboarding/bootstrap phase reports older than `30` days when the same project already has stable `ProjectMemory/`
- code reviews older than `45` days when newer reviews cover the same branch or feature area
- draft knowledge artifacts older than `45` days when their content was integrated or superseded
- duplicate architecture notes when a newer canonical architecture note exists
- root-level ad hoc reports that should have lived in typed folders and are older than `30` days

### Usually Delete
- `.DS_Store`
- empty directories
- orphan `.meta` files
- exact duplicate generated outputs when one canonical copy remains
- broken temporary files, partial exports, or placeholder-only artifacts

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

### Usually Delete In Host Reports
- `.DS_Store`
- empty directories
- exact duplicate transient summaries when one canonical retained copy exists
- broken temporary run outputs with no evidentiary value

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
  - if a same-project equivalent exists in `ProjectMemory/`, prefer `archive` for the root `Assets/AIOutput/` copy
- `ProjectMemory_Freshness_Report_*`
  - keep the latest `2`, archive older ones
- reports placed in the root of `Assets/AIOutput/` that now have canonical typed folders
  - prefer moving or archiving rather than deleting
- review or incident artifacts tied to regressions, outages, SDK failures, or release decisions
  - never auto-delete; archive only if clearly superseded

## Process
1. Determine the cleanup target scope: `projects`, `reports`, or `all`.
2. Inventory the selected target roots:
   - project scope -> `*/Assets/AIOutput/`
   - reports scope -> `AIOutput/Reports/`
3. Exclude protected paths and runtime-support files immediately.
4. Group candidates by report family, feature scope, and date.
5. Detect duplicates, superseded artifacts, junk files, and orphan metadata.
6. Score each candidate with `system_output_cleanup_scorecard_template.md`.
7. Produce a cleanup plan with `keep`, `archive`, `delete_candidate`, and `manual_review`.
8. Prefer archive destinations under:
   - project scope -> `Assets/AIOutput/Archive/`
   - reports scope -> `AIOutput/Reports/Archive/`
9. For each `delete_candidate`, write a short safety justification that explains why removal is safe and why it should happen.
10. Do not execute archive or deletion actions unless the user explicitly asks to apply the plan.

## Output
- filled candidate scorecards using `system_output_cleanup_scorecard_template.md`
- one summary scorecard using `system_output_cleanup_scorecard_template.md`
- summary by project
- protected files skipped
- keep list
- archive plan
- delete candidates
- manual review items
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
- keep ambiguous artifacts by default
- keep at least one newest artifact per category
- treat historical incident and release-decision reports as non-trivial
- treat missing user approval as an automatic stop condition for any delete action

## Recommended Short Commands
- `xuunity system cleanup`
- `xuunity system cleanup projects`
- `xuunity system cleanup reports`
- `xuunity system cleanup all`
- `xuunity system cleanup stale reports`
- `xuunity system cleanup ai outputs`
- `xuunity system archive old reports`
- `xuunity system audit ai clutter`
