# XUUnity Utility: Skill Merge

## Goal
Integrate extracted knowledge into the `XUUnity` skills system without duplication or conflict.

## Use For
- updating shared skills
- merging new best practices into existing families
- splitting generic rules from project-specific overrides

## Process
1. Compare the new knowledge against `skills/registry.md` and the target skill files.
2. Detect overlap, duplication, contradiction, or obsolete guidance.
3. Merge into the smallest correct target file.
4. If the knowledge is too broad, split it into smaller topic files.
5. If no existing family is a correct fit, create a proposal for a new skill family or a new topic cluster instead of forcing a bad merge.
5. If the knowledge is project-specific, route it to `Assets/AIOutput/ProjectMemory/SkillOverrides/`.
6. Update routing hints only if the new guidance changes skill discovery.

## Rule
Do not force unrelated knowledge into an existing skill family only to avoid creating a new family.
If the best outcome is a new family, propose it explicitly and include the required registry and routing updates.
If the source is mainly methodology or scoring logic rather than execution guidance, prefer merging it into `knowledge/` instead of forcing it into `skills/`.

## Output
- Merge decision
- Target file or files
- New family required, if any
- Duplicate or conflict notes
- Final merged rule set
- Follow-up updates needed in registry or routing
