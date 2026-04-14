# XUUnity Utility: System Self Evaluation

## Goal
Audit the current `XUUnity` protocol structure and evaluate whether it remains coherent, non-duplicated, and useful for LLM execution.

## Use For
- periodic protocol audits
- post-migration checks
- after adding new prompt families, skills, or utilities
- before team rollout

## Evaluation Scope
- routing consistency
- duplication across role, tasks, reviews, utilities, skills, platforms, and project memory
- missing layers or dead files
- shared knowledge reachability and trigger coverage
- conflicts between shared prompts and project-specific rules
- clarity of shorthand routing
- LLM efficiency and context cost

## Scoring
Score each area from `1` to `5`:
- `stability`
  - are routing and layering rules consistent and predictable
- `quality`
  - is guidance operational, accurate, and technically strong
- `professionalism`
  - does the protocol read like senior production engineering guidance
- `usefulness`
  - does it help solve real implementation and review tasks efficiently

Overall score:
- `18-20` strong
- `14-17` workable but needs cleanup
- `10-13` noisy or inconsistent
- `<10` requires structural correction

## Process
1. Inspect the active routing files first.
2. Identify duplicated or conflicting instructions.
3. Check whether the shortest normal user command can still assemble the correct stack.
4. Check whether skills, codestyle, project memory, and platform layers are reachable.
5. Check whether shared `knowledge/` files and internal overlay knowledge files have explicit load paths, trigger hints, or utility references.
5. Score the system.
6. Propose the smallest corrective actions first.

## Output
- Findings ordered by severity
- Score table
- Main structural risks
- Recommended fixes
- What should remain unchanged
