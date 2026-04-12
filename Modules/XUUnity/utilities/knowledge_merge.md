# XUUnity Utility: Knowledge Merge

## Goal
Integrate new knowledge without duplication or conflict.

## Process
1. Compare against shared prompts and project memory.
2. Detect duplicates, contradictions, or obsolete guidance.
3. Merge into the smallest correct target.
4. Keep cross-project rules in shared prompts and project-only exceptions in project memory.
5. If the source is an upstream research artifact, preserve only reusable methodology, scoring logic, reviewer rules, and stable conclusions.
6. Remove or redact literal secret values and project-confidential config details before finalizing the merged output.

## Output
- Merge decision
- Target file
- Conflict notes
- Final rule text
