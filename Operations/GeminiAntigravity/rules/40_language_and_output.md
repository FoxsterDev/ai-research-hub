---
trigger: always_on
description: Reply language, answer shape, code-comment policy, and where durable results must land.
---

# Language and output

- Reply in the language the user is writing in. Write every generated artifact — code, identifiers, logs, rules, prompts, reports, commit messages — in English regardless of chat language.
- Structure every non-trivial answer as **Scope → Findings (or plan) → Risks → Validation**, and put the actual result of what you ran in Validation.
- Default to no code comments. Add one only where the code is genuinely non-obvious, keep it to one line, and match the file's existing comment density. Never write a comment that restates the code or narrates a change or fix. Public-API doc comments are fine when the contract is not obvious.
- Match the file you are editing: keep its conventions and declaration order, and never reformat, reorder, or re-comment code you were not asked to change. Implement only the stated spec — do not invent states, modes, or UI beyond it.
- Chat is never the sole source of truth: a plan, review, audit, decision, or reusable lesson goes into a file at its routed location, and a deliverable must never live only in a temp or scratch directory.
