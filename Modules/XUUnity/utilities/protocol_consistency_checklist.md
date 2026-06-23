# XUUnity Utility: Protocol Consistency Checklist

## Goal
Run a compact consistency pass after editing shared `xuunity` prompts so the system becomes more stable instead of accumulating overlapping doctrine.

## Use For
- prompt-structure cleanup
- task-file consolidation
- shared-knowledge refactors
- schema normalization across related prompt files
- post-extraction review before integrating reusable protocol changes

## Checklist
1. Identify the canonical owner for each changed concept.
   - lane semantics -> `knowledge/validation_lanes.md`
   - Unity-path and evidence-strength boundaries -> `knowledge/unity_validation_boundaries.md`
   - validation schema -> `knowledge/validation_contract.md`
2. Check that task files reference the canonical owner instead of restating full doctrine inline.
3. Check that shared field names stay exact across the whole feature chain.
   - `primary_validation_lane`
   - `secondary_validation_lane`
   - `lane_selection_reason`
   - `expected_evidence_class`
   - `validation_gaps`
4. Check that unresolved fields use `none` explicitly instead of vague placeholders such as `probably`, `later`, or omitted keys.
5. Check that standalone task usability still exists.
   - Each task may keep a compact local reminder.
   - No task should require loading half the module just to understand its own output shape.
6. Check that evidence claims remain honest.
   - no source-only conclusion presented as generated-build proof
   - no compile success presented as runtime proof
   - no lane without trustworthy final accounting presented as full validation
7. Check that README and utility indexes reference any new canonical files or utilities.
8. Check that shared changes stay public-safe and do not leak host-local or project-private names into `AIRoot/`.
9. For any added or copied project router (`<Project>/Agents.md`), check that the `# Project Agent Router:` title and the `- Project:` field both equal the containing folder name, so a copy-pasted router cannot silently keep a sibling project's identity.

## Change Rule
- If doctrine changes, update the owning `knowledge/` file first.
- Update task files only to change stage-specific obligations, not to create a second doctrine source.
- If a task file starts to explain the same rule twice, cut it back and point to the owner.

## Output
- changed concept owners
- remaining duplication risk
- remaining schema drift
- missing index updates
- explicit follow-up fixes, or `none`
