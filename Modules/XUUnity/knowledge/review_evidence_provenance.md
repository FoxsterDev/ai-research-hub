# XUUnity Knowledge: Review Evidence Provenance

## Purpose
Prevent a change from validating itself through branch-authored memory, review reports, tests, or design notes.

## Evidence Order
For a change review, prefer evidence in this order:

1. explicit user requirements and independently approved product or platform contracts;
2. current source and runtime/build evidence for current behavior;
3. project memory and established exemplars from the comparison base;
4. independently reviewed external specifications where relevant;
5. memory, design notes, tests, and review artifacts added or changed by the target change.

Lower-ranked evidence may explain intent. It does not override contradictory higher-ranked evidence.

## Branch-Derived Evidence Rule
- Treat project memory added or modified in the reviewed change as a candidate design record, not an independent acceptance contract.
- Compare branch memory with the comparison-base version when one exists.
- Do not award project-fit or architecture credit because implementation and branch-authored memory agree with each other.
- Treat generated review artifacts in the same branch as historical reasoning, not proof that the design is approved or correct.
- Tests added by the change prove only the behavior they exercise; they do not independently justify production abstractions created mainly to make those tests possible.
- If the user or an architecture owner explicitly approves the new contract, record that approval as the authority instead of laundering it through branch memory.

## Finding Attribution Rule
- Before claiming that a member, type, or return value is unused, search for that exact symbol across production code and the relevant indirect-use surfaces. A sibling-member search is not evidence about the symbol that was not searched. Exact text search is necessary evidence, not sufficient proof when reflection, serialization, inspector wiring, generated code, or native entrypoints may consume it.
- Before attributing a defect to the reviewed change, inspect the comparison-base version of the same behavior. Label the issue `introduced`, `inherited`, or `reduced by the change`, and cite both base and target evidence when that classification affects the verdict.

## Current-Behavior Rule
Current source and representative runtime/build evidence win over stale memory for what the product does now. Memory remains relevant for intended boundaries, but a reviewer must report the drift instead of choosing whichever source makes the change look stronger.

## Output Requirement
When branch-derived evidence materially affects a verdict, state:

- comparison-base truth used;
- branch-derived candidate evidence used;
- independent authority, or `none`;
- any unresolved contradiction.
